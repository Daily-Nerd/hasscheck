"""Deprecation rules for HassCheck (issue #144).

Rules:
  Batch 1 (config_flow.unique_id.*):
    1. config_flow.unique_id.uses_ip_address
    2. config_flow.unique_id.uses_device_name
    3. config_flow.unique_id.uses_url
    4. config_flow.unique_id.missing_abort_if_configured
    5. config_flow.unique_id.not_normalized

  Batch 2:
    6.  config_entry.runtime_data.missing
    7.  entity.unique_id.mutable_source
    8.  setup.async_setup_entry.missing
    9.  helpers.deprecated_import
    10. manifest.config_flow.true_but_no_class

Category: deprecations
Severity: RECOMMENDED (all overridable)
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from hasscheck.ast_utils import module_calls_name, parse_module
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

CATEGORY = "deprecations"

_SOURCE_CHECKED_AT = "2026-05-01"

# ---------------------------------------------------------------------------
# Advisory source URLs
# ---------------------------------------------------------------------------
_UNIQUE_ID_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_config_flow_handler"
    "#unique-id"
)
_RUNTIME_DATA_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_index/#runtime_data"
)
_ENTITY_UNIQUE_ID_SOURCE = (
    "https://developers.home-assistant.io/docs/entity_registry_index/#unique-id"
)
_ASYNC_SETUP_ENTRY_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_index/#an-example"
)
_HELPERS_SOURCE = "https://developers.home-assistant.io/docs/core/entity/"
_MANIFEST_SOURCE = (
    "https://developers.home-assistant.io/docs/creating_integration_manifest"
)

# ---------------------------------------------------------------------------
# Deprecated helper paths (rule 9)
# ---------------------------------------------------------------------------
_DEPRECATED_HELPER_MODULES = frozenset(
    {
        "homeassistant.helpers.entity",
        "homeassistant.helpers.entity_platform",
        "homeassistant.helpers.entity_registry",
    }
)

# ---------------------------------------------------------------------------
# Shared path helpers
# ---------------------------------------------------------------------------


def _config_flow_path(context: ProjectContext) -> Path | None:
    if context.integration_path is None:
        return None
    return context.integration_path / "config_flow.py"


def _init_path(context: ProjectContext) -> Path | None:
    if context.integration_path is None:
        return None
    return context.integration_path / "__init__.py"


def _manifest_path(context: ProjectContext) -> Path | None:
    if context.integration_path is None:
        return None
    return context.integration_path / "manifest.json"


def _display_path(path: Path | None, context: ProjectContext, fallback: str) -> str:
    if path is None:
        return fallback
    try:
        return str(path.relative_to(context.root))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Shared Finding factories
# ---------------------------------------------------------------------------


def _make_not_applicable(
    rule_id: str,
    title: str,
    source_url: str,
    message: str,
    reason: str,
    path: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.RECOMMENDED,
        title=title,
        message=message,
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason=reason,
        ),
        source=RuleSource(url=source_url, checked_at=_SOURCE_CHECKED_AT),
        fix=None,
        path=path,
    )


def _make_finding(
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
        source=RuleSource(url=source_url, checked_at=_SOURCE_CHECKED_AT),
        fix=fix,
        path=path,
    )


# ---------------------------------------------------------------------------
# Shared config_flow.py gating helper
# ---------------------------------------------------------------------------


def _gate_config_flow_rule(
    context: ProjectContext,
    rule_id: str,
    title: str,
    source_url: str,
) -> tuple[Finding | None, ast.Module | None, str]:
    """Gate rule on config_flow.py existence and parseability.

    Returns (early_finding, tree, display_path).
    If early_finding is not None, return it immediately.
    """
    fallback = "custom_components/<domain>/config_flow.py"

    if context.integration_path is None:
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message="No integration directory was detected.",
                reason="integration_path must exist before this rule can run.",
                path=fallback,
            ),
            None,
            fallback,
        )

    cf_path = context.integration_path / "config_flow.py"
    display = _display_path(cf_path, context, fallback)

    if not cf_path.is_file():
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message="config_flow.py does not exist; rule cannot be checked.",
                reason="config_flow.py must exist before this rule can run.",
                path=display,
            ),
            None,
            display,
        )

    tree, error = parse_module(cf_path)
    if error is not None:
        return (
            _make_finding(
                rule_id,
                title,
                source_url,
                status=RuleStatus.WARN,
                message=f"config_flow.py could not be parsed ({error}); rule cannot be determined.",
                reason="config_flow.py exists but has a syntax error.",
                path=display,
                fix=FixSuggestion(summary="Fix syntax errors in config_flow.py."),
            ),
            None,
            display,
        )

    return None, tree, display


# ---------------------------------------------------------------------------
# Shared helpers: detect mutable-looking unique_id assignment near a call
# ---------------------------------------------------------------------------


def _find_unique_id_assignments(tree: ast.Module) -> list[ast.Assign | ast.AnnAssign]:
    """Return all assignment nodes that assign to a name containing 'unique_id'."""
    assignments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and "unique_id" in target.id:
                    assignments.append(node)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and "unique_id" in node.target.id:
                assignments.append(node)
    return assignments


def _variables_near_unique_id_call(tree: ast.Module) -> list[str]:
    """Return names of variables assigned in the same function scope as async_set_unique_id.

    Walk every AsyncFunctionDef/FunctionDef that contains an async_set_unique_id call.
    Collect Name assignments within that scope and return them as lowercase.
    """
    names: list[str] = []
    for fn_node in ast.walk(tree):
        if not isinstance(fn_node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue

        # Does this function call async_set_unique_id?
        fn_tree = ast.Module(body=[fn_node], type_ignores=[])
        if not module_calls_name(fn_tree, "async_set_unique_id"):
            continue

        # Collect all assigned names in this function
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.append(target.id.lower())
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.append(node.target.id.lower())
            # Also collect the argument name of async_set_unique_id call itself
            elif isinstance(node, ast.Call):
                func = node.func
                if (
                    isinstance(func, ast.Name) and func.id == "async_set_unique_id"
                ) or (
                    isinstance(func, ast.Attribute)
                    and func.attr == "async_set_unique_id"
                ):
                    for arg in node.args:
                        if isinstance(arg, ast.Name):
                            names.append(arg.id.lower())
    return names


def _has_normalization_near_unique_id(tree: ast.Module) -> bool:
    """Return True if .lower() or .strip() appears in a scope with async_set_unique_id."""
    for fn_node in ast.walk(tree):
        if not isinstance(fn_node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue

        fn_tree = ast.Module(body=[fn_node], type_ignores=[])
        if not module_calls_name(fn_tree, "async_set_unique_id"):
            continue

        # Check for .lower() or .strip() calls anywhere in this function
        for node in ast.walk(fn_node):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("lower", "strip"):
                return True

    return False


# ---------------------------------------------------------------------------
# Rule 1: config_flow.unique_id.uses_ip_address
# ---------------------------------------------------------------------------

_RULE1_ID = "config_flow.unique_id.uses_ip_address"
_RULE1_TITLE = "Config flow unique ID derived from mutable IP address"
_IP_KEYWORDS = frozenset({"ip", "ip_address", "ipaddress", "host", "address"})


def check_uses_ip_address(context: ProjectContext) -> Finding:
    """Check that config_flow.py does not use an IP/host variable as unique ID."""
    early, tree, display = _gate_config_flow_rule(
        context, _RULE1_ID, _RULE1_TITLE, _UNIQUE_ID_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None

    if not module_calls_name(tree, "async_set_unique_id"):
        return _make_finding(
            _RULE1_ID,
            _RULE1_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="async_set_unique_id not found in config_flow.py.",
            reason="No unique ID assignment detected; rule does not apply.",
            path=display,
        )

    var_names = _variables_near_unique_id_call(tree)
    if any(kw in name for name in var_names for kw in _IP_KEYWORDS):
        return _make_finding(
            _RULE1_ID,
            _RULE1_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.WARN,
            message=(
                "config_flow.py appears to use an IP address or hostname as the unique ID. "
                "Use a stable identifier (MAC address, serial number) instead."
            ),
            reason="IP addresses are mutable (DHCP) and make poor unique IDs.",
            path=display,
            fix=FixSuggestion(
                summary="Replace IP-derived unique ID with a stable device identifier.",
                docs_url=_UNIQUE_ID_SOURCE,
            ),
        )

    return _make_finding(
        _RULE1_ID,
        _RULE1_TITLE,
        _UNIQUE_ID_SOURCE,
        status=RuleStatus.PASS,
        message="config_flow.py does not appear to use a mutable IP address as the unique ID.",
        reason="No IP/host variable names detected near async_set_unique_id.",
        path=display,
    )


# ---------------------------------------------------------------------------
# Rule 2: config_flow.unique_id.uses_device_name
# ---------------------------------------------------------------------------

_RULE2_ID = "config_flow.unique_id.uses_device_name"
_RULE2_TITLE = "Config flow unique ID derived from mutable device name"
_NAME_KEYWORDS = frozenset({"name", "device_name", "devicename", "friendly_name"})


def check_uses_device_name(context: ProjectContext) -> Finding:
    """Check that config_flow.py does not use a device name as unique ID."""
    early, tree, display = _gate_config_flow_rule(
        context, _RULE2_ID, _RULE2_TITLE, _UNIQUE_ID_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None

    if not module_calls_name(tree, "async_set_unique_id"):
        return _make_finding(
            _RULE2_ID,
            _RULE2_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="async_set_unique_id not found in config_flow.py.",
            reason="No unique ID assignment detected; rule does not apply.",
            path=display,
        )

    var_names = _variables_near_unique_id_call(tree)
    if any(kw in name for name in var_names for kw in _NAME_KEYWORDS):
        return _make_finding(
            _RULE2_ID,
            _RULE2_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.WARN,
            message=(
                "config_flow.py appears to use a device name as the unique ID. "
                "Use a stable identifier (MAC address, serial number) instead."
            ),
            reason="Device names are mutable and make poor unique IDs.",
            path=display,
            fix=FixSuggestion(
                summary="Replace name-derived unique ID with a stable device identifier.",
                docs_url=_UNIQUE_ID_SOURCE,
            ),
        )

    return _make_finding(
        _RULE2_ID,
        _RULE2_TITLE,
        _UNIQUE_ID_SOURCE,
        status=RuleStatus.PASS,
        message="config_flow.py does not appear to use a mutable device name as the unique ID.",
        reason="No name variable detected near async_set_unique_id.",
        path=display,
    )


# ---------------------------------------------------------------------------
# Rule 3: config_flow.unique_id.uses_url
# ---------------------------------------------------------------------------

_RULE3_ID = "config_flow.unique_id.uses_url"
_RULE3_TITLE = "Config flow unique ID derived from URL or host"
_URL_KEYWORDS = frozenset({"url", "base_url", "endpoint", "host", "hostname"})


def check_uses_url(context: ProjectContext) -> Finding:
    """Check that config_flow.py does not use a URL or hostname as unique ID."""
    early, tree, display = _gate_config_flow_rule(
        context, _RULE3_ID, _RULE3_TITLE, _UNIQUE_ID_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None

    if not module_calls_name(tree, "async_set_unique_id"):
        return _make_finding(
            _RULE3_ID,
            _RULE3_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="async_set_unique_id not found in config_flow.py.",
            reason="No unique ID assignment detected; rule does not apply.",
            path=display,
        )

    var_names = _variables_near_unique_id_call(tree)
    if any(kw in name for name in var_names for kw in _URL_KEYWORDS):
        return _make_finding(
            _RULE3_ID,
            _RULE3_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.WARN,
            message=(
                "config_flow.py appears to use a URL or hostname as the unique ID. "
                "Use a stable identifier (MAC address, serial number) instead."
            ),
            reason="URLs and hostnames change with network reconfiguration.",
            path=display,
            fix=FixSuggestion(
                summary="Replace URL-derived unique ID with a stable device identifier.",
                docs_url=_UNIQUE_ID_SOURCE,
            ),
        )

    return _make_finding(
        _RULE3_ID,
        _RULE3_TITLE,
        _UNIQUE_ID_SOURCE,
        status=RuleStatus.PASS,
        message="config_flow.py does not appear to use a mutable URL/host as the unique ID.",
        reason="No URL/host variable detected near async_set_unique_id.",
        path=display,
    )


# ---------------------------------------------------------------------------
# Rule 4: config_flow.unique_id.missing_abort_if_configured
# ---------------------------------------------------------------------------

_RULE4_ID = "config_flow.unique_id.missing_abort_if_configured"
_RULE4_TITLE = "Config flow sets unique ID without aborting on duplicate"


def check_missing_abort_if_configured(context: ProjectContext) -> Finding:
    """Check that config_flow.py calls _abort_if_unique_id_configured alongside set_unique_id."""
    early, tree, display = _gate_config_flow_rule(
        context, _RULE4_ID, _RULE4_TITLE, _UNIQUE_ID_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None

    if not module_calls_name(tree, "async_set_unique_id"):
        return _make_finding(
            _RULE4_ID,
            _RULE4_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="async_set_unique_id not called; rule does not apply.",
            reason="No unique ID being set; abort check not needed.",
            path=display,
        )

    if module_calls_name(tree, "_abort_if_unique_id_configured"):
        return _make_finding(
            _RULE4_ID,
            _RULE4_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="config_flow.py calls both async_set_unique_id and _abort_if_unique_id_configured.",
            reason="Both calls present — duplicate config entry protection is in place.",
            path=display,
        )

    return _make_finding(
        _RULE4_ID,
        _RULE4_TITLE,
        _UNIQUE_ID_SOURCE,
        status=RuleStatus.WARN,
        message=(
            "config_flow.py calls async_set_unique_id but does not call "
            "_abort_if_unique_id_configured — duplicate config entries may be created."
        ),
        reason="async_set_unique_id should always be paired with _abort_if_unique_id_configured.",
        path=display,
        fix=FixSuggestion(
            summary="Add self._abort_if_unique_id_configured() after async_set_unique_id.",
            docs_url=_UNIQUE_ID_SOURCE,
        ),
    )


# ---------------------------------------------------------------------------
# Rule 5: config_flow.unique_id.not_normalized
# ---------------------------------------------------------------------------

_RULE5_ID = "config_flow.unique_id.not_normalized"
_RULE5_TITLE = "Config flow unique ID not normalized"


def check_not_normalized(context: ProjectContext) -> Finding:
    """Check that the unique ID is normalized (lowercased or stripped) before being set."""
    early, tree, display = _gate_config_flow_rule(
        context, _RULE5_ID, _RULE5_TITLE, _UNIQUE_ID_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None

    if not module_calls_name(tree, "async_set_unique_id"):
        return _make_finding(
            _RULE5_ID,
            _RULE5_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="async_set_unique_id not called; normalization check not applicable.",
            reason="No unique ID being set.",
            path=display,
        )

    if _has_normalization_near_unique_id(tree):
        return _make_finding(
            _RULE5_ID,
            _RULE5_TITLE,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="config_flow.py normalizes the unique ID with .lower() or .strip().",
            reason="Normalization detected in the same scope as async_set_unique_id.",
            path=display,
        )

    return _make_finding(
        _RULE5_ID,
        _RULE5_TITLE,
        _UNIQUE_ID_SOURCE,
        status=RuleStatus.WARN,
        message=(
            "config_flow.py calls async_set_unique_id but does not appear to normalize "
            "the unique ID with .lower() or .strip()."
        ),
        reason="Unique IDs should be normalized for consistency across setups.",
        path=display,
        fix=FixSuggestion(
            summary="Add .lower().strip() to the unique ID value before calling async_set_unique_id.",
            docs_url=_UNIQUE_ID_SOURCE,
        ),
    )


# ---------------------------------------------------------------------------
# Shared __init__.py gating helper
# ---------------------------------------------------------------------------


def _gate_init_rule(
    context: ProjectContext,
    rule_id: str,
    title: str,
    source_url: str,
) -> tuple[Finding | None, ast.Module | None, str]:
    """Gate rule on __init__.py existence and parseability."""
    fallback = "custom_components/<domain>/__init__.py"

    if context.integration_path is None:
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message="No integration directory was detected.",
                reason="integration_path must exist before this rule can run.",
                path=fallback,
            ),
            None,
            fallback,
        )

    init = context.integration_path / "__init__.py"
    display = _display_path(init, context, fallback)

    if not init.is_file():
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message="__init__.py does not exist; rule cannot be checked.",
                reason="__init__.py must exist before this rule can run.",
                path=display,
            ),
            None,
            display,
        )

    tree, error = parse_module(init)
    if error is not None:
        return (
            _make_finding(
                rule_id,
                title,
                source_url,
                status=RuleStatus.WARN,
                message=f"__init__.py could not be parsed ({error}); rule cannot be determined.",
                reason="__init__.py exists but has a syntax error.",
                path=display,
                fix=FixSuggestion(summary="Fix syntax errors in __init__.py."),
            ),
            None,
            display,
        )

    return None, tree, display


# ---------------------------------------------------------------------------
# Rule 6: config_entry.runtime_data.missing
# ---------------------------------------------------------------------------

_RULE6_ID = "config_entry.runtime_data.missing"
_RULE6_TITLE = "Integration uses hass.data instead of entry.runtime_data"


def _has_hass_data_usage(tree: ast.Module) -> bool:
    """Return True if any hass.data[...] or hass.data.get(...) access is found."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        value = node.value
        if not isinstance(value, ast.Attribute):
            continue
        if value.attr != "data":
            continue
        if isinstance(value.value, ast.Name) and value.value.id == "hass":
            return True
    # Also check hass.data.get(...)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != "get":
            continue
        if not isinstance(func.value, ast.Attribute):
            continue
        if func.value.attr != "data":
            continue
        if isinstance(func.value.value, ast.Name) and func.value.value.id == "hass":
            return True
    return False


def check_runtime_data_missing(context: ProjectContext) -> Finding:
    """Check that __init__.py uses entry.runtime_data instead of hass.data[DOMAIN]."""
    early, tree, display = _gate_init_rule(
        context, _RULE6_ID, _RULE6_TITLE, _RUNTIME_DATA_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None

    if _has_hass_data_usage(tree):
        return _make_finding(
            _RULE6_ID,
            _RULE6_TITLE,
            _RUNTIME_DATA_SOURCE,
            status=RuleStatus.WARN,
            message=(
                "__init__.py uses hass.data[DOMAIN] for storing runtime data. "
                "Migrate to entry.runtime_data (HA 2024.4+ recommended pattern)."
            ),
            reason="hass.data is the legacy pattern; entry.runtime_data is type-safe and cleaner.",
            path=display,
            fix=FixSuggestion(
                summary="Replace hass.data[DOMAIN] with entry.runtime_data = <your object>.",
                docs_url=_RUNTIME_DATA_SOURCE,
            ),
        )

    return _make_finding(
        _RULE6_ID,
        _RULE6_TITLE,
        _RUNTIME_DATA_SOURCE,
        status=RuleStatus.PASS,
        message="__init__.py does not use hass.data for runtime data storage.",
        reason="No hass.data[DOMAIN] usage detected.",
        path=display,
    )


# ---------------------------------------------------------------------------
# Rule 7: entity.unique_id.mutable_source
# ---------------------------------------------------------------------------

_RULE7_ID = "entity.unique_id.mutable_source"
_RULE7_TITLE = "Entity unique_id derived from mutable source"

_HA_PLATFORM_NAMES = frozenset(
    {
        "binary_sensor",
        "button",
        "camera",
        "climate",
        "cover",
        "fan",
        "light",
        "lock",
        "media_player",
        "number",
        "select",
        "sensor",
        "switch",
        "text",
        "update",
        "vacuum",
    }
)

_MUTABLE_ENTITY_ID_KEYWORDS = frozenset({"name", "ip", "ip_address", "host", "address"})


def _entity_files(context: ProjectContext) -> list[Path]:
    """Return all .py files in integration_path that match platform names."""
    if context.integration_path is None:
        return []
    return [
        context.integration_path / f"{name}.py"
        for name in _HA_PLATFORM_NAMES
        if (context.integration_path / f"{name}.py").is_file()
    ]


def _has_mutable_unique_id_in_tree(tree: ast.Module) -> bool:
    """Return True if any unique_id property returns a value derived from name/ip."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "unique_id":
            continue
        # Check if there's a decorator @property
        is_property = any(
            (isinstance(d, ast.Name) and d.id == "property")
            or (isinstance(d, ast.Attribute) and d.attr == "property")
            for d in node.decorator_list
        )
        if not is_property:
            continue
        # Scan return values for mutable attribute access
        for inner in ast.walk(node):
            if isinstance(inner, ast.Attribute):
                attr_name = inner.attr.lower()
                if any(kw in attr_name for kw in _MUTABLE_ENTITY_ID_KEYWORDS):
                    return True
            elif isinstance(inner, ast.Name):
                var_name = inner.id.lower()
                if any(kw in var_name for kw in _MUTABLE_ENTITY_ID_KEYWORDS):
                    return True
    return False


def check_entity_unique_id_mutable(context: ProjectContext) -> Finding:
    """Check that entity files do not use mutable sources for unique_id."""
    fallback = "custom_components/<domain>/<platform>.py"

    if context.integration_path is None:
        return _make_not_applicable(
            _RULE7_ID,
            _RULE7_TITLE,
            _ENTITY_UNIQUE_ID_SOURCE,
            message="No integration directory was detected.",
            reason="integration_path must exist before this rule can run.",
            path=fallback,
        )

    entity_files = _entity_files(context)
    if not entity_files:
        return _make_not_applicable(
            _RULE7_ID,
            _RULE7_TITLE,
            _ENTITY_UNIQUE_ID_SOURCE,
            message="No entity platform files found in integration directory.",
            reason="No platform files (sensor.py, switch.py, etc.) to inspect.",
            path=fallback,
        )

    for ef in entity_files:
        display = _display_path(ef, context, fallback)
        tree, error = parse_module(ef)
        if error is not None:
            continue  # skip unparseable files

        if _has_mutable_unique_id_in_tree(tree):
            return _make_finding(
                _RULE7_ID,
                _RULE7_TITLE,
                _ENTITY_UNIQUE_ID_SOURCE,
                status=RuleStatus.WARN,
                message=(
                    f"{display} has a unique_id property that appears to derive from "
                    "a mutable source (name or IP). Use a stable identifier instead."
                ),
                reason="Mutable unique IDs cause entity registry corruption when values change.",
                path=display,
                fix=FixSuggestion(
                    summary="Replace mutable unique_id source with a stable identifier.",
                    docs_url=_ENTITY_UNIQUE_ID_SOURCE,
                ),
            )

    first_display = _display_path(entity_files[0], context, fallback)
    return _make_finding(
        _RULE7_ID,
        _RULE7_TITLE,
        _ENTITY_UNIQUE_ID_SOURCE,
        status=RuleStatus.PASS,
        message="Entity unique_id does not appear to use mutable sources.",
        reason="No mutable name/IP attribute detected in unique_id properties.",
        path=first_display,
    )


# ---------------------------------------------------------------------------
# Rule 8: setup.async_setup_entry.missing
# ---------------------------------------------------------------------------

_RULE8_ID = "setup.async_setup_entry.missing"
_RULE8_TITLE = "Integration defines async_setup but not async_setup_entry"


def check_async_setup_entry_missing(context: ProjectContext) -> Finding:
    """Check that if __init__.py defines async_setup it also defines async_setup_entry."""
    from hasscheck.ast_utils import has_async_function

    early, tree, display = _gate_init_rule(
        context, _RULE8_ID, _RULE8_TITLE, _ASYNC_SETUP_ENTRY_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None

    has_setup = has_async_function(tree, "async_setup")
    has_setup_entry = has_async_function(tree, "async_setup_entry")

    if has_setup and not has_setup_entry:
        return _make_finding(
            _RULE8_ID,
            _RULE8_TITLE,
            _ASYNC_SETUP_ENTRY_SOURCE,
            status=RuleStatus.WARN,
            message=(
                "__init__.py defines async_setup but not async_setup_entry. "
                "Config-entry-based integrations must define async_setup_entry."
            ),
            reason="async_setup_entry is required for config-entry-based integrations.",
            path=display,
            fix=FixSuggestion(
                summary="Add async_setup_entry(hass, entry) to __init__.py.",
                docs_url=_ASYNC_SETUP_ENTRY_SOURCE,
            ),
        )

    return _make_finding(
        _RULE8_ID,
        _RULE8_TITLE,
        _ASYNC_SETUP_ENTRY_SOURCE,
        status=RuleStatus.PASS,
        message="__init__.py defines async_setup_entry or does not use the legacy async_setup pattern.",
        reason="async_setup_entry is present or async_setup is not defined.",
        path=display,
    )


# ---------------------------------------------------------------------------
# Rule 9: helpers.deprecated_import
# ---------------------------------------------------------------------------

_RULE9_ID = "helpers.deprecated_import"
_RULE9_TITLE = "Integration imports from deprecated homeassistant.helpers path"


def _has_deprecated_helper_import(tree: ast.Module) -> str | None:
    """Return the first deprecated import module path found, or None."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if module in _DEPRECATED_HELPER_MODULES:
            return module
    return None


def check_helpers_deprecated_import(context: ProjectContext) -> Finding:
    """Check that integration files don't import from deprecated HA helper paths."""
    fallback = "custom_components/<domain>/<file>.py"

    if context.integration_path is None:
        return _make_not_applicable(
            _RULE9_ID,
            _RULE9_TITLE,
            _HELPERS_SOURCE,
            message="No integration directory was detected.",
            reason="integration_path must exist before this rule can run.",
            path=fallback,
        )

    python_files = sorted(context.integration_path.glob("*.py"))
    if not python_files:
        return _make_not_applicable(
            _RULE9_ID,
            _RULE9_TITLE,
            _HELPERS_SOURCE,
            message="No Python files found in the integration directory.",
            reason="No .py files to inspect for deprecated imports.",
            path=fallback,
        )

    for py_file in python_files:
        display = _display_path(py_file, context, fallback)
        tree, error = parse_module(py_file)
        if error is not None:
            continue

        deprecated_module = _has_deprecated_helper_import(tree)
        if deprecated_module is not None:
            return _make_finding(
                _RULE9_ID,
                _RULE9_TITLE,
                _HELPERS_SOURCE,
                status=RuleStatus.WARN,
                message=(
                    f"{display} imports from deprecated path '{deprecated_module}'. "
                    "Migrate to the modern import path."
                ),
                reason=f"'{deprecated_module}' was deprecated in HA 2024.x.",
                path=display,
                fix=FixSuggestion(
                    summary=f"Replace 'from {deprecated_module} import ...' with the modern path.",
                    docs_url=_HELPERS_SOURCE,
                ),
            )

    first_display = _display_path(python_files[0], context, fallback)
    return _make_finding(
        _RULE9_ID,
        _RULE9_TITLE,
        _HELPERS_SOURCE,
        status=RuleStatus.PASS,
        message="No deprecated homeassistant.helpers imports found.",
        reason="All imports use non-deprecated paths.",
        path=first_display,
    )


# ---------------------------------------------------------------------------
# Rule 10: manifest.config_flow.true_but_no_class
# ---------------------------------------------------------------------------

_RULE10_ID = "manifest.config_flow.true_but_no_class"
_RULE10_TITLE = "manifest.json declares config_flow: true but no ConfigFlow class found"


def _has_config_flow_class(tree: ast.Module) -> bool:
    """Return True if any class named 'ConfigFlow' is defined in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ConfigFlow":
            return True
    return False


def check_manifest_config_flow_true_but_no_class(context: ProjectContext) -> Finding:
    """Check that when manifest declares config_flow: true, a ConfigFlow class exists."""
    fallback = "custom_components/<domain>/manifest.json"

    if context.integration_path is None:
        return _make_not_applicable(
            _RULE10_ID,
            _RULE10_TITLE,
            _MANIFEST_SOURCE,
            message="No integration directory was detected.",
            reason="integration_path must exist before this rule can run.",
            path=fallback,
        )

    manifest = context.integration_path / "manifest.json"
    display_manifest = _display_path(manifest, context, fallback)

    if not manifest.is_file():
        return _make_not_applicable(
            _RULE10_ID,
            _RULE10_TITLE,
            _MANIFEST_SOURCE,
            message="manifest.json does not exist; rule cannot be checked.",
            reason="manifest.json must exist before this rule can run.",
            path=display_manifest,
        )

    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _make_not_applicable(
            _RULE10_ID,
            _RULE10_TITLE,
            _MANIFEST_SOURCE,
            message="manifest.json could not be read or parsed.",
            reason="manifest.json exists but is not valid JSON.",
            path=display_manifest,
        )

    if not isinstance(payload, dict) or not payload.get("config_flow", False):
        return _make_finding(
            _RULE10_ID,
            _RULE10_TITLE,
            _MANIFEST_SOURCE,
            status=RuleStatus.PASS,
            message="manifest.json does not declare config_flow: true; rule does not apply.",
            reason="No config_flow: true in manifest.",
            path=display_manifest,
        )

    # manifest has config_flow: true — check for ConfigFlow class
    cf_path = context.integration_path / "config_flow.py"
    display_cf = _display_path(
        cf_path, context, "custom_components/<domain>/config_flow.py"
    )

    if not cf_path.is_file():
        return _make_finding(
            _RULE10_ID,
            _RULE10_TITLE,
            _MANIFEST_SOURCE,
            status=RuleStatus.WARN,
            message=(
                "manifest.json declares config_flow: true but config_flow.py does not exist."
            ),
            reason="config_flow: true requires config_flow.py with a ConfigFlow class.",
            path=display_manifest,
            fix=FixSuggestion(
                summary="Create config_flow.py with a ConfigFlow class.",
                docs_url=_MANIFEST_SOURCE,
            ),
        )

    tree, error = parse_module(cf_path)
    if error is not None:
        return _make_finding(
            _RULE10_ID,
            _RULE10_TITLE,
            _MANIFEST_SOURCE,
            status=RuleStatus.WARN,
            message=f"config_flow.py could not be parsed ({error}); ConfigFlow class cannot be detected.",
            reason="config_flow.py exists but has a syntax error.",
            path=display_cf,
            fix=FixSuggestion(summary="Fix syntax errors in config_flow.py."),
        )

    if _has_config_flow_class(tree):
        return _make_finding(
            _RULE10_ID,
            _RULE10_TITLE,
            _MANIFEST_SOURCE,
            status=RuleStatus.PASS,
            message="manifest.json declares config_flow: true and a ConfigFlow class was found.",
            reason="ConfigFlow class present in config_flow.py.",
            path=display_cf,
        )

    return _make_finding(
        _RULE10_ID,
        _RULE10_TITLE,
        _MANIFEST_SOURCE,
        status=RuleStatus.WARN,
        message=(
            "manifest.json declares config_flow: true but no ConfigFlow class was found in "
            "config_flow.py."
        ),
        reason="config_flow: true requires a ConfigFlow subclass in config_flow.py.",
        path=display_cf,
        fix=FixSuggestion(
            summary="Add a ConfigFlow class to config_flow.py.",
            docs_url=_MANIFEST_SOURCE,
        ),
    )


# ---------------------------------------------------------------------------
# Rule registry — batch 1
# ---------------------------------------------------------------------------

RULES: list[RuleDefinition] = [
    RuleDefinition(
        id=_RULE1_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE1_TITLE,
        why=(
            "IP addresses change on DHCP renewal, causing duplicate config entries "
            "or broken integrations. Use a stable device identifier (MAC address, "
            "serial number) instead."
        ),
        source_url=_UNIQUE_ID_SOURCE,
        check=check_uses_ip_address,
        overridable=True,
        advisory_id="ha-2025-03-unique-id-ip-source",
        min_ha_version="2025.3",
    ),
    RuleDefinition(
        id=_RULE2_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE2_TITLE,
        why=(
            "Device names can be changed by users or by the device itself, causing "
            "duplicate config entries or broken integrations. Use a stable identifier instead."
        ),
        source_url=_UNIQUE_ID_SOURCE,
        check=check_uses_device_name,
        overridable=True,
        advisory_id="ha-2025-03-unique-id-name-source",
        min_ha_version="2025.3",
    ),
    RuleDefinition(
        id=_RULE3_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE3_TITLE,
        why=(
            "URLs and hostnames change with network reconfiguration, causing duplicate "
            "config entries or broken integrations. Use a stable identifier instead."
        ),
        source_url=_UNIQUE_ID_SOURCE,
        check=check_uses_url,
        overridable=True,
        advisory_id="ha-2025-03-unique-id-url-source",
        min_ha_version="2025.3",
    ),
    RuleDefinition(
        id=_RULE4_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE4_TITLE,
        why=(
            "When async_set_unique_id is called, _abort_if_unique_id_configured should "
            "also be called to prevent duplicate config entries. Missing this call allows "
            "users to set up the same device multiple times."
        ),
        source_url=_UNIQUE_ID_SOURCE,
        check=check_missing_abort_if_configured,
        overridable=True,
        advisory_id="ha-2025-03-unique-id-missing-abort",
        min_ha_version="2025.3",
    ),
    RuleDefinition(
        id=_RULE5_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE5_TITLE,
        why=(
            "Unique IDs should be normalized (e.g., lowercased, stripped) to ensure "
            "consistency across setups and HA versions. Without normalization, the same "
            "device may get different unique IDs depending on the identifier source."
        ),
        source_url=_UNIQUE_ID_SOURCE,
        check=check_not_normalized,
        overridable=True,
        advisory_id="ha-2025-03-unique-id-not-normalized",
        min_ha_version="2025.3",
    ),
    RuleDefinition(
        id=_RULE6_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE6_TITLE,
        why=(
            "hass.data[DOMAIN] is the legacy pattern for storing per-entry runtime objects. "
            "entry.runtime_data (HA 2024.4+) is type-safe, avoids global state, and is "
            "cleaner to test."
        ),
        source_url=_RUNTIME_DATA_SOURCE,
        check=check_runtime_data_missing,
        overridable=True,
        advisory_id="ha-2024-04-runtime-data-adoption",
        min_ha_version="2024.4",
    ),
    RuleDefinition(
        id=_RULE7_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE7_TITLE,
        why=(
            "Entity unique IDs derived from mutable values (name, IP) cause entity registry "
            "corruption when the source value changes. Use a stable, immutable identifier."
        ),
        source_url=_ENTITY_UNIQUE_ID_SOURCE,
        check=check_entity_unique_id_mutable,
        overridable=True,
        advisory_id="ha-2025-03-entity-unique-id-mutable",
        min_ha_version="2025.3",
    ),
    RuleDefinition(
        id=_RULE8_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE8_TITLE,
        why=(
            "Integrations that use config entries must define async_setup_entry. "
            "Defining only the legacy async_setup function means the integration cannot "
            "be set up via config entries."
        ),
        source_url=_ASYNC_SETUP_ENTRY_SOURCE,
        check=check_async_setup_entry_missing,
        overridable=True,
        advisory_id="ha-2024-01-async-setup-entry",
        min_ha_version="2024.1",
    ),
    RuleDefinition(
        id=_RULE9_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE9_TITLE,
        why=(
            "Several homeassistant.helpers.* modules were deprecated in HA 2024.x. "
            "Importing from these paths will fail in a future HA version."
        ),
        source_url=_HELPERS_SOURCE,
        check=check_helpers_deprecated_import,
        overridable=True,
        advisory_id="ha-2024-03-helpers-deprecated-imports",
        min_ha_version="2024.3",
    ),
    RuleDefinition(
        id=_RULE10_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RULE10_TITLE,
        why=(
            "When manifest.json declares config_flow: true, HA expects a ConfigFlow class "
            "in config_flow.py. Missing this class causes HA to error when attempting to "
            "set up the integration via the UI."
        ),
        source_url=_MANIFEST_SOURCE,
        check=check_manifest_config_flow_true_but_no_class,
        overridable=True,
        advisory_id="ha-2025-01-manifest-config-flow-class",
        min_ha_version="2025.1",
    ),
]
