from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from hasscheck.config import HassCheckConfig, apply_overrides, discover_config
from hasscheck.detect import detect_project
from hasscheck.models import (
    ApplicabilityApplied,
    CategorySignal,
    HassCheckReport,
    ProjectInfo,
    ReportSummary,
    RuleStatus,
)
from hasscheck.provenance import detect_provenance
from hasscheck.rules.registry import RULES
from hasscheck.slug import detect_repo_slug
from hasscheck.target import _read_manifest_version, build_validity, detect_target

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
}


def run_check(
    path: Path | str,
    *,
    config: HassCheckConfig | None = None,
    no_config: bool = False,
) -> HassCheckReport:
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

    findings = [rule.check(context) for rule in RULES]

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

    # Populate manifest_hash and requirements_hash for ProjectInfo
    _manifest_hash: str | None = None
    _requirements_hash: str | None = None
    if context.integration_path is not None:
        _, _manifest_hash, _requirements_hash = _read_manifest_version(
            context.integration_path
        )

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
            manifest_hash=_manifest_hash,
            requirements_hash=_requirements_hash,
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
