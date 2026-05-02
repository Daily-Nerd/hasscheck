"""Rules checking entity platform patterns for modern HA integrations (issue #107).

Rules:
  - entity.unique_id.set
  - entity.has_entity_name.set
  - entity.device_info.set

Category: modern_ha_patterns
Severity: RECOMMENDED
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

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

_SOURCE_CHECKED_AT = "2026-05-01"

_UNIQUE_ID_SOURCE = (
    "https://developers.home-assistant.io/docs/entity_registry_index/#unique-id"
)
_HAS_ENTITY_NAME_SOURCE = (
    "https://developers.home-assistant.io/docs/core/entity/"
    "#has_entity_name-true-mandatory-for-new-integrations"
)
_DEVICE_INFO_SOURCE = (
    "https://developers.home-assistant.io/docs/device_registry_index/#defining-devices"
)

# Canonical set of HA platform names (Source: homeassistant/const.py Platform enum)
_HA_PLATFORM_NAMES: frozenset[str] = frozenset(
    {
        "air_quality",
        "alarm_control_panel",
        "binary_sensor",
        "button",
        "calendar",
        "camera",
        "climate",
        "conversation",
        "cover",
        "date",
        "datetime",
        "device_tracker",
        "event",
        "fan",
        "geo_location",
        "humidifier",
        "image",
        "image_processing",
        "lawn_mower",
        "light",
        "lock",
        "media_player",
        "notify",
        "number",
        "remote",
        "scene",
        "select",
        "sensor",
        "siren",
        "stt",
        "switch",
        "text",
        "time",
        "todo",
        "tts",
        "update",
        "vacuum",
        "valve",
        "wake_word",
        "water_heater",
        "weather",
    }
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _display_path(path: Path, context: ProjectContext, fallback: str) -> str:
    if path is None:
        return fallback
    return str(path.relative_to(context.root))


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
        source=RuleSource(url=source_url),
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
        source=RuleSource(url=source_url),
        fix=fix,
        path=path,
    )


def _iter_platform_files(integration_path: Path) -> Iterable[Path]:
    """Yield existing HA platform files in the integration directory."""
    for name in _HA_PLATFORM_NAMES:
        candidate = integration_path / f"{name}.py"
        if candidate.is_file():
            yield candidate


def _inspect_entity_files_for(
    integration_path: Path,
    predicate,
) -> tuple[bool, list[str]]:
    """Inspect all platform files with predicate.

    Returns (any_match, parse_errors) where:
    - any_match: True if at least one file satisfied the predicate
    - parse_errors: list of file paths (as str) that failed to parse
    """
    any_match = False
    parse_errors: list[str] = []

    for path in _iter_platform_files(integration_path):
        tree, error = parse_module(path)
        if error is not None:
            parse_errors.append(str(path))
            continue
        assert tree is not None
        if predicate(tree):
            any_match = True

    return any_match, parse_errors


# ---------------------------------------------------------------------------
# Detection predicates
# ---------------------------------------------------------------------------


def _entity_file_sets_unique_id(tree: ast.Module) -> bool:
    """Return True if the module assigns _attr_unique_id (class or self attr)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_attr_unique_id":
                    return True
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "_attr_unique_id"
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    return True
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == "_attr_unique_id":
                return True
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "_attr_unique_id"
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                return True
    return False


def _entity_file_has_entity_name_true(tree: ast.Module) -> bool:
    """Return True if _attr_has_entity_name is assigned literal True."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets_match = False
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_attr_has_entity_name":
                targets_match = True
                break
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "_attr_has_entity_name"
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                targets_match = True
                break
        if not targets_match:
            continue
        # Value must be literal True
        if isinstance(node.value, ast.Constant) and node.value.value is True:
            return True
    return False


def _entity_file_sets_device_info(tree: ast.Module) -> bool:
    """Return True if the module sets _attr_device_info OR has a device_info
    method/property returning DeviceInfo(...).
    """
    for node in ast.walk(tree):
        # Path 1: _attr_device_info assignment (class or self attribute)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id == "_attr_device_info":
                    return True
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "_attr_device_info"
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    return True
        # Path 2: any function/method named "device_info" returning DeviceInfo(...)
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "device_info"
        ):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Call):
                    func = inner.value.func
                    if isinstance(func, ast.Name) and func.id == "DeviceInfo":
                        return True
                    if isinstance(func, ast.Attribute) and func.attr == "DeviceInfo":
                        return True
    return False


# ---------------------------------------------------------------------------
# Shared gating for entity rules
# ---------------------------------------------------------------------------


def _gate_entity_rule(
    context: ProjectContext,
    rule_id: str,
    title: str,
    source_url: str,
) -> tuple[Finding | None, Path | None, str]:
    """Shared gating for entity platform rules.

    Returns (early_finding, integration_path, display_path).
    If early_finding is not None, caller should return it immediately.
    """
    fallback_path = "custom_components/<domain>/"

    if context.integration_path is None:
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message="No integration directory was detected.",
                reason="custom_components/<domain>/ must exist before HassCheck can inspect entity platforms.",
                path=fallback_path,
            ),
            None,
            fallback_path,
        )

    display = _display_path(context.integration_path, context, fallback_path)

    # Check if any platform files exist
    platform_files = list(_iter_platform_files(context.integration_path))
    if not platform_files:
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message="No entity platform files found in the integration directory.",
                reason="At least one HA platform file (sensor.py, light.py, etc.) must exist for this rule to apply.",
                path=display,
            ),
            None,
            display,
        )

    return None, context.integration_path, display


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def entity_unique_id_set(context: ProjectContext) -> Finding:
    """Check that at least one entity platform file sets _attr_unique_id."""
    rule_id = "entity.unique_id.set"
    title = "Entity sets _attr_unique_id"

    early, integration_path, display = _gate_entity_rule(
        context, rule_id, title, _UNIQUE_ID_SOURCE
    )
    if early is not None:
        return early

    assert integration_path is not None
    any_match, parse_errors = _inspect_entity_files_for(
        integration_path, _entity_file_sets_unique_id
    )

    if any_match:
        return _make_finding(
            rule_id,
            title,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.PASS,
            message="At least one entity platform file sets _attr_unique_id.",
            reason="A unique ID is required for entities to support the entity registry and avoid duplicates.",
            path=display,
        )

    if parse_errors:
        return _make_finding(
            rule_id,
            title,
            _UNIQUE_ID_SOURCE,
            status=RuleStatus.WARN,
            message=f"Could not parse some platform files; _attr_unique_id presence cannot be determined. Files: {', '.join(parse_errors)}",
            reason="Platform files exist but contain syntax errors.",
            path=display,
            fix=FixSuggestion(summary="Fix syntax errors in platform files."),
        )

    return _make_finding(
        rule_id,
        title,
        _UNIQUE_ID_SOURCE,
        status=RuleStatus.WARN,
        message="No entity platform file sets _attr_unique_id; entities will not be registered in the entity registry.",
        reason="A unique ID is required for entities to support the entity registry and avoid duplicates.",
        path=display,
        fix=FixSuggestion(
            summary="Set self._attr_unique_id or the class attribute _attr_unique_id in each entity class.",
            docs_url=_UNIQUE_ID_SOURCE,
        ),
    )


def entity_has_entity_name_set(context: ProjectContext) -> Finding:
    """Check that at least one entity platform file sets _attr_has_entity_name = True."""
    rule_id = "entity.has_entity_name.set"
    title = "Entity sets _attr_has_entity_name = True"

    early, integration_path, display = _gate_entity_rule(
        context, rule_id, title, _HAS_ENTITY_NAME_SOURCE
    )
    if early is not None:
        return early

    assert integration_path is not None
    any_match, parse_errors = _inspect_entity_files_for(
        integration_path, _entity_file_has_entity_name_true
    )

    if any_match:
        return _make_finding(
            rule_id,
            title,
            _HAS_ENTITY_NAME_SOURCE,
            status=RuleStatus.PASS,
            message="At least one entity platform file sets _attr_has_entity_name = True.",
            reason="_attr_has_entity_name = True is mandatory for new integrations per HA 2023.x+ guidelines.",
            path=display,
        )

    if parse_errors:
        return _make_finding(
            rule_id,
            title,
            _HAS_ENTITY_NAME_SOURCE,
            status=RuleStatus.WARN,
            message=f"Could not parse some platform files; _attr_has_entity_name presence cannot be determined. Files: {', '.join(parse_errors)}",
            reason="Platform files exist but contain syntax errors.",
            path=display,
            fix=FixSuggestion(summary="Fix syntax errors in platform files."),
        )

    return _make_finding(
        rule_id,
        title,
        _HAS_ENTITY_NAME_SOURCE,
        status=RuleStatus.WARN,
        message="No entity platform file sets _attr_has_entity_name = True; entity naming may not follow HA guidelines.",
        reason="_attr_has_entity_name = True is mandatory for new integrations per HA 2023.x+ guidelines.",
        path=display,
        fix=FixSuggestion(
            summary="Add _attr_has_entity_name = True to each entity class.",
            docs_url=_HAS_ENTITY_NAME_SOURCE,
        ),
    )


def entity_device_info_set(context: ProjectContext) -> Finding:
    """Check that at least one entity platform file sets device_info."""
    rule_id = "entity.device_info.set"
    title = "Entity sets device_info"

    early, integration_path, display = _gate_entity_rule(
        context, rule_id, title, _DEVICE_INFO_SOURCE
    )
    if early is not None:
        return early

    assert integration_path is not None
    any_match, parse_errors = _inspect_entity_files_for(
        integration_path, _entity_file_sets_device_info
    )

    if any_match:
        return _make_finding(
            rule_id,
            title,
            _DEVICE_INFO_SOURCE,
            status=RuleStatus.PASS,
            message="At least one entity platform file sets device_info.",
            reason="Providing device_info groups entities under a device in the device registry.",
            path=display,
        )

    if parse_errors:
        return _make_finding(
            rule_id,
            title,
            _DEVICE_INFO_SOURCE,
            status=RuleStatus.WARN,
            message=f"Could not parse some platform files; device_info presence cannot be determined. Files: {', '.join(parse_errors)}",
            reason="Platform files exist but contain syntax errors.",
            path=display,
            fix=FixSuggestion(summary="Fix syntax errors in platform files."),
        )

    return _make_finding(
        rule_id,
        title,
        _DEVICE_INFO_SOURCE,
        status=RuleStatus.WARN,
        message="No entity platform file sets device_info; entities will not be grouped under a device.",
        reason="Providing device_info groups entities under a device in the device registry.",
        path=display,
        fix=FixSuggestion(
            summary="Set self._attr_device_info = DeviceInfo(...) in each entity class.",
            docs_url=_DEVICE_INFO_SOURCE,
        ),
    )


# ---------------------------------------------------------------------------
# Rule registry entries
# ---------------------------------------------------------------------------

RULES: list[RuleDefinition] = [
    RuleDefinition(
        id="entity.unique_id.set",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="Entity sets _attr_unique_id",
        why=(
            "A unique ID is required for entities to be tracked across restarts, to support "
            "entity customisation and to avoid duplicates in the entity registry. "
            "Note: this rule uses AST inspection; it checks for _attr_unique_id assignments "
            "at class level or via self._attr_unique_id in any platform file."
        ),
        source_url=_UNIQUE_ID_SOURCE,
        check=entity_unique_id_set,
        overridable=True,
    ),
    RuleDefinition(
        id="entity.has_entity_name.set",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="Entity sets _attr_has_entity_name = True",
        why=(
            "_attr_has_entity_name = True is mandatory for new integrations as of HA 2023.x. "
            "It enables proper entity naming conventions where the device name is the prefix. "
            "Note: this rule only triggers PASS for literal True; False is treated as absent."
        ),
        source_url=_HAS_ENTITY_NAME_SOURCE,
        check=entity_has_entity_name_set,
        overridable=True,
    ),
    RuleDefinition(
        id="entity.device_info.set",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="Entity sets device_info",
        why=(
            "Providing device_info groups entities under a device in the device registry, "
            "improving the user experience in Settings → Devices & Services. "
            "Note: this rule uses AST inspection; it checks for _attr_device_info assignment "
            "or a device_info property/method returning DeviceInfo(...)."
        ),
        source_url=_DEVICE_INFO_SOURCE,
        check=entity_device_info_set,
        overridable=True,
    ),
]
