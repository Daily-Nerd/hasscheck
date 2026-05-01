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
DIAGNOSTICS_SOURCE = "https://developers.home-assistant.io/docs/core/integration/diagnostics/"


def diagnostics_file_exists(context: ProjectContext) -> Finding:
    if context.integration_path is None:
        return Finding(
            rule_id="diagnostics.file.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py exists",
            message="No integration directory was detected, so diagnostics.py cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect diagnostics.py.",
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=FixSuggestion(summary="Create custom_components/<domain>/ before adding diagnostics.py."),
            path="custom_components/<domain>/diagnostics.py",
        )

    path = context.integration_path / "diagnostics.py"
    exists = path.is_file()
    return Finding(
        rule_id="diagnostics.file.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="diagnostics.py exists",
        message=(
            "Integration includes diagnostics.py."
            if exists
            else "Integration does not include diagnostics.py; downloadable troubleshooting data support cannot be inspected."
        ),
        applicability=Applicability(reason="Diagnostics help users provide support data while redacting sensitive information."),
        source=RuleSource(url=DIAGNOSTICS_SOURCE),
        fix=None if exists else FixSuggestion(summary="Add diagnostics.py with redaction for sensitive values."),
        path=str(path.relative_to(context.root)),
    )


RULES = [
    RuleDefinition(
        id="diagnostics.file.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="diagnostics.py exists",
        why="Diagnostics help users and maintainers troubleshoot without exposing secrets when implemented with redaction.",
        source_url=DIAGNOSTICS_SOURCE,
        check=diagnostics_file_exists,
    )
]
