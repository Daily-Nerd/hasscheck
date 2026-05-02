from __future__ import annotations

import ast
import re
from dataclasses import dataclass

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

CATEGORY = "diagnostics_repairs"
DIAGNOSTICS_SOURCE = (
    "https://developers.home-assistant.io/docs/core/integration/diagnostics/"
)
# Source: https://developers.home-assistant.io/docs/core/integration-diagnostics
# _SOURCE_CHECKED_AT = "2026-05-01"

_DIAGNOSTICS_FUNC_NAMES = frozenset(
    {"async_get_config_entry_diagnostics", "async_get_device_diagnostics"}
)
_LOCAL_REDACT_RE = re.compile(r"^_?redact(_.*)?$")


@dataclass(frozen=True)
class _DiagnosticsSignals:
    # Per design D6 (v0.8 PR4) and #106 Path B: import without a call is not
    # evidence of active redaction. PASS resolution requires an actual call.
    calls_async_redact: bool
    calls_local_redact: bool  # local def + call to name matching ^_?redact(_.*)?$
    returns_raw_entry_data: (
        bool  # Return with attribute entry.data/options or config_entry.data
    )


def _diagnostics_signals(tree: ast.Module) -> _DiagnosticsSignals:
    """Walk the AST and extract redaction-related signals."""
    calls_async_redact = False

    # Collect names of local functions matching the redact pattern
    local_redact_defs: set[str] = set()
    # Collect all Name nodes used in calls to detect if helper is called
    called_names: set[str] = set()
    returns_raw_entry_data = False

    for node in ast.walk(tree):
        # Detect calls to async_redact_data (Name or Attribute)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "async_redact_data":
                calls_async_redact = True
            elif isinstance(func, ast.Attribute) and func.attr == "async_redact_data":
                calls_async_redact = True
            # Track all function calls by name
            if isinstance(func, ast.Name):
                called_names.add(func.id)

        # Collect local function definitions matching the redact pattern
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _LOCAL_REDACT_RE.match(node.name):
                local_redact_defs.add(node.name)

        # Detect raw entry.data / entry.options / config_entry.data returns
        if isinstance(node, ast.Return) and node.value is not None:
            val = node.value
            # Pattern: entry.data or entry.options or config_entry.data
            if isinstance(val, ast.Attribute) and val.attr in {"data", "options"}:
                if isinstance(val.value, ast.Name) and val.value.id in {
                    "entry",
                    "config_entry",
                }:
                    returns_raw_entry_data = True
            # Pattern: dict(entry.data) or dict(entry.options) or dict(config_entry.data)
            elif (
                isinstance(val, ast.Call)
                and isinstance(val.func, ast.Name)
                and val.func.id == "dict"
                and val.args
            ):
                arg0 = val.args[0]
                if isinstance(arg0, ast.Attribute) and arg0.attr in {"data", "options"}:
                    if isinstance(arg0.value, ast.Name) and arg0.value.id in {
                        "entry",
                        "config_entry",
                    }:
                        returns_raw_entry_data = True

    # A local redact helper counts only if it is both defined AND called elsewhere
    calls_local_redact = bool(local_redact_defs & called_names)

    return _DiagnosticsSignals(
        calls_async_redact=calls_async_redact,
        calls_local_redact=calls_local_redact,
        returns_raw_entry_data=returns_raw_entry_data,
    )


def _has_diagnostics_function(tree: ast.Module) -> bool:
    """Return True if tree contains any async diagnostics function."""
    return any(
        isinstance(node, ast.AsyncFunctionDef) and node.name in _DIAGNOSTICS_FUNC_NAMES
        for node in ast.walk(tree)
    )


_REDACTION_WHY = (
    "Home Assistant diagnostics expose integration state for troubleshooting. "
    "Without redaction, sensitive fields (API keys, tokens, passwords, coordinates) "
    "can be leaked when users share diagnostic data. "
    "Use async_redact_data from homeassistant.components.diagnostics or a local "
    "redaction helper to strip sensitive keys before returning. "
    "Note: this rule uses AST static inspection and cannot detect redaction performed "
    "in a base class, mixin, or via dynamic dispatch — those cases may produce a "
    "false WARN. A WARN does NOT guarantee a bug; treat it as a prompt for "
    "MANUAL_REVIEW of the diagnostics output."
)


def diagnostics_file_exists(context: ProjectContext) -> Finding:
    if context.integration_path is None:
        return Finding(
            rule_id="diagnostics.file.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py exists",
            message="No integration directory was detected, so diagnostics.py cannot be inspected yet.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect diagnostics.py.",
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=FixSuggestion(
                summary="Create custom_components/<domain>/ before adding diagnostics.py."
            ),
            path="custom_components/<domain>/diagnostics.py",
        )

    path = context.integration_path / "diagnostics.py"
    exists = path.is_file()
    if (
        not exists
        and context.applicability
        and context.applicability.supports_diagnostics is False
    ):
        return Finding(
            rule_id="diagnostics.file.exists",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py exists",
            message="Project config declares diagnostics are not supported by this integration.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="hasscheck.yaml declares supports_diagnostics: false.",
                source="config",
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=None,
            path=str(path.relative_to(context.root)),
        )

    return Finding(
        rule_id="diagnostics.file.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="diagnostics.py exists",
        message=(
            "Integration includes diagnostics.py."
            if exists
            else "Integration does not include diagnostics.py; downloadable troubleshooting data support cannot be inspected."
        ),
        applicability=Applicability(
            reason="Diagnostics help users provide support data while redacting sensitive information."
        ),
        source=RuleSource(url=DIAGNOSTICS_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add diagnostics.py with redaction for sensitive values.",
            command="hasscheck scaffold diagnostics",
            docs_url="https://developers.home-assistant.io/docs/core/integration/diagnostics/",
        ),
        path=str(path.relative_to(context.root)),
    )


def diagnostics_redaction_used(context: ProjectContext) -> Finding:
    """Check that diagnostics.py uses async_redact_data or a local redaction helper."""
    # Guard: no integration directory
    if context.integration_path is None:
        return Finding(
            rule_id="diagnostics.redaction.used",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py uses redaction",
            message="No integration directory was detected.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="custom_components/<domain>/ must exist before HassCheck can inspect diagnostics.py.",
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=None,
            path="custom_components/<domain>/diagnostics.py",
        )

    diagnostics_path = context.integration_path / "diagnostics.py"

    # Guard: applicability flag opts out (regardless of whether file exists)
    if context.applicability and context.applicability.supports_diagnostics is False:
        return Finding(
            rule_id="diagnostics.redaction.used",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py uses redaction",
            message="Project config declares diagnostics are not supported by this integration.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="hasscheck.yaml declares supports_diagnostics: false.",
                source="config",
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=None,
            path=str(diagnostics_path.relative_to(context.root)),
        )

    # Guard: diagnostics.py does not exist
    if not diagnostics_path.is_file():
        return Finding(
            rule_id="diagnostics.redaction.used",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py uses redaction",
            message="diagnostics.py does not exist; redaction usage cannot be inspected.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="diagnostics.py must exist before this rule can run.",
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=None,
            path=str(diagnostics_path.relative_to(context.root)),
        )

    rel_path = str(diagnostics_path.relative_to(context.root))

    # Parse the file
    tree, error = parse_module(diagnostics_path)

    if error is not None:
        return Finding(
            rule_id="diagnostics.redaction.used",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.WARN,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py uses redaction",
            message=f"diagnostics.py could not be parsed ({error}); redaction usage cannot be determined.",
            applicability=Applicability(
                reason="diagnostics.py exists but has a syntax error."
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=FixSuggestion(summary="Fix syntax errors in diagnostics.py."),
            path=rel_path,
        )

    assert tree is not None

    # Guard: no diagnostics function defined — file is empty/stub
    if not _has_diagnostics_function(tree):
        return Finding(
            rule_id="diagnostics.redaction.used",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py uses redaction",
            message="diagnostics.py exists but does not define a diagnostics function.",
            applicability=Applicability(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason="No async_get_config_entry_diagnostics or async_get_device_diagnostics found.",
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=FixSuggestion(
                summary="Add async_get_config_entry_diagnostics or async_get_device_diagnostics to diagnostics.py.",
                command="hasscheck scaffold diagnostics",
            ),
            path=rel_path,
        )

    signals = _diagnostics_signals(tree)

    # Resolution priority per design D6:
    # 1. raw return AND no redaction → WARN (strong)
    # 2. any redaction found → PASS
    # 3. otherwise → WARN (generic)

    if signals.returns_raw_entry_data and not (
        signals.calls_async_redact or signals.calls_local_redact
    ):
        return Finding(
            rule_id="diagnostics.redaction.used",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.WARN,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py uses redaction",
            message=(
                "diagnostics returns entry.data without redaction — "
                "likely exposes secrets; use async_redact_data."
            ),
            applicability=Applicability(
                reason="diagnostics.py returns entry.data or entry.options directly without redacting sensitive fields."
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=FixSuggestion(
                summary="Use async_redact_data or a local redaction helper before returning entry data.",
                docs_url=DIAGNOSTICS_SOURCE,
            ),
            path=rel_path,
        )

    if signals.calls_async_redact or signals.calls_local_redact:
        return Finding(
            rule_id="diagnostics.redaction.used",
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.PASS,
            severity=RuleSeverity.RECOMMENDED,
            title="diagnostics.py uses redaction",
            message="diagnostics.py uses a recognized redaction pattern.",
            applicability=Applicability(
                reason="Redaction protects sensitive fields from being exposed in diagnostic data."
            ),
            source=RuleSource(url=DIAGNOSTICS_SOURCE),
            fix=None,
            path=rel_path,
        )

    # Generic WARN: function exists, no raw return, no recognized redaction
    return Finding(
        rule_id="diagnostics.redaction.used",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="diagnostics.py uses redaction",
        message="diagnostics.py does not appear to redact sensitive data; review manually before relying on diagnostics output.",
        applicability=Applicability(
            reason="diagnostics.py defines a diagnostics function but no recognized redaction pattern was detected."
        ),
        source=RuleSource(url=DIAGNOSTICS_SOURCE),
        fix=FixSuggestion(
            summary="Add async_redact_data or a local redaction helper to strip sensitive keys.",
            docs_url=DIAGNOSTICS_SOURCE,
        ),
        path=rel_path,
    )


RULES = [
    RuleDefinition(
        id="diagnostics.file.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="diagnostics.py exists",
        why="Diagnostics help users and maintainers troubleshoot without exposing secrets when implemented with redaction.",
        source_url=DIAGNOSTICS_SOURCE,
        check=diagnostics_file_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="diagnostics.redaction.used",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="diagnostics.py uses redaction",
        why=_REDACTION_WHY,
        source_url=DIAGNOSTICS_SOURCE,
        check=diagnostics_redaction_used,
        overridable=True,
    ),
]
