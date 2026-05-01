from __future__ import annotations

import json
from typing import Any

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

CATEGORY = "modern_ha_patterns"
CONFIG_FLOW_SOURCE = "https://developers.home-assistant.io/docs/core/integration/config_flow"
MANIFEST_SOURCE = "https://developers.home-assistant.io/docs/creating_integration_manifest"


def _config_flow_path(context: ProjectContext):
    if context.integration_path is None:
        return None
    return context.integration_path / "config_flow.py"


def _manifest_path(context: ProjectContext):
    if context.integration_path is None:
        return None
    return context.integration_path / "manifest.json"


def _display_path(path, context: ProjectContext, fallback: str) -> str:
    if path is None:
        return fallback
    return str(path.relative_to(context.root))


def _read_manifest(context: ProjectContext) -> tuple[dict[str, Any] | None, str | None]:
    path = _manifest_path(context)
    if path is None or not path.is_file():
        return None, None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, exc.msg

    if not isinstance(payload, dict):
        return None, "manifest root must be a JSON object"

    return payload, None


def config_flow_file_exists(context: ProjectContext) -> Finding:
    path = _config_flow_path(context)
    if path is None:
        return Finding(
            rule_id="config_flow.file.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="config_flow.py exists",
            message="No integration directory was detected, so config_flow.py cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect config_flow.py.",
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(summary="Create custom_components/<domain>/ before adding config_flow.py."),
            path="custom_components/<domain>/config_flow.py",
        )

    exists = path.is_file()
    return Finding(
        rule_id="config_flow.file.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py exists",
        message=(
            "Integration includes config_flow.py."
            if exists
            else "Integration does not include config_flow.py; UI setup support cannot be inspected."
        ),
        applicability=Applicability(reason="Config flows are the standard way to set up integrations via the UI."),
        source=RuleSource(url=CONFIG_FLOW_SOURCE),
        fix=None
        if exists
        else FixSuggestion(summary="Add config_flow.py when the integration should support setup via the Home Assistant UI."),
        path=_display_path(path, context, "custom_components/<domain>/config_flow.py"),
    )


def config_flow_manifest_flag_consistent(context: ProjectContext) -> Finding:
    config_path = _config_flow_path(context)
    manifest_path = _manifest_path(context)
    if config_path is None or manifest_path is None:
        return Finding(
            rule_id="config_flow.manifest_flag_consistent",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title="config_flow.py and manifest config_flow flag agree",
            message="No integration directory was detected, so config flow consistency cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect config flow consistency.",
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(summary="Create custom_components/<domain>/ and manifest.json first."),
            path="custom_components/<domain>/",
        )

    manifest, error = _read_manifest(context)
    if manifest is None and error is None:
        return Finding(
            rule_id="config_flow.manifest_flag_consistent",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title="config_flow.py and manifest config_flow flag agree",
            message="manifest.json is missing, so config_flow metadata cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.json must exist before HassCheck can inspect config_flow metadata.",
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(summary="Create manifest.json first, then define config_flow when needed."),
            path=_display_path(manifest_path, context, "custom_components/<domain>/manifest.json"),
        )

    if error is not None:
        return Finding(
            rule_id="config_flow.manifest_flag_consistent",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.REQUIRED,
            title="config_flow.py and manifest config_flow flag agree",
            message=f"manifest.json is not valid JSON: {error}.",
            applicability=Applicability(reason="manifest.json exists but cannot be parsed."),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(summary="Fix manifest.json syntax, then rerun HassCheck."),
            path=_display_path(manifest_path, context, "custom_components/<domain>/manifest.json"),
        )

    has_file = config_path.is_file()
    manifest_flag = manifest.get("config_flow") is True if manifest else False

    if has_file and manifest_flag:
        return Finding(
            rule_id="config_flow.manifest_flag_consistent",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.PASS,
            severity=RuleSeverity.REQUIRED,
            title="config_flow.py and manifest config_flow flag agree",
            message="config_flow.py exists and manifest.json sets config_flow: true.",
            applicability=Applicability(reason="Home Assistant needs both config_flow.py and manifest config_flow metadata."),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=None,
            path=_display_path(config_path, context, "custom_components/<domain>/config_flow.py"),
        )

    if has_file and not manifest_flag:
        return Finding(
            rule_id="config_flow.manifest_flag_consistent",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.REQUIRED,
            title="config_flow.py and manifest config_flow flag agree",
            message="config_flow.py exists, but manifest.json does not set config_flow: true.",
            applicability=Applicability(reason="Home Assistant activates config flows through manifest config_flow metadata."),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(summary="Add \"config_flow\": true to manifest.json."),
            path=_display_path(manifest_path, context, "custom_components/<domain>/manifest.json"),
        )

    if manifest_flag and not has_file:
        return Finding(
            rule_id="config_flow.manifest_flag_consistent",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.REQUIRED,
            title="config_flow.py and manifest config_flow flag agree",
            message="manifest.json sets config_flow: true, but config_flow.py is missing.",
            applicability=Applicability(reason="Home Assistant docs say config_flow.py needs to exist when config_flow is specified."),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(summary="Add config_flow.py or remove config_flow from manifest.json until UI setup is implemented."),
            path=_display_path(config_path, context, "custom_components/<domain>/config_flow.py"),
        )

    return Finding(
        rule_id="config_flow.manifest_flag_consistent",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.REQUIRED,
        title="config_flow.py and manifest config_flow flag agree",
        message="No config_flow.py file and no manifest config_flow flag were found.",
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason="The integration does not currently advertise a config flow.",
        ),
        source=RuleSource(url=CONFIG_FLOW_SOURCE),
        fix=FixSuggestion(summary="Add config_flow.py and set config_flow: true when adding UI setup support."),
        path=_display_path(manifest_path, context, "custom_components/<domain>/manifest.json"),
    )


RULES = [
    RuleDefinition(
        id="config_flow.file.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py exists",
        why="Config flows are the standard way for Home Assistant integrations to support UI setup.",
        source_url=CONFIG_FLOW_SOURCE,
        check=config_flow_file_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="config_flow.manifest_flag_consistent",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="config_flow.py and manifest config_flow flag agree",
        why="Home Assistant requires manifest config_flow metadata to match the config_flow.py implementation.",
        source_url=CONFIG_FLOW_SOURCE,
        check=config_flow_manifest_flag_consistent,
        overridable=False,
    ),
]
