from __future__ import annotations

import ast
import re
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

CATEGORY = "tests_ci"
TESTS_SOURCE = "https://developers.home-assistant.io/docs/development_testing/"
_SOURCE_CHECKED_AT = "2026-05-01"

# ---------------------------------------------------------------------------
# Regex patterns for new detection rules (#108)
# ---------------------------------------------------------------------------
_CONFIG_FLOW_FILE_RE = re.compile(r"^test_config_flow.*\.py$")
_CONFIG_FLOW_FUNC_RE = re.compile(r"^test_(config_flow|async_step)")
_SETUP_ENTRY_NAMES = frozenset({"async_setup_entry", "async_unload_entry"})
_UNLOAD_NAMES = frozenset({"async_unload_entry"})
_UNLOAD_FUNC_RE = re.compile(r"^test_(unload|async_unload)")
_SETUP_FUNC_RE = re.compile(r"^test_(setup_entry|async_setup_entry)")


# ---------------------------------------------------------------------------
# Helpers for tests.folder.exists (pre-existing rule)
# ---------------------------------------------------------------------------


def tests_folder_exists(context: ProjectContext) -> Finding:
    path = context.root / "tests"
    exists = path.is_dir()
    return Finding(
        rule_id="tests.folder.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="tests folder exists",
        message=(
            "Repository contains a tests directory."
            if exists
            else "Repository does not contain a tests directory; automated test coverage cannot be inspected."
        ),
        applicability=Applicability(
            reason="Tests help maintainers keep integration behavior stable as Home Assistant evolves."
        ),
        source=RuleSource(url=TESTS_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add a tests/ directory with pytest-based integration tests."
        ),
        path="tests",
    )


# ---------------------------------------------------------------------------
# Helpers for detection rules (#108)
# ---------------------------------------------------------------------------


def _iter_test_files(root: Path) -> Iterable[Path]:
    """Yield all .py files under <root>/tests/ if the folder exists."""
    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return
    yield from tests_dir.rglob("*.py")


def _module_imports(tree: ast.Module, target: str) -> bool:
    """True if any import statement references a name containing *target*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if target in alias.name:
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if target in module:
                return True
            for alias in node.names:
                if target in alias.name:
                    return True
    return False


def _module_function_names(tree: ast.Module) -> Iterable[str]:
    """Yield names of all FunctionDef and AsyncFunctionDef nodes in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name


def _module_references_name(tree: ast.Module, target: str) -> bool:
    """True if any Name or Attribute node references *target*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == target:
            return True
        if isinstance(node, ast.Attribute) and node.attr == target:
            return True
    return False


def _make_detection_not_applicable(
    rule_id: str,
    title: str,
    reason: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.RECOMMENDED,
        title=title,
        message=reason,
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason=reason,
        ),
        source=RuleSource(url=TESTS_SOURCE),
        fix=None,
        path="tests",
    )


def _make_detection_finding(
    rule_id: str,
    title: str,
    *,
    status: RuleStatus,
    message: str,
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
        applicability=Applicability(
            reason="Integration tests validate that setup, teardown, and config flow work correctly."
        ),
        source=RuleSource(url=TESTS_SOURCE),
        fix=fix,
        path="tests",
    )


def _gate_detection_rule(
    context: ProjectContext,
    rule_id: str,
    title: str,
) -> Finding | None:
    """Return a NOT_APPLICABLE finding if the rule cannot run, else None."""
    if context.integration_path is None:
        return _make_detection_not_applicable(
            rule_id,
            title,
            "No integration directory was detected.",
        )
    tests_dir = context.root / "tests"
    if not tests_dir.is_dir():
        return _make_detection_not_applicable(
            rule_id,
            title,
            "no tests/ folder; tests.folder.exists owns this signal.",
        )
    return None


# ---------------------------------------------------------------------------
# Check functions — test detection rules (#108)
# ---------------------------------------------------------------------------


def tests_config_flow_detected(context: ProjectContext) -> Finding:
    """Detect whether any test file covers config_flow paths."""
    rule_id = "tests.config_flow.detected"
    title = "tests cover config_flow"

    early = _gate_detection_rule(context, rule_id, title)
    if early is not None:
        return early

    has_parse_errors = False
    for path in _iter_test_files(context.root):
        # Filename pattern check — no parsing needed
        if _CONFIG_FLOW_FILE_RE.match(path.name):
            return _make_detection_finding(
                rule_id,
                title,
                status=RuleStatus.PASS,
                message=f"Config flow test file detected: {path.name}.",
            )

        tree, error = parse_module(path)
        if error is not None:
            has_parse_errors = True
            continue

        assert tree is not None
        if _module_imports(tree, "config_flow"):
            return _make_detection_finding(
                rule_id,
                title,
                status=RuleStatus.PASS,
                message=f"Config flow import detected in {path.name}.",
            )
        if any(_CONFIG_FLOW_FUNC_RE.match(fn) for fn in _module_function_names(tree)):
            return _make_detection_finding(
                rule_id,
                title,
                status=RuleStatus.PASS,
                message=f"Config flow test function detected in {path.name}.",
            )

    warn_message = "tests/ folder exists but no config_flow test coverage detected." + (
        " (some files could not be parsed)" if has_parse_errors else ""
    )
    return _make_detection_finding(
        rule_id,
        title,
        status=RuleStatus.WARN,
        message=warn_message,
        fix=FixSuggestion(
            summary="Add tests/test_config_flow.py to test the config flow user step.",
            docs_url=TESTS_SOURCE,
        ),
    )


def tests_setup_entry_detected(context: ProjectContext) -> Finding:
    """Detect whether any test file covers async_setup_entry or async_unload_entry."""
    rule_id = "tests.setup_entry.detected"
    title = "tests cover async_setup_entry"

    early = _gate_detection_rule(context, rule_id, title)
    if early is not None:
        return early

    has_parse_errors = False
    for path in _iter_test_files(context.root):
        tree, error = parse_module(path)
        if error is not None:
            has_parse_errors = True
            continue

        assert tree is not None
        for name in _SETUP_ENTRY_NAMES:
            if _module_references_name(tree, name):
                return _make_detection_finding(
                    rule_id,
                    title,
                    status=RuleStatus.PASS,
                    message=f"{name} reference detected in {path.name}.",
                )
        if any(_SETUP_FUNC_RE.match(fn) for fn in _module_function_names(tree)):
            return _make_detection_finding(
                rule_id,
                title,
                status=RuleStatus.PASS,
                message=f"setup_entry test function detected in {path.name}.",
            )

    warn_message = (
        "tests/ folder exists but no async_setup_entry test coverage detected."
        + (" (some files could not be parsed)" if has_parse_errors else "")
    )
    return _make_detection_finding(
        rule_id,
        title,
        status=RuleStatus.WARN,
        message=warn_message,
        fix=FixSuggestion(
            summary="Add a test that calls async_setup_entry and async_unload_entry.",
            docs_url=TESTS_SOURCE,
        ),
    )


def tests_unload_detected(context: ProjectContext) -> Finding:
    """Detect whether any test file covers async_unload_entry."""
    rule_id = "tests.unload.detected"
    title = "tests cover async_unload_entry"

    early = _gate_detection_rule(context, rule_id, title)
    if early is not None:
        return early

    has_parse_errors = False
    for path in _iter_test_files(context.root):
        tree, error = parse_module(path)
        if error is not None:
            has_parse_errors = True
            continue

        assert tree is not None
        if _module_references_name(tree, "async_unload_entry"):
            return _make_detection_finding(
                rule_id,
                title,
                status=RuleStatus.PASS,
                message=f"async_unload_entry reference detected in {path.name}.",
            )
        if any(_UNLOAD_FUNC_RE.match(fn) for fn in _module_function_names(tree)):
            return _make_detection_finding(
                rule_id,
                title,
                status=RuleStatus.PASS,
                message=f"Unload test function detected in {path.name}.",
            )

    warn_message = (
        "tests/ folder exists but no async_unload_entry test coverage detected."
        + (" (some files could not be parsed)" if has_parse_errors else "")
    )
    return _make_detection_finding(
        rule_id,
        title,
        status=RuleStatus.WARN,
        message=warn_message,
        fix=FixSuggestion(
            summary="Add a test that calls async_unload_entry to verify clean teardown.",
            docs_url=TESTS_SOURCE,
        ),
    )


RULES = [
    RuleDefinition(
        id="tests.folder.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="tests folder exists",
        why="Tests provide maintainers a safety net for future Home Assistant and integration changes.",
        source_url=TESTS_SOURCE,
        check=tests_folder_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="tests.config_flow.detected",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="tests cover config_flow",
        why=(
            "Config flow tests verify that users can set up, authenticate, and configure "
            "the integration from the UI. Without them, regressions in the setup path "
            "may go undetected across Home Assistant upgrades. "
            "This rule uses heuristic static inspection: filename pattern, import analysis, "
            "and function name matching — no test execution is performed."
        ),
        source_url=TESTS_SOURCE,
        check=tests_config_flow_detected,
        overridable=True,
    ),
    RuleDefinition(
        id="tests.setup_entry.detected",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="tests cover async_setup_entry",
        why=(
            "async_setup_entry is the primary integration lifecycle hook. Testing it ensures "
            "the integration loads correctly and fails gracefully on bad configuration. "
            "This rule uses heuristic static inspection: Name/Attribute references to "
            "async_setup_entry / async_unload_entry, and function name matching."
        ),
        source_url=TESTS_SOURCE,
        check=tests_setup_entry_detected,
        overridable=True,
    ),
    RuleDefinition(
        id="tests.unload.detected",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="tests cover async_unload_entry",
        why=(
            "Testing async_unload_entry ensures the integration cleans up resources properly "
            "when removed or reloaded. Missing unload tests can hide resource leaks. "
            "This rule uses heuristic static inspection: Name/Attribute references to "
            "async_unload_entry, and function name matching."
        ),
        source_url=TESTS_SOURCE,
        check=tests_unload_detected,
        overridable=True,
    ),
]
