from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from packaging.requirements import InvalidRequirement, Requirement

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

# ---------------------------------------------------------------------------
# PR2 (#52) — iot_class + integration_type enum constants
# Source: https://developers.home-assistant.io/docs/creating_integration_manifest
# Source-checked-at: 2026-05-01
# ---------------------------------------------------------------------------

_HA_DEV_DOCS_URL = (
    "https://developers.home-assistant.io/docs/creating_integration_manifest"
)
_SOURCE_CHECKED_AT = "2026-05-01"

# Canonical iot_class values — anchor #iot-class
# Source: https://developers.home-assistant.io/docs/creating_integration_manifest#iot-class
# Verified: 2026-05-01
_VALID_IOT_CLASSES: frozenset[str] = frozenset(
    {
        "assumed_state",
        "calculated",
        "cloud_polling",
        "cloud_push",
        "local_polling",
        "local_push",
    }
)

# Canonical integration_type values — anchor #integration-type
# Source: https://developers.home-assistant.io/docs/creating_integration_manifest#integration-type
# Verified: 2026-05-01
_VALID_INTEGRATION_TYPES: frozenset[str] = frozenset(
    {
        "device",
        "entity",
        "hardware",
        "helper",
        "hub",
        "service",
        "system",
        "virtual",
    }
)


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

    return cast(dict[str, Any], payload), None


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
        isinstance(item, str) and item.strip() for item in cast(list[Any], value)
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


# ---------------------------------------------------------------------------
# PR2 (#52) — _required_enum_field_rule factory
# Generates both the *.exists and *.valid variants for a manifest field
# that must belong to a known frozenset of string values.
# ---------------------------------------------------------------------------


def _required_enum_field_rule(
    *,
    exists_rule_id: str,
    valid_rule_id: str,
    field_name: str,
    exists_title: str,
    valid_title: str,
    exists_warn_message: str,
    valid_values: frozenset[str],
    valid_sorted_display: str,
    fix_exists_summary: str,
    fix_valid_summary: str,
    # why_exists and why_valid are used in RuleDefinition directly — not inside checks
    why_exists: str = "",
    why_valid: str = "",
) -> tuple[Callable[[ProjectContext], Finding], Callable[[ProjectContext], Finding]]:
    """Return (exists_check, valid_check) for a manifest enum field.

    exists semantics:
      - NOT_APPLICABLE if no manifest (missing or no integration path)
      - FAIL if manifest JSON is broken
      - PASS if field is present (any non-empty string)
      - WARN if field is absent

    valid semantics:
      - NOT_APPLICABLE if no manifest OR field is absent
      - PASS if field value is in valid_values
      - FAIL if field value is present but not in valid_values
    """

    def exists_check(context: ProjectContext) -> Finding:
        path = _manifest_path(context)
        display = _manifest_display_path(context)

        if path is None or not path.is_file():
            return Finding(
                rule_id=exists_rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.NOT_APPLICABLE,
                severity=RuleSeverity.RECOMMENDED,
                title=exists_title,
                message=f"manifest.json is missing, so the {field_name} field cannot be inspected yet.",
                applicability=Applicability(
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason=f"manifest.json must exist before HassCheck can inspect manifest.{field_name}.",
                ),
                source=RuleSource(url=_HA_DEV_DOCS_URL),
                fix=FixSuggestion(summary=fix_exists_summary),
                path="custom_components/<domain>/manifest.json",
            )

        payload, error = _read_manifest(context)
        if error is not None:
            return Finding(
                rule_id=exists_rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.FAIL,
                severity=RuleSeverity.RECOMMENDED,
                title=exists_title,
                message=f"manifest.json is not valid JSON: {error}.",
                applicability=Applicability(
                    reason="manifest.json exists but cannot be parsed."
                ),
                source=RuleSource(url=_HA_DEV_DOCS_URL),
                fix=FixSuggestion(
                    summary="Fix manifest.json syntax, then rerun HassCheck."
                ),
                path=display,
            )

        value = payload.get(field_name) if payload else None
        is_present = isinstance(value, str) and bool(value.strip())

        if is_present:
            return Finding(
                rule_id=exists_rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.PASS,
                severity=RuleSeverity.RECOMMENDED,
                title=exists_title,
                message=f"manifest.json declares {field_name}.",
                applicability=Applicability(
                    reason=f"Declaring {field_name} classifies the integration for Home Assistant discovery."
                ),
                source=RuleSource(url=_HA_DEV_DOCS_URL),
                fix=None,
                path=display,
            )

        return Finding(
            rule_id=exists_rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.WARN,
            severity=RuleSeverity.RECOMMENDED,
            title=exists_title,
            message=exists_warn_message,
            applicability=Applicability(
                reason=f"Declaring {field_name} is recommended for Home Assistant integrations."
            ),
            source=RuleSource(url=_HA_DEV_DOCS_URL),
            fix=FixSuggestion(summary=fix_exists_summary),
            path=display,
        )

    def valid_check(context: ProjectContext) -> Finding:
        path = _manifest_path(context)
        display = _manifest_display_path(context)

        if path is None or not path.is_file():
            return Finding(
                rule_id=valid_rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.NOT_APPLICABLE,
                severity=RuleSeverity.RECOMMENDED,
                title=valid_title,
                message=f"manifest.json is missing, so the {field_name} field cannot be validated.",
                applicability=Applicability(
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason=f"manifest.json must exist before HassCheck can validate manifest.{field_name}.",
                ),
                source=RuleSource(url=_HA_DEV_DOCS_URL),
                fix=FixSuggestion(summary=fix_exists_summary),
                path="custom_components/<domain>/manifest.json",
            )

        payload, error = _read_manifest(context)
        if error is not None:
            # Broken manifest: exists rule FAILs, valid rule is NOT_APPLICABLE
            return Finding(
                rule_id=valid_rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.NOT_APPLICABLE,
                severity=RuleSeverity.RECOMMENDED,
                title=valid_title,
                message=f"manifest.json could not be parsed; {field_name} validation is skipped.",
                applicability=Applicability(
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason="manifest.json must be valid JSON before field values can be validated.",
                ),
                source=RuleSource(url=_HA_DEV_DOCS_URL),
                fix=FixSuggestion(
                    summary="Fix manifest.json syntax, then rerun HassCheck."
                ),
                path=display,
            )

        value = payload.get(field_name) if payload else None

        if not isinstance(value, str) or not value.strip():
            # Field absent → not applicable for the valid rule
            return Finding(
                rule_id=valid_rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.NOT_APPLICABLE,
                severity=RuleSeverity.RECOMMENDED,
                title=valid_title,
                message=f"manifest.json does not declare {field_name}; value validation is skipped.",
                applicability=Applicability(
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason=f"manifest.{field_name} must be present before its value can be validated.",
                ),
                source=RuleSource(url=_HA_DEV_DOCS_URL),
                fix=FixSuggestion(summary=fix_exists_summary),
                path=display,
            )

        if value in valid_values:
            return Finding(
                rule_id=valid_rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.PASS,
                severity=RuleSeverity.RECOMMENDED,
                title=valid_title,
                message=f'manifest.json {field_name} "{value}" is a recognized value.',
                applicability=Applicability(
                    reason=f"manifest.{field_name} must be one of the values defined in the HA integration manifest docs."
                ),
                source=RuleSource(url=_HA_DEV_DOCS_URL),
                fix=None,
                path=display,
            )

        return Finding(
            rule_id=valid_rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.RECOMMENDED,
            title=valid_title,
            message=(
                f'manifest.json {field_name} "{value}" is not a recognized value '
                f"(expected one of: {valid_sorted_display})."
            ),
            applicability=Applicability(
                reason=f"manifest.{field_name} must be one of the values defined in the HA integration manifest docs."
            ),
            source=RuleSource(url=_HA_DEV_DOCS_URL),
            fix=FixSuggestion(summary=fix_valid_summary),
            path=display,
        )

    return exists_check, valid_check


_IOT_CLASS_EXISTS_WHY = (
    "iot_class describes how the integration fetches data (polling vs. push, "
    "cloud vs. local). Home Assistant uses this value to set user expectations "
    "about connectivity and latency. "
    f"Source: {_HA_DEV_DOCS_URL} (verified {_SOURCE_CHECKED_AT})."
)
_IOT_CLASS_VALID_WHY = (
    "iot_class must be one of the canonical values defined in the Home Assistant "
    "integration manifest docs. An unrecognised value may cause HA to silently "
    "ignore the field or display incorrect information. "
    f"Source: {_HA_DEV_DOCS_URL} (verified {_SOURCE_CHECKED_AT})."
)
_INTEGRATION_TYPE_EXISTS_WHY = (
    "integration_type classifies how the integration fits into the Home Assistant "
    "architecture (hub, device, helper, etc.). Required for integrations with a "
    "config flow; custom integrations default to 'hub' when omitted. "
    f"Source: {_HA_DEV_DOCS_URL} (verified {_SOURCE_CHECKED_AT})."
)
_INTEGRATION_TYPE_VALID_WHY = (
    "integration_type must be one of the canonical values defined in the Home Assistant "
    "integration manifest docs. An unrecognised value is rejected by the core manifest "
    "loader in newer HA versions. "
    f"Source: {_HA_DEV_DOCS_URL} (verified {_SOURCE_CHECKED_AT})."
)

_iot_class_exists_check, _iot_class_valid_check = _required_enum_field_rule(
    exists_rule_id="manifest.iot_class.exists",
    valid_rule_id="manifest.iot_class.valid",
    field_name="iot_class",
    exists_title="manifest.json declares iot_class",
    valid_title="manifest.json iot_class is a recognized value",
    exists_warn_message=(
        "manifest.json does not declare iot_class; recommended for Home Assistant integrations."
    ),
    valid_values=_VALID_IOT_CLASSES,
    valid_sorted_display="assumed_state, calculated, cloud_polling, cloud_push, local_polling, local_push",
    fix_exists_summary="Add an iot_class field to manifest.json.",
    fix_valid_summary=(
        "Set iot_class to one of: assumed_state, calculated, cloud_polling, "
        "cloud_push, local_polling, local_push."
    ),
    why_exists=_IOT_CLASS_EXISTS_WHY,
    why_valid=_IOT_CLASS_VALID_WHY,
)

_integration_type_exists_check, _integration_type_valid_check = (
    _required_enum_field_rule(
        exists_rule_id="manifest.integration_type.exists",
        valid_rule_id="manifest.integration_type.valid",
        field_name="integration_type",
        exists_title="manifest.json declares integration_type",
        valid_title="manifest.json integration_type is a recognized value",
        exists_warn_message=(
            "manifest.json does not declare integration_type; recommended for Home Assistant integrations."
        ),
        valid_values=_VALID_INTEGRATION_TYPES,
        valid_sorted_display="device, entity, hardware, helper, hub, service, system, virtual",
        fix_exists_summary="Add an integration_type field to manifest.json.",
        fix_valid_summary=(
            "Set integration_type to one of: device, entity, hardware, helper, hub, service, system, virtual."
        ),
        why_exists=_INTEGRATION_TYPE_EXISTS_WHY,
        why_valid=_INTEGRATION_TYPE_VALID_WHY,
    )
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


# ---------------------------------------------------------------------------
# Issue #100 — manifest.requirements sanity checks
# Source: https://developers.home-assistant.io/docs/creating_integration_manifest/#requirements
# Source-checked-at: 2026-05-01
# ---------------------------------------------------------------------------

_HA_REQUIREMENTS_DOCS_URL = (
    "https://developers.home-assistant.io/docs/creating_integration_manifest"
    "#requirements"
)

_PEP_508_URL_PREFIXES = ("git+", "http://", "https://", "file://")

RULE_ID_REQUIREMENTS_IS_LIST = "manifest.requirements.is_list"
RULE_ID_REQUIREMENTS_WELL_FORMED = "manifest.requirements.entries_well_formed"
RULE_ID_REQUIREMENTS_NO_GIT = "manifest.requirements.no_git_or_url_specs"

_REQUIREMENTS_WHY_IS_LIST = (
    "Home Assistant's manifest loader requires requirements to be a JSON array. "
    "A non-array value will cause a hard error during integration loading. "
    f"Source: {_HA_REQUIREMENTS_DOCS_URL} (verified 2026-05-01)."
)
_REQUIREMENTS_WHY_WELL_FORMED = (
    "Each entry in requirements must be a valid PEP 508 specifier so pip can "
    "resolve and install the dependency. Malformed specifiers will fail at "
    "integration install time. "
    f"Source: {_HA_REQUIREMENTS_DOCS_URL} (verified 2026-05-01)."
)
_REQUIREMENTS_WHY_NO_GIT = (
    "Direct git+ or URL-based install specs are not supported by HACS and may "
    "fail in sandboxed or offline HA installations. Publish packages to PyPI and "
    "reference them by name instead. "
    f"Source: {_HA_REQUIREMENTS_DOCS_URL} (verified 2026-05-01)."
)


def _is_url_or_git_spec(entry: str) -> bool:
    """Return True if *entry* is a direct URL / VCS spec that PEP 508 cannot parse."""
    s = entry.strip()
    return s.startswith(_PEP_508_URL_PREFIXES) or "@ git+" in s


def _manifest_requirements_is_list(context: ProjectContext) -> Finding:
    rule_id = RULE_ID_REQUIREMENTS_IS_LIST
    title = "manifest.json requirements is a JSON array"
    path = _manifest_path(context)
    display = _manifest_display_path(context)

    if path is None or not path.is_file():
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message="manifest.json is missing, so the requirements field cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.json must exist before HassCheck can inspect manifest.requirements.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=FixSuggestion(summary="Create manifest.json first."),
            path="custom_components/<domain>/manifest.json",
        )

    payload, error = _read_manifest(context)
    if error is not None:
        return _invalid_manifest_finding(rule_id, title, error, display)

    assert payload is not None
    if "requirements" not in payload:
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message="manifest.json has no requirements key; rule is not applicable.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.requirements must be present before its type can be validated.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=None,
            path=display,
        )

    value = payload["requirements"]
    if isinstance(value, list):
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.PASS,
            severity=RuleSeverity.REQUIRED,
            title=title,
            message="manifest.requirements is a JSON array.",
            applicability=Applicability(
                reason="Home Assistant expects requirements to be a JSON array of PEP 508 strings."
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=None,
            path=display,
        )

    type_name = type(value).__name__
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title=title,
        message=f"manifest.requirements must be a JSON array, got {type_name}.",
        applicability=Applicability(
            reason="Home Assistant expects requirements to be a JSON array of PEP 508 strings."
        ),
        source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
        fix=FixSuggestion(summary="Change manifest.requirements to a JSON array."),
        path=display,
    )


def _manifest_requirements_entries_well_formed(context: ProjectContext) -> Finding:
    rule_id = RULE_ID_REQUIREMENTS_WELL_FORMED
    title = "manifest.json requirements entries are valid PEP 508 specifiers"
    path = _manifest_path(context)
    display = _manifest_display_path(context)

    if path is None or not path.is_file():
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message="manifest.json is missing, so requirements entries cannot be validated.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.json must exist before HassCheck can validate requirements entries.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=FixSuggestion(summary="Create manifest.json first."),
            path="custom_components/<domain>/manifest.json",
        )

    payload, error = _read_manifest(context)
    if error is not None:
        return _invalid_manifest_finding(rule_id, title, error, display)

    assert payload is not None

    if "requirements" not in payload:
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message="manifest.json has no requirements key; rule is not applicable.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.requirements must be present before entries can be validated.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=None,
            path=display,
        )

    value = payload["requirements"]

    if not isinstance(value, list):
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message="manifest.requirements is not a list; entry validation is skipped.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.requirements must be a list before entries can be validated.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=None,
            path=display,
        )

    # Empty list is trivially valid
    for entry in value:
        if not isinstance(entry, str):
            type_name = type(entry).__name__
            return Finding(
                rule_id=rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.FAIL,
                severity=RuleSeverity.RECOMMENDED,
                title=title,
                message=(
                    f"manifest.requirements contains a non-string entry of type {type_name}; "
                    "expected a PEP 508 string."
                ),
                applicability=Applicability(
                    reason="Each requirements entry must be a PEP 508 string."
                ),
                source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
                fix=FixSuggestion(
                    summary="Replace non-string requirements entries with PEP 508 specifier strings."
                ),
                path=display,
            )
        # Skip URL / VCS specs — rule 3 handles those; PEP 508 parser rejects them.
        if _is_url_or_git_spec(entry):
            continue
        try:
            Requirement(entry)
        except InvalidRequirement:
            return Finding(
                rule_id=rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.FAIL,
                severity=RuleSeverity.RECOMMENDED,
                title=title,
                message=(
                    f'manifest.requirements entry "{entry}" is not a valid PEP 508 specifier.'
                ),
                applicability=Applicability(
                    reason="Each requirements entry must be a valid PEP 508 specifier string."
                ),
                source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
                fix=FixSuggestion(
                    summary="Fix or remove the invalid PEP 508 specifier from requirements."
                ),
                path=display,
            )

    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS,
        severity=RuleSeverity.RECOMMENDED,
        title=title,
        message="All manifest.requirements entries are valid PEP 508 specifiers.",
        applicability=Applicability(
            reason="Each requirements entry must be a valid PEP 508 specifier string."
        ),
        source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
        fix=None,
        path=display,
    )


def _manifest_requirements_no_git_or_url_specs(context: ProjectContext) -> Finding:
    rule_id = RULE_ID_REQUIREMENTS_NO_GIT
    title = "manifest.json requirements contains no git/URL install specs"
    path = _manifest_path(context)
    display = _manifest_display_path(context)

    if path is None or not path.is_file():
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message="manifest.json is missing, so requirements cannot be inspected.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.json must exist before HassCheck can inspect requirements.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=FixSuggestion(summary="Create manifest.json first."),
            path="custom_components/<domain>/manifest.json",
        )

    payload, error = _read_manifest(context)
    if error is not None:
        return _invalid_manifest_finding(rule_id, title, error, display)

    assert payload is not None

    if "requirements" not in payload:
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message="manifest.json has no requirements key; rule is not applicable.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.requirements must be present before it can be inspected.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=None,
            path=display,
        )

    value = payload["requirements"]

    if not isinstance(value, list):
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message="manifest.requirements is not a list; rule is not applicable.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="manifest.requirements must be a list before entries can be inspected.",
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=None,
            path=display,
        )

    flagged = [
        entry
        for entry in value
        if isinstance(entry, str) and _is_url_or_git_spec(entry)
    ]

    if flagged:
        flagged_display = ", ".join(flagged)
        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.WARN,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message=(
                f"manifest.requirements contains non-PyPI install specs: {flagged_display}. "
                "Use PyPI package names to ensure installability via HACS and pip."
            ),
            applicability=Applicability(
                reason=(
                    "Direct git/URL specs cannot be installed in all environments "
                    "and are not supported by HACS."
                )
            ),
            source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
            fix=FixSuggestion(
                summary="Replace git/URL specs with published PyPI package names."
            ),
            path=display,
        )

    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS,
        severity=RuleSeverity.RECOMMENDED,
        title=title,
        message="manifest.requirements contains no git/URL install specs.",
        applicability=Applicability(
            reason=(
                "Direct git/URL specs cannot be installed in all environments "
                "and are not supported by HACS."
            )
        ),
        source=RuleSource(url=_HA_REQUIREMENTS_DOCS_URL),
        fix=None,
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
    # PR2 (#52) — iot_class and integration_type validation
    RuleDefinition(
        id="manifest.iot_class.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="manifest.json declares iot_class",
        why=_IOT_CLASS_EXISTS_WHY,
        source_url=_HA_DEV_DOCS_URL,
        check=_iot_class_exists_check,
        overridable=True,
    ),
    RuleDefinition(
        id="manifest.iot_class.valid",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="manifest.json iot_class is a recognized value",
        why=_IOT_CLASS_VALID_WHY,
        source_url=_HA_DEV_DOCS_URL,
        check=_iot_class_valid_check,
        overridable=True,
    ),
    RuleDefinition(
        id="manifest.integration_type.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="manifest.json declares integration_type",
        why=_INTEGRATION_TYPE_EXISTS_WHY,
        source_url=_HA_DEV_DOCS_URL,
        check=_integration_type_exists_check,
        overridable=True,
    ),
    RuleDefinition(
        id="manifest.integration_type.valid",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="manifest.json integration_type is a recognized value",
        why=_INTEGRATION_TYPE_VALID_WHY,
        source_url=_HA_DEV_DOCS_URL,
        check=_integration_type_valid_check,
        overridable=True,
    ),
    # Issue #100 — manifest.requirements sanity checks
    RuleDefinition(
        id=RULE_ID_REQUIREMENTS_IS_LIST,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.REQUIRED,
        title="manifest.json requirements is a JSON array",
        why=_REQUIREMENTS_WHY_IS_LIST,
        source_url=_HA_REQUIREMENTS_DOCS_URL,
        check=_manifest_requirements_is_list,
        overridable=False,
    ),
    RuleDefinition(
        id=RULE_ID_REQUIREMENTS_WELL_FORMED,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="manifest.json requirements entries are valid PEP 508 specifiers",
        why=_REQUIREMENTS_WHY_WELL_FORMED,
        source_url=_HA_REQUIREMENTS_DOCS_URL,
        check=_manifest_requirements_entries_well_formed,
        overridable=True,
    ),
    RuleDefinition(
        id=RULE_ID_REQUIREMENTS_NO_GIT,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="manifest.json requirements contains no git/URL install specs",
        why=_REQUIREMENTS_WHY_NO_GIT,
        source_url=_HA_REQUIREMENTS_DOCS_URL,
        check=_manifest_requirements_no_git_or_url_specs,
        overridable=True,
    ),
]
