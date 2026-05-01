from __future__ import annotations

import json

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

HA_MANIFEST_SOURCE = "https://developers.home-assistant.io/docs/creating_integration_manifest/"
HACS_INTEGRATION_SOURCE = "https://www.hacs.xyz/docs/publish/integration/"


def _manifest_path(context: ProjectContext):
    if context.integration_path is None:
        return None
    return context.integration_path / "manifest.json"


def manifest_exists(context: ProjectContext) -> Finding:
    path = _manifest_path(context)
    exists = path is not None and path.is_file()
    display = "custom_components/<domain>/manifest.json" if path is None else str(path.relative_to(context.root))
    return Finding(
        rule_id="manifest.exists",
        rule_version="1.0.0",
        category="manifest_metadata",
        status=RuleStatus.PASS if exists else RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json exists",
        message=(
            "Integration manifest exists."
            if exists
            else "Integration manifest is missing, so Home Assistant and HACS metadata cannot be inspected."
        ),
        applicability=Applicability(reason="Every Home Assistant integration needs a manifest.json file."),
        source=RuleSource(url=HACS_INTEGRATION_SOURCE),
        fix=None
        if exists
        else FixSuggestion(summary="Add custom_components/<domain>/manifest.json with the required integration metadata."),
        path=display,
    )


def manifest_domain_exists(context: ProjectContext) -> Finding:
    path = _manifest_path(context)
    if path is None or not path.is_file():
        return Finding(
            rule_id="manifest.domain.exists",
            rule_version="1.0.0",
            category="manifest_metadata",
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title="manifest.json defines domain",
            message="manifest.json is missing, so the domain field cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.json must exist before HassCheck can inspect manifest.domain.",
            ),
            source=RuleSource(url=HACS_INTEGRATION_SOURCE),
            fix=FixSuggestion(summary="Create manifest.json first, then define the domain field."),
            path="custom_components/<domain>/manifest.json",
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Finding(
            rule_id="manifest.domain.exists",
            rule_version="1.0.0",
            category="manifest_metadata",
            status=RuleStatus.FAIL,
            severity=RuleSeverity.REQUIRED,
            title="manifest.json defines domain",
            message=f"manifest.json is not valid JSON: {exc.msg}.",
            applicability=Applicability(reason="manifest.json exists but cannot be parsed."),
            source=RuleSource(url=HACS_INTEGRATION_SOURCE),
            fix=FixSuggestion(summary="Fix manifest.json syntax, then rerun HassCheck."),
            path=str(path.relative_to(context.root)),
        )

    domain = payload.get("domain")
    has_domain = isinstance(domain, str) and bool(domain.strip())
    return Finding(
        rule_id="manifest.domain.exists",
        rule_version="1.0.0",
        category="manifest_metadata",
        status=RuleStatus.PASS if has_domain else RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines domain",
        message=("manifest.json defines a domain." if has_domain else "manifest.json does not define a non-empty domain."),
        applicability=Applicability(reason="HACS expects custom integration manifests to define domain."),
        source=RuleSource(url=HACS_INTEGRATION_SOURCE),
        fix=None if has_domain else FixSuggestion(summary="Add a stable domain field to manifest.json."),
        path=str(path.relative_to(context.root)),
    )


RULES = [
    RuleDefinition(
        id="manifest.exists",
        version="1.0.0",
        category="manifest_metadata",
        severity=RuleSeverity.REQUIRED,
        title="manifest.json exists",
        why="Home Assistant integrations use manifest.json for integration metadata.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_exists,
    ),
    RuleDefinition(
        id="manifest.domain.exists",
        version="1.0.0",
        category="manifest_metadata",
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines domain",
        why="The domain is the stable integration identifier used by Home Assistant and HACS.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_domain_exists,
    ),
]
