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

CATEGORY = "hacs_structure"
HACS_SOURCE = "https://www.hacs.xyz/docs/publish/integration/"
HA_BRAND_SOURCE = "https://developers.home-assistant.io/docs/core/integration/brand_images/"


def brand_icon_exists(context: ProjectContext) -> Finding:
    if context.integration_path is None:
        return Finding(
            rule_id="brand.icon.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="brand/icon.png exists",
            message="No integration directory was detected, so brand/icon.png cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect brand assets.",
            ),
            source=RuleSource(url=HACS_SOURCE),
            fix=FixSuggestion(summary="Create custom_components/<domain>/ before adding brand/icon.png."),
            path="custom_components/<domain>/brand/icon.png",
        )

    path = context.integration_path / "brand" / "icon.png"
    exists = path.is_file()
    return Finding(
        rule_id="brand.icon.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="brand/icon.png exists",
        message=(
            "Integration includes brand/icon.png."
            if exists
            else "Integration does not include brand/icon.png. HACS and Home Assistant brand image support cannot be fully inspected."
        ),
        applicability=Applicability(reason="HACS expects integration brand assets, and Home Assistant supports local custom integration brand images."),
        source=RuleSource(url=HACS_SOURCE),
        fix=None if exists else FixSuggestion(summary="Add custom_components/<domain>/brand/icon.png."),
        path=str(path.relative_to(context.root)),
    )


RULES = [
    RuleDefinition(
        id="brand.icon.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="brand/icon.png exists",
        why="Brand icons help users recognize integrations and are expected by HACS integration publishing docs.",
        source_url=HACS_SOURCE,
        check=brand_icon_exists,
        overridable=True,
    )
]
