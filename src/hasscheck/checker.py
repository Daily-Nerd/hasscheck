from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from hasscheck.config import HassCheckConfig, apply_overrides, discover_config
from hasscheck.detect import detect_project
from hasscheck.models import CategorySignal, HassCheckReport, ProjectInfo, ReportSummary, RuleStatus
from hasscheck.rules.registry import RULES

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

    context = detect_project(root)
    findings = [rule.check(context) for rule in RULES]

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
            integration_path=str(context.integration_path.relative_to(root)) if context.integration_path else None,
        ),
        summary=ReportSummary(categories=categories, overrides_applied=overrides_applied),
        findings=findings,
    )
