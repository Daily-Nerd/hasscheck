"""Rules checking __init__.py patterns for modern HA integrations (issue #107).

Rules:
  - init.async_setup_entry.defined
  - init.runtime_data.used

Category: modern_ha_patterns
Severity: RECOMMENDED
"""

from __future__ import annotations

import ast

from hasscheck.ast_utils import has_async_function, parse_module
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
_INIT_FILE = "__init__.py"

_SOURCE_CHECKED_AT = "2026-05-01"

_ASYNC_SETUP_ENTRY_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_index/#an-example"
)
_RUNTIME_DATA_SOURCE = (
    "https://developers.home-assistant.io/docs/config_entries_index/#runtime_data"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _display_path(path, context: ProjectContext, fallback: str) -> str:
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


def _gate_init_rule(
    context: ProjectContext,
    rule_id: str,
    title: str,
    source_url: str,
) -> tuple[Finding | None, ast.Module | None, str]:
    """Shared gating for __init__.py rules.

    Returns (early_finding, tree, display_path).
    If early_finding is not None, the caller should return it immediately.
    """
    fallback_path = f"custom_components/<domain>/{_INIT_FILE}"

    if context.integration_path is None:
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message="No integration directory was detected.",
                reason=f"custom_components/<domain>/ must exist before HassCheck can inspect {_INIT_FILE}.",
                path=fallback_path,
            ),
            None,
            fallback_path,
        )

    init_path = context.integration_path / _INIT_FILE
    display = _display_path(init_path, context, fallback_path)

    if not init_path.is_file():
        return (
            _make_not_applicable(
                rule_id,
                title,
                source_url,
                message=f"{_INIT_FILE} does not exist; this rule cannot be checked.",
                reason=f"{_INIT_FILE} must exist before this rule can run.",
                path=display,
            ),
            None,
            display,
        )

    tree, error = parse_module(init_path)
    if error is not None:
        return (
            _make_finding(
                rule_id,
                title,
                source_url,
                status=RuleStatus.WARN,
                message=f"{_INIT_FILE} could not be parsed ({error}); {title.lower()} cannot be determined.",
                reason=f"{_INIT_FILE} exists but has a syntax error.",
                path=display,
                fix=FixSuggestion(summary=f"Fix syntax errors in {_INIT_FILE}."),
            ),
            None,
            display,
        )

    return None, tree, display


# ---------------------------------------------------------------------------
# Detection predicates
# ---------------------------------------------------------------------------


def _has_runtime_data_usage(tree: ast.Module) -> bool:
    """Return True if any Attribute with attr='runtime_data' is accessed on
    a Name whose id is in {entry, config_entry, _entry}.
    """
    targets = {"entry", "config_entry", "_entry"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "runtime_data":
            if isinstance(node.value, ast.Name) and node.value.id in targets:
                return True
    return False


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def init_async_setup_entry_defined(context: ProjectContext) -> Finding:
    """Check that __init__.py defines async_setup_entry."""
    rule_id = "init.async_setup_entry.defined"
    title = "__init__.py defines async_setup_entry"

    early, tree, display = _gate_init_rule(
        context, rule_id, title, _ASYNC_SETUP_ENTRY_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None
    if has_async_function(tree, "async_setup_entry"):
        return _make_finding(
            rule_id,
            title,
            _ASYNC_SETUP_ENTRY_SOURCE,
            status=RuleStatus.PASS,
            message="__init__.py defines async_setup_entry.",
            reason="async_setup_entry is the standard entry point for config-entry-based integrations.",
            path=display,
        )

    return _make_finding(
        rule_id,
        title,
        _ASYNC_SETUP_ENTRY_SOURCE,
        status=RuleStatus.WARN,
        message="__init__.py does not define async_setup_entry; the integration may not support config entries.",
        reason="async_setup_entry is the standard entry point for config-entry-based integrations.",
        path=display,
        fix=FixSuggestion(
            summary="Add async_setup_entry(hass, entry) to __init__.py.",
            docs_url=_ASYNC_SETUP_ENTRY_SOURCE,
        ),
    )


def init_runtime_data_used(context: ProjectContext) -> Finding:
    """Check that __init__.py uses entry.runtime_data (HA 2024.4+ pattern)."""
    rule_id = "init.runtime_data.used"
    title = "__init__.py uses entry.runtime_data"

    early, tree, display = _gate_init_rule(
        context, rule_id, title, _RUNTIME_DATA_SOURCE
    )
    if early is not None:
        return early

    assert tree is not None
    if _has_runtime_data_usage(tree):
        return _make_finding(
            rule_id,
            title,
            _RUNTIME_DATA_SOURCE,
            status=RuleStatus.PASS,
            message="__init__.py uses entry.runtime_data.",
            reason="entry.runtime_data is the HA 2024.4+ recommended way to store per-entry runtime objects.",
            path=display,
        )

    return _make_finding(
        rule_id,
        title,
        _RUNTIME_DATA_SOURCE,
        status=RuleStatus.WARN,
        message=(
            "__init__.py does not use entry.runtime_data; "
            "consider migrating from hass.data to entry.runtime_data."
        ),
        reason="entry.runtime_data is the HA 2024.4+ recommended way to store per-entry runtime objects.",
        path=display,
        fix=FixSuggestion(
            summary="Replace hass.data[DOMAIN][entry.entry_id] with entry.runtime_data = <your object>.",
            docs_url=_RUNTIME_DATA_SOURCE,
        ),
    )


# ---------------------------------------------------------------------------
# Rule registry entries
# ---------------------------------------------------------------------------

RULES: list[RuleDefinition] = [
    RuleDefinition(
        id="init.async_setup_entry.defined",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="__init__.py defines async_setup_entry",
        why=(
            "async_setup_entry is the standard entry point for config-entry-based integrations. "
            "Without it, the integration cannot be loaded by Home Assistant when a config entry exists. "
            "Note: this rule uses AST inspection and cannot detect async_setup_entry defined only in "
            "a base class or via dynamic attribute assignment."
        ),
        source_url=_ASYNC_SETUP_ENTRY_SOURCE,
        check=init_async_setup_entry_defined,
        overridable=True,
    ),
    RuleDefinition(
        id="init.runtime_data.used",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="__init__.py uses entry.runtime_data",
        why=(
            "entry.runtime_data is the HA 2024.4+ recommended way to store per-entry runtime objects "
            "instead of the older hass.data[DOMAIN][entry.entry_id] pattern. "
            "Note: this rule uses AST inspection; it looks for attribute access on names "
            "'entry', 'config_entry', or '_entry'."
        ),
        source_url=_RUNTIME_DATA_SOURCE,
        check=init_runtime_data_used,
        overridable=True,
    ),
]
