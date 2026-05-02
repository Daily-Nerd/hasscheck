from __future__ import annotations

import ast
import json
from collections.abc import Iterable
from typing import Any

from hasscheck.ast_utils import parse_module
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
CONFIG_FLOW_SOURCE = (
    "https://developers.home-assistant.io/docs/core/integration/config_flow"
)
# Source: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
# _SOURCE_CHECKED_AT = "2026-05-01"
USER_STEP_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_config_flow_handler/"
    "#defining-the-flow"
)
MANIFEST_SOURCE = (
    "https://developers.home-assistant.io/docs/creating_integration_manifest"
)

# ---------------------------------------------------------------------------
# Constants for advanced detection rules (#101)
# ---------------------------------------------------------------------------
_REAUTH_STEP_NAMES = frozenset({"async_step_reauth", "async_step_reauth_confirm"})
_DISCOVERY_FLOW_STEPS = frozenset(
    {
        "async_step_user",
        "async_step_zeroconf",
        "async_step_dhcp",
        "async_step_bluetooth",
        "async_step_usb",
    }
)
# Calls that count as flow plumbing only — not real connection work
_FLOW_PLUMBING_CALLS = frozenset(
    {
        "async_show_form",
        "async_create_entry",
        "async_abort",
        "async_set_unique_id",
        "_abort_if_unique_id_configured",
    }
)

_REAUTH_STEP_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_config_flow_handler/"
    "#reauthentication"
)
_RECONFIGURE_STEP_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_config_flow_handler/"
    "#reconfigure"
)
_UNIQUE_ID_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_config_flow_handler/"
    "#unique-ids"
)
_CONNECTION_TEST_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_config_flow_handler/"
    "#defining-the-flow"
)


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


def _has_async_function(tree: ast.Module, name: str) -> bool:
    """Return True if tree contains any AsyncFunctionDef with the given name.

    Uses ast.walk so it finds the function at any nesting depth
    (module-level or as a class method).
    """
    return any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == name
        for node in ast.walk(tree)
    )


def _has_async_function_any(tree: ast.Module, names: Iterable[str]) -> bool:
    """True if any AsyncFunctionDef matches one of the given names."""
    name_set = frozenset(names)
    return any(
        isinstance(node, ast.AsyncFunctionDef) and node.name in name_set
        for node in ast.walk(tree)
    )


def _module_calls_name(tree: ast.Module, target: str) -> bool:
    """True if any Call's func is a Name(id=target) or Attribute(attr=target)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == target:
            return True
        if isinstance(func, ast.Attribute) and func.attr == target:
            return True
    return False


def _has_connection_test(tree: ast.Module) -> bool:
    """True if any discovery-flow step awaits a non-plumbing call.

    Scans all AsyncFunctionDef nodes whose name is in _DISCOVERY_FLOW_STEPS.
    Inside each, looks for Await expressions on a Call where the callee is
    not a flow-step name (async_step_*) and not in _FLOW_PLUMBING_CALLS.
    Any such awaited call is considered real connection work.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if node.name not in _DISCOVERY_FLOW_STEPS:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Await):
                continue
            call = inner.value
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if isinstance(func, ast.Name):
                callee = func.id
            elif isinstance(func, ast.Attribute):
                callee = func.attr
            else:
                continue
            # async_step_* calls are flow routing — not connection work
            if callee.startswith("async_step_"):
                continue
            if callee in _FLOW_PLUMBING_CALLS:
                continue
            return True
    return False


def config_flow_user_step_exists(context: ProjectContext) -> Finding:
    """Check that config_flow.py defines async_step_user."""
    # Guard: no integration directory
    if context.integration_path is None:
        return Finding(
            rule_id="config_flow.user_step.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="config_flow.py defines async_step_user",
            message="No integration directory was detected.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect config_flow.py.",
            ),
            source=RuleSource(url=USER_STEP_SOURCE),
            fix=None,
            path="custom_components/<domain>/config_flow.py",
        )

    config_flow_path = context.integration_path / "config_flow.py"

    # Guard: applicability flag opts out
    if context.applicability and context.applicability.uses_config_flow is False:
        return Finding(
            rule_id="config_flow.user_step.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="config_flow.py defines async_step_user",
            message="Project config declares this integration does not use config flow UI setup.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="hasscheck.yaml declares uses_config_flow: false.",
                source="config",
            ),
            source=RuleSource(url=USER_STEP_SOURCE),
            fix=None,
            path=_display_path(
                config_flow_path, context, "custom_components/<domain>/config_flow.py"
            ),
        )

    # Guard: config_flow.py does not exist
    if not config_flow_path.is_file():
        return Finding(
            rule_id="config_flow.user_step.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="config_flow.py defines async_step_user",
            message="config_flow.py does not exist; async_step_user presence cannot be checked.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="config_flow.py must exist before this rule can run.",
            ),
            source=RuleSource(url=USER_STEP_SOURCE),
            fix=None,
            path=_display_path(
                config_flow_path, context, "custom_components/<domain>/config_flow.py"
            ),
        )

    # Parse the file
    tree, error = parse_module(config_flow_path)

    if error is not None:
        return Finding(
            rule_id="config_flow.user_step.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.WARN,
            severity=RuleSeverity.RECOMMENDED,
            title="config_flow.py defines async_step_user",
            message=f"config_flow.py could not be parsed ({error}); async_step_user presence cannot be determined.",
            applicability=Applicability(
                reason="config_flow.py exists but has a syntax error."
            ),
            source=RuleSource(url=USER_STEP_SOURCE),
            fix=FixSuggestion(summary="Fix syntax errors in config_flow.py."),
            path=_display_path(
                config_flow_path, context, "custom_components/<domain>/config_flow.py"
            ),
        )

    # error is None here, so tree must be a parsed Module
    assert tree is not None
    if _has_async_function(tree, "async_step_user"):
        return Finding(
            rule_id="config_flow.user_step.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.PASS,
            severity=RuleSeverity.RECOMMENDED,
            title="config_flow.py defines async_step_user",
            message="config_flow.py defines async_step_user.",
            applicability=Applicability(
                reason="async_step_user is the standard entry point for UI-driven config flow setup."
            ),
            source=RuleSource(url=USER_STEP_SOURCE),
            fix=None,
            path=_display_path(
                config_flow_path, context, "custom_components/<domain>/config_flow.py"
            ),
        )

    return Finding(
        rule_id="config_flow.user_step.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py defines async_step_user",
        message="config_flow.py does not define async_step_user; users cannot start setup from the UI.",
        applicability=Applicability(
            reason="async_step_user is the standard entry point for UI-driven config flow setup."
        ),
        source=RuleSource(url=USER_STEP_SOURCE),
        fix=FixSuggestion(
            summary="Add async_step_user to your ConfigFlow class in config_flow.py.",
            docs_url=USER_STEP_SOURCE,
        ),
        path=_display_path(
            config_flow_path, context, "custom_components/<domain>/config_flow.py"
        ),
    )


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
            fix=FixSuggestion(
                summary="Create custom_components/<domain>/ before adding config_flow.py."
            ),
            path="custom_components/<domain>/config_flow.py",
        )

    exists = path.is_file()
    if (
        not exists
        and context.applicability
        and context.applicability.uses_config_flow is False
    ):
        return Finding(
            rule_id="config_flow.file.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="config_flow.py exists",
            message="Project config declares this integration does not use config flow UI setup.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="hasscheck.yaml declares uses_config_flow: false.",
                source="config",
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=None,
            path=_display_path(
                path, context, "custom_components/<domain>/config_flow.py"
            ),
        )

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
        applicability=Applicability(
            reason="Config flows are the standard way to set up integrations via the UI."
        ),
        source=RuleSource(url=CONFIG_FLOW_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add config_flow.py when the integration should support setup via the Home Assistant UI."
        ),
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
            fix=FixSuggestion(
                summary="Create custom_components/<domain>/ and manifest.json first."
            ),
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
            fix=FixSuggestion(
                summary="Create manifest.json first, then define config_flow when needed."
            ),
            path=_display_path(
                manifest_path, context, "custom_components/<domain>/manifest.json"
            ),
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
            applicability=Applicability(
                reason="manifest.json exists but cannot be parsed."
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(
                summary="Fix manifest.json syntax, then rerun HassCheck."
            ),
            path=_display_path(
                manifest_path, context, "custom_components/<domain>/manifest.json"
            ),
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
            applicability=Applicability(
                reason="Home Assistant needs both config_flow.py and manifest config_flow metadata."
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=None,
            path=_display_path(
                config_path, context, "custom_components/<domain>/config_flow.py"
            ),
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
            applicability=Applicability(
                reason="Home Assistant activates config flows through manifest config_flow metadata."
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(summary='Add "config_flow": true to manifest.json.'),
            path=_display_path(
                manifest_path, context, "custom_components/<domain>/manifest.json"
            ),
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
            applicability=Applicability(
                reason="Home Assistant docs say config_flow.py needs to exist when config_flow is specified."
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=FixSuggestion(
                summary="Add config_flow.py or remove config_flow from manifest.json until UI setup is implemented."
            ),
            path=_display_path(
                config_path, context, "custom_components/<domain>/config_flow.py"
            ),
        )

    if context.applicability and context.applicability.uses_config_flow is False:
        return Finding(
            rule_id="config_flow.manifest_flag_consistent",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.REQUIRED,
            title="config_flow.py and manifest config_flow flag agree",
            message="Project config declares this integration does not use config flow UI setup.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="hasscheck.yaml declares uses_config_flow: false.",
                source="config",
            ),
            source=RuleSource(url=CONFIG_FLOW_SOURCE),
            fix=None,
            path=_display_path(
                manifest_path, context, "custom_components/<domain>/manifest.json"
            ),
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
        fix=FixSuggestion(
            summary="Add config_flow.py and set config_flow: true when adding UI setup support."
        ),
        path=_display_path(
            manifest_path, context, "custom_components/<domain>/manifest.json"
        ),
    )


_USER_STEP_WHY = (
    "async_step_user is the standard entry point for Home Assistant config flows "
    "initiated by the user from the UI. Without it, users cannot set up this "
    "integration from Settings → Devices & Services. "
    "Note: this rule uses AST inspection and cannot detect async_step_user that is "
    "defined only in a base class, mixin, or via dynamic attribute assignment — "
    "those cases will produce a false WARN."
)


# ---------------------------------------------------------------------------
# Helper: shared NOT_APPLICABLE / gating logic for v0.10 AST rules
# ---------------------------------------------------------------------------


def _make_not_applicable_finding(
    rule_id: str,
    title: str,
    source_url: str,
    message: str,
    reason: str,
    path: str,
    applicability_source: str | None = None,
    fix: FixSuggestion | None = None,
) -> Finding:
    applicability_kwargs: dict = {
        "status": ApplicabilityStatus.NOT_APPLICABLE,
        "reason": reason,
    }
    if applicability_source is not None:
        applicability_kwargs["source"] = applicability_source
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.RECOMMENDED,
        title=title,
        message=message,
        applicability=Applicability(**applicability_kwargs),
        source=RuleSource(url=source_url),
        fix=fix,
        path=path,
    )


def _make_ast_rule_finding(
    rule_id: str,
    title: str,
    source_url: str,
    *,
    status: RuleStatus,
    message: str,
    reason: str,
    path: str,
    fix: FixSuggestion | None = None,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=status,
        severity=RuleSeverity.RECOMMENDED,
        title=title,
        message=message,
        applicability=Applicability(reason=reason),
        source=RuleSource(url=source_url),
        fix=fix,
        path=path,
    )


def _gate_config_flow_ast_rule(
    context: ProjectContext,
    rule_id: str,
    title: str,
    source_url: str,
) -> tuple[Finding | None, ast.Module | None, str]:
    """Shared gating: check integration_path, applicability, file existence, parse.

    Returns (early_finding, tree, display_path).
    If early_finding is not None, the caller should return it immediately.
    """
    fallback_path = "custom_components/<domain>/config_flow.py"

    if context.integration_path is None:
        return (
            _make_not_applicable_finding(
                rule_id,
                title,
                source_url,
                message="No integration directory was detected.",
                reason="custom_components/<domain>/ must exist before HassCheck can inspect config_flow.py.",
                path=fallback_path,
            ),
            None,
            fallback_path,
        )

    config_flow_path = context.integration_path / "config_flow.py"
    display = _display_path(config_flow_path, context, fallback_path)

    if context.applicability and context.applicability.uses_config_flow is False:
        return (
            _make_not_applicable_finding(
                rule_id,
                title,
                source_url,
                message="Project config declares this integration does not use config flow UI setup.",
                reason="hasscheck.yaml declares uses_config_flow: false.",
                path=display,
                applicability_source="config",
            ),
            None,
            display,
        )

    if not config_flow_path.is_file():
        return (
            _make_not_applicable_finding(
                rule_id,
                title,
                source_url,
                message="config_flow.py does not exist; this rule cannot be checked.",
                reason="config_flow.py must exist before this rule can run.",
                path=display,
            ),
            None,
            display,
        )

    tree, error = parse_module(config_flow_path)
    if error is not None:
        return (
            _make_ast_rule_finding(
                rule_id,
                title,
                source_url,
                status=RuleStatus.WARN,
                message=f"config_flow.py could not be parsed ({error}); {title.lower()} cannot be determined.",
                reason="config_flow.py exists but has a syntax error.",
                path=display,
                fix=FixSuggestion(summary="Fix syntax errors in config_flow.py."),
            ),
            None,
            display,
        )

    return None, tree, display


# ---------------------------------------------------------------------------
# Check functions — v0.10 advanced config_flow rules (#101)
# ---------------------------------------------------------------------------


def config_flow_reauth_step_exists(context: ProjectContext) -> Finding:
    """Check that config_flow.py defines async_step_reauth or async_step_reauth_confirm."""
    rule_id = "config_flow.reauth_step.exists"
    title = "config_flow.py defines a reauthentication step"

    early, tree, display = _gate_config_flow_ast_rule(
        context, rule_id, title, _REAUTH_STEP_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None
    if _has_async_function_any(tree, _REAUTH_STEP_NAMES):
        return _make_ast_rule_finding(
            rule_id,
            title,
            _REAUTH_STEP_SOURCE,
            status=RuleStatus.PASS,
            message="config_flow.py defines a reauthentication step (async_step_reauth or async_step_reauth_confirm).",
            reason="Reauthentication allows users to fix expired credentials without removing and re-adding the integration.",
            path=display,
        )

    return _make_ast_rule_finding(
        rule_id,
        title,
        _REAUTH_STEP_SOURCE,
        status=RuleStatus.WARN,
        message="config_flow.py does not define async_step_reauth or async_step_reauth_confirm; reauthentication is not supported.",
        reason="Reauthentication allows users to fix expired credentials without removing and re-adding the integration.",
        path=display,
        fix=FixSuggestion(
            summary="Add async_step_reauth (and optionally async_step_reauth_confirm) to your ConfigFlow class.",
            docs_url=_REAUTH_STEP_SOURCE,
        ),
    )


def config_flow_reconfigure_step_exists(context: ProjectContext) -> Finding:
    """Check that config_flow.py defines async_step_reconfigure."""
    rule_id = "config_flow.reconfigure_step.exists"
    title = "config_flow.py defines a reconfigure step"

    early, tree, display = _gate_config_flow_ast_rule(
        context, rule_id, title, _RECONFIGURE_STEP_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None
    if _has_async_function(tree, "async_step_reconfigure"):
        return _make_ast_rule_finding(
            rule_id,
            title,
            _RECONFIGURE_STEP_SOURCE,
            status=RuleStatus.PASS,
            message="config_flow.py defines async_step_reconfigure.",
            reason="Reconfigure lets users update integration settings (e.g. host/port) without removing and re-adding it.",
            path=display,
        )

    return _make_ast_rule_finding(
        rule_id,
        title,
        _RECONFIGURE_STEP_SOURCE,
        status=RuleStatus.WARN,
        message="config_flow.py does not define async_step_reconfigure; users cannot update settings from the UI.",
        reason="Reconfigure lets users update integration settings (e.g. host/port) without removing and re-adding it.",
        path=display,
        fix=FixSuggestion(
            summary="Add async_step_reconfigure to your ConfigFlow class.",
            docs_url=_RECONFIGURE_STEP_SOURCE,
        ),
    )


def config_flow_unique_id_set(context: ProjectContext) -> Finding:
    """Check that config_flow.py calls async_set_unique_id."""
    rule_id = "config_flow.unique_id.set"
    title = "config_flow.py sets a unique ID"

    early, tree, display = _gate_config_flow_ast_rule(
        context, rule_id, title, _UNIQUE_ID_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None
    if _module_calls_name(tree, "async_set_unique_id"):
        return _make_ast_rule_finding(
            rule_id,
            title,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="config_flow.py calls async_set_unique_id.",
            reason="Setting a unique ID prevents duplicate config entries and enables entity deduplication.",
            path=display,
        )

    return _make_ast_rule_finding(
        rule_id,
        title,
        _UNIQUE_ID_SOURCE,
        status=RuleStatus.WARN,
        message="config_flow.py does not call async_set_unique_id; duplicate config entries may occur.",
        reason="Setting a unique ID prevents duplicate config entries and enables entity deduplication.",
        path=display,
        fix=FixSuggestion(
            summary="Call self.async_set_unique_id(<device-identifier>) before creating the entry.",
            docs_url=_UNIQUE_ID_SOURCE,
        ),
    )


def config_flow_connection_test(context: ProjectContext) -> Finding:
    """Check that at least one discovery-flow step awaits a non-plumbing call."""
    rule_id = "config_flow.connection_test"
    title = "config_flow.py tests the connection before creating the entry"

    early, tree, display = _gate_config_flow_ast_rule(
        context, rule_id, title, _CONNECTION_TEST_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None
    if _has_connection_test(tree):
        return _make_ast_rule_finding(
            rule_id,
            title,
            _CONNECTION_TEST_SOURCE,
            status=RuleStatus.PASS,
            message="config_flow.py awaits a non-plumbing call inside a discovery-flow step — connection testing detected.",
            reason="Testing the connection during setup gives users immediate feedback and prevents broken entries.",
            path=display,
        )

    return _make_ast_rule_finding(
        rule_id,
        title,
        _CONNECTION_TEST_SOURCE,
        status=RuleStatus.WARN,
        message=(
            "No connection test detected in config_flow.py. "
            "Discovery-flow steps (async_step_user, async_step_zeroconf, etc.) "
            "appear to only call flow plumbing methods."
        ),
        reason="Testing the connection during setup gives users immediate feedback and prevents broken entries.",
        path=display,
        fix=FixSuggestion(
            summary="Add a connection test (e.g. await validate_input(hass, data)) inside async_step_user.",
            docs_url=_CONNECTION_TEST_SOURCE,
        ),
    )


RULES = [
    RuleDefinition(
        id="config_flow.user_step.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py defines async_step_user",
        why=_USER_STEP_WHY,
        source_url=USER_STEP_SOURCE,
        check=config_flow_user_step_exists,
        overridable=True,
    ),
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
    RuleDefinition(
        id="config_flow.reauth_step.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py defines a reauthentication step",
        why=(
            "Reauthentication lets users recover from expired OAuth tokens or changed passwords "
            "without removing and re-adding the integration. "
            "Note: this rule uses AST inspection and cannot detect methods inherited from a base class."
        ),
        source_url=_REAUTH_STEP_SOURCE,
        check=config_flow_reauth_step_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="config_flow.reconfigure_step.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py defines a reconfigure step",
        why=(
            "Reconfigure lets users update integration settings (e.g. host, port, API key) "
            "without removing and re-adding the integration. "
            "Note: this rule uses AST inspection and cannot detect methods inherited from a base class."
        ),
        source_url=_RECONFIGURE_STEP_SOURCE,
        check=config_flow_reconfigure_step_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="config_flow.unique_id.set",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py sets a unique ID",
        why=(
            "Setting a unique ID via async_set_unique_id prevents duplicate config entries "
            "and enables entity deduplication across restarts. "
            "Note: this rule uses AST inspection; it detects any call to async_set_unique_id "
            "anywhere in the module."
        ),
        source_url=_UNIQUE_ID_SOURCE,
        check=config_flow_unique_id_set,
        overridable=True,
    ),
    RuleDefinition(
        id="config_flow.connection_test",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="config_flow.py tests the connection before creating the entry",
        why=(
            "Testing the connection during setup gives users immediate feedback when credentials "
            "or network settings are wrong, preventing broken config entries. "
            "Note: this rule uses a heuristic — it checks whether any discovery-flow step "
            "(async_step_user, async_step_zeroconf, etc.) awaits a call that is not pure flow "
            "plumbing (async_show_form, async_create_entry, etc.). False negatives are possible "
            "if connection logic lives in a helper called without await."
        ),
        source_url=_CONNECTION_TEST_SOURCE,
        check=config_flow_connection_test,
        overridable=True,
    ),
]
