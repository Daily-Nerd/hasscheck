from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from hasscheck.config import HassCheckConfig, apply_overrides, discover_config
from hasscheck.detect import detect_project
from hasscheck.models import (
    Applicability,
    ApplicabilityApplied,
    ApplicabilityStatus,
    CategorySignal,
    HassCheckReport,
    ProjectInfo,
    ReportSummary,
    RuleStatus,
)
from hasscheck.profiles import PROFILES, ProfileDefinition
from hasscheck.provenance import detect_provenance
from hasscheck.rules.base import RuleDefinition
from hasscheck.rules.registry import RULES
from hasscheck.slug import detect_repo_slug
from hasscheck.target import build_validity, detect_target

APPLICABILITY_FLAGS_BY_RULE = {
    "diagnostics.file.exists": "supports_diagnostics",
    "diagnostics.redaction.used": "supports_diagnostics",
    "repairs.file.exists": "has_user_fixable_repairs",
    "config_flow.file.exists": "uses_config_flow",
    "config_flow.manifest_flag_consistent": "uses_config_flow",
    "config_flow.user_step.exists": "uses_config_flow",
    # v0.10 issue #101 — advanced config_flow rules
    "config_flow.reauth_step.exists": "uses_config_flow",
    "config_flow.reconfigure_step.exists": "uses_config_flow",
    "config_flow.unique_id.set": "uses_config_flow",
    "config_flow.connection_test": "uses_config_flow",
}

CATEGORY_LABELS = {
    "hacs_structure": "HACS Structure",
    "manifest_metadata": "Manifest Metadata",
    "modern_ha_patterns": "Modern HA Patterns",
    "diagnostics_repairs": "Diagnostics/Repairs",
    "docs_support": "Docs/Support",
    "maintenance_signals": "Maintenance Signals",
    "tests_ci": "Tests/CI",
    "version": "Version Identity",
}


def apply_profile_overrides(
    findings: list,
    profile: ProfileDefinition | None,
    rules: list[RuleDefinition],
) -> list:
    """Apply profile severity boosts and disables to findings.

    Returns a new list. Findings whose rule_id is in profile.disabled_rules
    become NOT_APPLICABLE with applicability.source='profile'. Findings whose
    rule_id is in profile.severity_overrides AND whose rule is overridable
    receive the boosted severity. Non-overridable rules are silently passed
    through unchanged (D6 — profiles cannot mutate locked rules).

    profile=None is the no-op case: findings are returned as a new list,
    unchanged in content.

    Override order documented here: (1) rules fire, (2) profile overrides,
    (3) per-rule config overrides.
    """
    if profile is None:
        return list(findings)

    rule_by_id = {r.id: r for r in rules}
    result = []

    for finding in findings:
        rule = rule_by_id.get(finding.rule_id)

        # Disabled by profile → mark not_applicable, source='profile'
        if finding.rule_id in profile.disabled_rules:
            if rule is None or not rule.overridable:
                # D6 — silently skip non-overridable rules
                result.append(finding)
                continue
            result.append(
                finding.model_copy(
                    update={
                        "status": RuleStatus.NOT_APPLICABLE,
                        "applicability": Applicability(
                            status=ApplicabilityStatus.NOT_APPLICABLE,
                            reason=f"Disabled by profile '{profile.id}'.",
                            source="profile",
                        ),
                    }
                )
            )
            continue

        # Severity boost — only when rule is overridable
        if (
            finding.rule_id in profile.severity_overrides
            and rule is not None
            and rule.overridable
        ):
            result.append(
                finding.model_copy(
                    update={"severity": profile.severity_overrides[finding.rule_id]}
                )
            )
            continue

        # Pass through unchanged
        result.append(finding)

    return result


def run_check(
    path: Path | str,
    *,
    config: HassCheckConfig | None = None,
    no_config: bool = False,
    profile_name: str | None = None,
) -> HassCheckReport:
    """Run a full HassCheck report for the given repository path.

    Override order:
      1. Rules fire and produce raw findings.
      2. Profile severity_overrides and disabled_rules are applied
         (apply_profile_overrides). Only overridable rules are affected.
      3. Per-rule RuleOverride entries from hasscheck.yaml are applied last
         (apply_overrides). User intent always wins over profile.
    """
    if config is not None and no_config:
        raise ValueError("Cannot pass both config= and no_config=True; pick one.")

    root = Path(path).resolve()

    if config is None and not no_config:
        config = discover_config(root)

    rule_settings: dict[str, dict] = {}
    if config is not None:
        rule_settings = {
            rule_id: override.settings
            for rule_id, override in (config.rules or {}).items()
            if override.settings
        }

    context = detect_project(
        root,
        applicability=config.applicability if config else None,
        rule_settings=rule_settings,
    )

    now = datetime.now(UTC)
    target = detect_target(root, context.integration_path, context.domain)
    validity = build_validity(checked_at=now)

    # Pipe version identity from detect_target into the rule context (ADR-0002)
    if target is not None:
        context = replace(
            context,
            integration_version=target.integration_version,
            integration_version_source=target.integration_version_source,
            integration_release_tag=target.integration_release_tag,
            commit_sha=target.commit_sha,
        )

    findings = [rule.check(context) for rule in RULES]

    # --- profile resolution: CLI argument wins over config (D5) ---
    effective_profile_name = profile_name or (config.profile if config else None)
    if effective_profile_name is not None:
        if effective_profile_name not in PROFILES:
            raise ValueError(
                f"Unknown profile: {effective_profile_name!r}. "
                f"Known profiles: {sorted(PROFILES)}."
            )
        findings = apply_profile_overrides(
            findings, PROFILES[effective_profile_name], RULES
        )

    config_applicability_rule_ids = sorted(
        finding.rule_id
        for finding in findings
        if finding.applicability.source == "config"
    )
    applicability_applied = ApplicabilityApplied(
        count=len(config_applicability_rule_ids),
        rule_ids=config_applicability_rule_ids,
        flags=sorted(
            {
                APPLICABILITY_FLAGS_BY_RULE[rule_id]
                for rule_id in config_applicability_rule_ids
            }
        ),
    )

    from hasscheck.models import OverridesApplied

    overrides_applied = OverridesApplied()

    if config is not None:
        findings, overrides_applied = apply_overrides(findings, config)

    possible: dict[str, int] = defaultdict(int)
    awarded: dict[str, int] = defaultdict(int)
    for finding in findings:
        if finding.status in {RuleStatus.NOT_APPLICABLE, RuleStatus.MANUAL_REVIEW}:
            continue
        possible[finding.category] += 1
        if finding.status is RuleStatus.PASS:
            awarded[finding.category] += 1

    categories = [
        CategorySignal(
            id=category,
            label=CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
            points_awarded=awarded[category],
            points_possible=points_possible,
        )
        for category, points_possible in sorted(possible.items())
    ]

    return HassCheckReport(
        project=ProjectInfo(
            path=str(root),
            type="integration" if context.integration_path is not None else "unknown",
            domain=context.domain,
            integration_path=str(context.integration_path.relative_to(root))
            if context.integration_path
            else None,
            repo_slug=detect_repo_slug(root, context.integration_path),
            integration_version=target.integration_version if target else None,
            integration_version_source=target.integration_version_source
            if target
            else "unknown",
            manifest_hash=target.manifest_hash if target else None,
            requirements_hash=target.requirements_hash if target else None,
        ),
        summary=ReportSummary(
            categories=categories,
            overrides_applied=overrides_applied,
            applicability_applied=applicability_applied,
        ),
        findings=findings,
        provenance=detect_provenance(now=now),
        target=target,
        validity=validity,
    )
