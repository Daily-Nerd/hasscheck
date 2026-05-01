from __future__ import annotations

import json
from collections.abc import Callable
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

HACS_INTEGRATION_SOURCE = "https://www.hacs.xyz/docs/publish/integration/"
CATEGORY = "manifest_metadata"


def _manifest_path(context: ProjectContext):
    if context.integration_path is None:
        return None
    return context.integration_path / "manifest.json"


def _manifest_display_path(context: ProjectContext) -> str:
    path = _manifest_path(context)
    return (
        "custom_components/<domain>/manifest.json"
        if path is None
        else str(path.relative_to(context.root))
    )


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


def _not_applicable_for_missing_manifest(
    rule_id: str, title: str, field_name: str, fix_summary: str
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.REQUIRED,
        title=title,
        message=f"manifest.json is missing, so the {field_name} field cannot be inspected yet.",
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason=f"manifest.json must exist before HassCheck can inspect manifest.{field_name}.",
        ),
        source=RuleSource(url=HACS_INTEGRATION_SOURCE),
        fix=FixSuggestion(summary=fix_summary),
        path="custom_components/<domain>/manifest.json",
    )


def _invalid_manifest_finding(
    rule_id: str, title: str, error: str, path: str
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title=title,
        message=f"manifest.json is not valid JSON: {error}.",
        applicability=Applicability(
            reason="manifest.json exists but cannot be parsed."
        ),
        source=RuleSource(url=HACS_INTEGRATION_SOURCE),
        fix=FixSuggestion(summary="Fix manifest.json syntax, then rerun HassCheck."),
        path=path,
    )


def _required_string_field_rule(
    *,
    rule_id: str,
    field_name: str,
    title: str,
    present_message: str,
    missing_message: str,
    applicability_reason: str,
    fix_summary: str,
) -> Callable[[ProjectContext], Finding]:
    def check(context: ProjectContext) -> Finding:
        path = _manifest_path(context)
        display_path = _manifest_display_path(context)
        if path is None or not path.is_file():
            return _not_applicable_for_missing_manifest(
                rule_id, title, field_name, fix_summary
            )

        payload, error = _read_manifest(context)
        if error is not None:
            return _invalid_manifest_finding(rule_id, title, error, display_path)

        value = payload.get(field_name) if payload else None
        is_present = isinstance(value, str) and bool(value.strip())
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.PASS if is_present else RuleStatus.FAIL,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message=present_message if is_present else missing_message,
            applicability=Applicability(reason=applicability_reason),
            source=RuleSource(url=HACS_INTEGRATION_SOURCE),
            fix=None if is_present else FixSuggestion(summary=fix_summary),
            path=display_path,
        )

    return check


def _codeowners_rule(context: ProjectContext) -> Finding:
    path = _manifest_path(context)
    display_path = _manifest_display_path(context)
    title = "manifest.json defines codeowners"
    if path is None or not path.is_file():
        return _not_applicable_for_missing_manifest(
            "manifest.codeowners.exists",
            title,
            "codeowners",
            "Create manifest.json first, then define a non-empty codeowners list.",
        )

    payload, error = _read_manifest(context)
    if error is not None:
        return _invalid_manifest_finding(
            "manifest.codeowners.exists", title, error, display_path
        )

    value = payload.get("codeowners") if payload else None
    is_present = isinstance(value, list) and any(
        isinstance(item, str) and item.strip() for item in value
    )
    return Finding(
        rule_id="manifest.codeowners.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if is_present else RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title=title,
        message=(
            "manifest.json defines at least one code owner."
            if is_present
            else "manifest.json does not define a non-empty codeowners list."
        ),
        applicability=Applicability(
            reason="HACS expects custom integration manifests to define codeowners."
        ),
        source=RuleSource(url=HACS_INTEGRATION_SOURCE),
        fix=None
        if is_present
        else FixSuggestion(summary="Add a non-empty codeowners list to manifest.json."),
        path=display_path,
    )


manifest_domain_exists = _required_string_field_rule(
    rule_id="manifest.domain.exists",
    field_name="domain",
    title="manifest.json defines domain",
    present_message="manifest.json defines a domain.",
    missing_message="manifest.json does not define a non-empty domain.",
    applicability_reason="HACS expects custom integration manifests to define domain.",
    fix_summary="Add a stable domain field to manifest.json.",
)
manifest_name_exists = _required_string_field_rule(
    rule_id="manifest.name.exists",
    field_name="name",
    title="manifest.json defines name",
    present_message="manifest.json defines a name.",
    missing_message="manifest.json does not define a non-empty name.",
    applicability_reason="HACS expects custom integration manifests to define name.",
    fix_summary="Add a human-readable name field to manifest.json.",
)
manifest_version_exists = _required_string_field_rule(
    rule_id="manifest.version.exists",
    field_name="version",
    title="manifest.json defines version",
    present_message="manifest.json defines a version.",
    missing_message="manifest.json does not define a non-empty version.",
    applicability_reason="HACS expects custom integration manifests to define version.",
    fix_summary="Add a version field to manifest.json.",
)
manifest_documentation_exists = _required_string_field_rule(
    rule_id="manifest.documentation.exists",
    field_name="documentation",
    title="manifest.json defines documentation",
    present_message="manifest.json defines documentation.",
    missing_message="manifest.json does not define a non-empty documentation URL.",
    applicability_reason="HACS expects custom integration manifests to define documentation.",
    fix_summary="Add a documentation URL to manifest.json.",
)
manifest_issue_tracker_exists = _required_string_field_rule(
    rule_id="manifest.issue_tracker.exists",
    field_name="issue_tracker",
    title="manifest.json defines issue tracker",
    present_message="manifest.json defines an issue tracker.",
    missing_message="manifest.json does not define a non-empty issue_tracker URL.",
    applicability_reason="HACS expects custom integration manifests to define issue_tracker.",
    fix_summary="Add an issue_tracker URL to manifest.json.",
)
manifest_codeowners_exists = _codeowners_rule

# ---------------------------------------------------------------------------
# manifest.domain.matches_directory — PR1 (#51)
# Source: https://developers.home-assistant.io/docs/creating_integration_manifest
# ---------------------------------------------------------------------------

HA_MANIFEST_DOCS_URL = (
    "https://developers.home-assistant.io/docs/creating_integration_manifest"
)


def manifest_domain_matches_directory(context: ProjectContext) -> Finding:
    rule_id = "manifest.domain.matches_directory"
    title = "manifest.json domain matches integration directory"

    if context.integration_path is None:
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message="No integration directory was detected, so domain consistency cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect domain consistency.",
            ),
            source=RuleSource(url=HA_MANIFEST_DOCS_URL),
            fix=FixSuggestion(
                summary="Create custom_components/<domain>/ and manifest.json first."
            ),
            path="custom_components/<domain>/manifest.json",
        )

    manifest_path = context.integration_path / "manifest.json"
    display = str(manifest_path.relative_to(context.root))

    if not manifest_path.is_file():
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message="manifest.json is missing, so the domain field cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.json must exist before HassCheck can inspect manifest.domain.",
            ),
            source=RuleSource(url=HA_MANIFEST_DOCS_URL),
            fix=FixSuggestion(
                summary="Add manifest.json with a domain field that matches the integration directory name."
            ),
            path=display,
        )

    payload, error = _read_manifest(context)
    if error is not None:
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message=f"manifest.json is not valid JSON: {error}.",
            applicability=Applicability(
                reason="manifest.json exists but cannot be parsed."
            ),
            source=RuleSource(url=HA_MANIFEST_DOCS_URL),
            fix=FixSuggestion(
                summary="Fix manifest.json syntax, then rerun HassCheck."
            ),
            path=display,
        )

    dir_name = context.integration_path.name
    manifest_domain = payload.get("domain") if payload else None

    if isinstance(manifest_domain, str) and manifest_domain == dir_name:
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.PASS,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message=f'manifest.json domain matches integration directory "{dir_name}".',
            applicability=Applicability(
                reason="The manifest domain must match the integration directory name."
            ),
            source=RuleSource(url=HA_MANIFEST_DOCS_URL),
            fix=None,
            path=display,
        )

    manifest_domain_display = (
        manifest_domain if isinstance(manifest_domain, str) else "(missing)"
    )
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title=title,
        message=(
            f'manifest.json domain "{manifest_domain_display}" does not match '
            f'integration directory "{dir_name}".'
        ),
        applicability=Applicability(
            reason="The manifest domain must match the integration directory name."
        ),
        source=RuleSource(url=HA_MANIFEST_DOCS_URL),
        fix=FixSuggestion(
            summary=(
                "Rename the integration directory or update manifest.domain so both "
                "use the same stable domain."
            )
        ),
        path=display,
    )


def manifest_exists(context: ProjectContext) -> Finding:
    path = _manifest_path(context)
    exists = path is not None and path.is_file()
    display = _manifest_display_path(context)
    return Finding(
        rule_id="manifest.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json exists",
        message=(
            "Integration manifest exists."
            if exists
            else "Integration manifest is missing, so Home Assistant and HACS metadata cannot be inspected."
        ),
        applicability=Applicability(
            reason="Every Home Assistant integration needs a manifest.json file."
        ),
        source=RuleSource(url=HACS_INTEGRATION_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add custom_components/<domain>/manifest.json with the required integration metadata."
        ),
        path=display,
    )


RULES = [
    RuleDefinition(
        id="manifest.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json exists",
        why="Home Assistant integrations use manifest.json for integration metadata.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="manifest.domain.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines domain",
        why="The domain is the stable integration identifier used by Home Assistant and HACS.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_domain_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="manifest.name.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines name",
        why="The name is the human-readable integration label exposed in Home Assistant and HACS metadata.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_name_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="manifest.version.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines version",
        why="HACS expects custom integration manifests to include a version for release and update metadata.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_version_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="manifest.documentation.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines documentation",
        why="Documentation gives users and HACS a stable path to setup and support information.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_documentation_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="manifest.issue_tracker.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines issue tracker",
        why="An issue tracker gives users a clear support path for custom integration problems.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_issue_tracker_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="manifest.codeowners.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json defines codeowners",
        why="Code owners make maintainership explicit and are expected by HACS integration metadata.",
        source_url=HACS_INTEGRATION_SOURCE,
        check=manifest_codeowners_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="manifest.domain.matches_directory",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json domain matches integration directory",
        why=(
            "The manifest domain must match the name of the integration directory under "
            "custom_components/. A mismatch causes Home Assistant to silently misidentify "
            "the integration, breaking HACS discovery and core platform loading. "
            "Note: this rule cannot be overridden via hasscheck.yaml."
        ),
        source_url=HA_MANIFEST_DOCS_URL,
        check=manifest_domain_matches_directory,
        overridable=False,
    ),
]
