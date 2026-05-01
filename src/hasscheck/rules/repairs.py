from __future__ import annotations

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    FixSuggestion,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.rules.base import ProjectContext, RuleDefinition

CATEGORY = "diagnostics_repairs"
REPAIRS_SOURCE = "https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/repair-issues/"


def repairs_file_exists(context: ProjectContext) -> Finding:
    if context.integration_path is None:
        return Finding(
            rule_id="repairs.file.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="repairs.py exists",
            message="No integration directory was detected, so repairs.py cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect repairs.py.",
            ),
            source=RuleSource(url=REPAIRS_SOURCE),
            fix=FixSuggestion(
                summary="Create custom_components/<domain>/ before adding repairs.py."
            ),
            path="custom_components/<domain>/repairs.py",
        )

    path = context.integration_path / "repairs.py"
    exists = path.is_file()
    if (
        not exists
        and context.applicability
        and context.applicability.has_user_fixable_repairs is False
    ):
        return Finding(
            rule_id="repairs.file.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="repairs.py exists",
            message="Project config declares there are no user-fixable repair scenarios.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="hasscheck.yaml declares has_user_fixable_repairs: false.",
                source="config",
            ),
            source=RuleSource(url=REPAIRS_SOURCE),
            fix=None,
            path=str(path.relative_to(context.root)),
        )

    return Finding(
        rule_id="repairs.file.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="repairs.py exists",
        message=(
            "Integration includes repairs.py."
            if exists
            else "Integration does not include repairs.py; user-fixable repair flows cannot be inspected."
        ),
        applicability=Applicability(
            reason="Repair flows are useful when integrations have user-fixable problems."
        ),
        source=RuleSource(url=REPAIRS_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add repairs.py when the integration has user-fixable repair scenarios."
        ),
        path=str(path.relative_to(context.root)),
    )


RULES = [
    RuleDefinition(
        id="repairs.file.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="repairs.py exists",
        why="Repair flows guide users through problems they can fix themselves.",
        source_url=REPAIRS_SOURCE,
        check=repairs_file_exists,
        overridable=True,
    )
]
