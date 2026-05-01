"""Tests for diagnostics.redaction.used rule (PR4, #53).

TDD cycle:
  - RED: written first, references production code that does not yet exist
  - GREEN: confirmed after implementation

Spec: sdd/v0-8-rule-depth/spec — Domain: diagnostics-rules (#53)
Design: D1 (AST helpers + _DiagnosticsSignals), D6 (scaffold compatibility), D7 (exact message strings)
"""

from __future__ import annotations

from pathlib import Path

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RULE_ID = "diagnostics.redaction.used"


def _write_integration(
    root: Path,
    *,
    dir_name: str = "test_integration",
    manifest: str | None = None,
    diagnostics_src: str | None = None,
) -> Path:
    """Create custom_components/<dir_name>/ with optional manifest and diagnostics.py."""
    integration = root / "custom_components" / dir_name
    integration.mkdir(parents=True)

    mf = manifest or (
        '{"domain": "'
        + dir_name
        + '", "name": "Test", "documentation": "https://example.com",'
        ' "issue_tracker": "https://example.com/issues", "codeowners": ["@test"],'
        ' "version": "0.1.0", "config_flow": true}'
    )
    (integration / "manifest.json").write_text(mf, encoding="utf-8")

    if diagnostics_src is not None:
        (integration / "diagnostics.py").write_text(diagnostics_src, encoding="utf-8")

    return integration


def _finding_for(root: Path):
    return {f.rule_id: f for f in run_check(root).findings}[RULE_ID]


# ---------------------------------------------------------------------------
# Rule registration — metadata + explain reachability
# ---------------------------------------------------------------------------


def test_rule_is_registered() -> None:
    rule = RULES_BY_ID[RULE_ID]
    assert rule.id == RULE_ID
    assert rule.version == "1.0.0"
    assert rule.category == "diagnostics_repairs"
    assert str(rule.severity) == "recommended"
    assert rule.overridable is True
    assert rule.why, "why must be non-empty"


def test_why_mentions_ast_limitations_and_manual_review() -> None:
    """Spec: AST Limitation Documented for diagnostics.redaction.used."""
    rule = RULES_BY_ID[RULE_ID]
    why_lower = rule.why.lower()
    # Must mention AST limitations
    assert "ast" in why_lower or "static" in why_lower or "inspect" in why_lower, (
        "why must mention AST inspection limitations"
    )
    # Must mention manual review boundary
    assert "manual" in why_lower or "manual_review" in why_lower, (
        "why must mention the MANUAL_REVIEW boundary"
    )


# ---------------------------------------------------------------------------
# NOT_APPLICABLE: no integration directory
# ---------------------------------------------------------------------------


def test_not_applicable_when_no_integration_directory(tmp_path: Path) -> None:
    """No custom_components/ → NOT_APPLICABLE."""
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# NOT_APPLICABLE: diagnostics.py does not exist in integration
# ---------------------------------------------------------------------------


def test_not_applicable_when_no_diagnostics_file(tmp_path: Path) -> None:
    """Integration directory without diagnostics.py → NOT_APPLICABLE."""
    _write_integration(tmp_path)  # no diagnostics_src
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# NOT_APPLICABLE: diagnostics.py exists but has no diagnostics function
# ---------------------------------------------------------------------------


def test_not_applicable_when_diagnostics_file_has_no_diagnostics_function(
    tmp_path: Path,
) -> None:
    """diagnostics.py exists but defines no async_get_config_entry_diagnostics
    or async_get_device_diagnostics → NOT_APPLICABLE (empty stub)."""
    src = """\
# Empty diagnostics stub — no function defined yet
TO_REDACT: list[str] = []
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# NOT_APPLICABLE: supports_diagnostics=False in hasscheck.yaml applicability
# ---------------------------------------------------------------------------


def test_not_applicable_when_supports_diagnostics_false(tmp_path: Path) -> None:
    """Applicability flag supports_diagnostics=False → NOT_APPLICABLE."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    return {}
"""
    _write_integration(tmp_path, diagnostics_src=src)
    (tmp_path / "hasscheck.yaml").write_text(
        "applicability:\n  supports_diagnostics: false\n", encoding="utf-8"
    )
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# PASS: async_redact_data imported and called
# ---------------------------------------------------------------------------


def test_pass_when_async_redact_data_imported_and_called(tmp_path: Path) -> None:
    """PASS when diagnostics.py imports and calls async_redact_data."""
    src = """\
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = ["api_key", "password"]


async def async_get_config_entry_diagnostics(hass, entry):
    return async_redact_data(dict(entry.data), TO_REDACT)
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# PASS: local helper named redact_data — defined AND called
# ---------------------------------------------------------------------------


def test_pass_when_local_redact_data_defined_and_called(tmp_path: Path) -> None:
    """PASS when local helper 'redact_data' is defined and called in diagnostics.py."""
    src = """\
TO_REDACT = ["api_key"]


async def async_get_config_entry_diagnostics(hass, entry):
    return {"entry": redact_data(dict(entry.data), TO_REDACT)}


def redact_data(data, to_redact):
    return {k: "**REDACTED**" if k in to_redact else v for k, v in data.items()}
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# PASS: local helper named _redact_secrets — defined AND called
# ---------------------------------------------------------------------------


def test_pass_when_local_underscore_redact_helper_defined_and_called(
    tmp_path: Path,
) -> None:
    """PASS when local helper '_redact_secrets' (matching ^_?redact(_.*)?$) defined+called."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    return _redact_secrets(dict(entry.data))


def _redact_secrets(data):
    data.pop("api_key", None)
    return data
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# PASS: local helper named redact_x (matches ^_?redact(_.*)?$) — defined AND called
# ---------------------------------------------------------------------------


def test_pass_when_redact_x_helper_defined_and_called(tmp_path: Path) -> None:
    """PASS when local helper name matches ^_?redact(_.*)?$ and is both defined and called."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    return {"data": redact_sensitive(entry.data)}


def redact_sensitive(data):
    return {k: v for k, v in data.items() if k != "password"}
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# Edge: local helper defined but never called → NOT a PASS
# ---------------------------------------------------------------------------


def test_not_pass_when_helper_defined_but_never_called(tmp_path: Path) -> None:
    """Local helper defined but not called → should NOT be PASS (must be both defined AND used)."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    # Forgot to call the helper
    return dict(entry.data)


def redact_data(data, to_redact):
    return {k: "**REDACTED**" if k in to_redact else v for k, v in data.items()}
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    # Helper defined but not called — raw return is detected → WARN
    assert f.status is RuleStatus.WARN


# ---------------------------------------------------------------------------
# WARN (strong): raw entry.data returned
# ---------------------------------------------------------------------------


def test_warn_strong_when_entry_data_returned_raw(tmp_path: Path) -> None:
    """Spec: strong WARN when entry.data returned without redaction."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    return entry.data
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    assert "likely exposes secrets" in f.message


# ---------------------------------------------------------------------------
# WARN (strong): dict(entry.data) returned raw
# ---------------------------------------------------------------------------


def test_warn_strong_when_dict_entry_data_returned_raw(tmp_path: Path) -> None:
    """Spec: strong WARN when dict(entry.data) returned without redaction."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    return dict(entry.data)
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    assert "likely exposes secrets" in f.message


# ---------------------------------------------------------------------------
# WARN (strong): entry.options returned raw
# ---------------------------------------------------------------------------


def test_warn_strong_when_entry_options_returned_raw(tmp_path: Path) -> None:
    """Spec: strong WARN when entry.options returned without redaction."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    return entry.options
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    assert "likely exposes secrets" in f.message


# ---------------------------------------------------------------------------
# WARN (strong): config_entry.data returned raw
# ---------------------------------------------------------------------------


def test_warn_strong_when_config_entry_data_returned_raw(tmp_path: Path) -> None:
    """Spec: strong WARN when config_entry.data returned without redaction."""
    src = """\
async def async_get_device_diagnostics(hass, config_entry, device):
    return config_entry.data
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    assert "likely exposes secrets" in f.message


# ---------------------------------------------------------------------------
# WARN (generic): diagnostics function exists, no redaction, no suspicious return
# ---------------------------------------------------------------------------


def test_warn_generic_when_no_redaction_and_no_raw_return(tmp_path: Path) -> None:
    """WARN (generic) when diagnostics function exists but no recognized redaction pattern."""
    src = """\
async def async_get_config_entry_diagnostics(hass, entry):
    return {"device_info": "some_static_data"}
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    # Generic wording — not the strong "likely exposes secrets" message
    assert "likely exposes secrets" not in f.message


# ---------------------------------------------------------------------------
# WARN: parse error (syntax error in diagnostics.py)
# ---------------------------------------------------------------------------


def test_warn_when_diagnostics_has_syntax_error(tmp_path: Path) -> None:
    """Parse error → WARN with message containing 'could not be parsed'."""
    src = """\
def broken(
    # unclosed parenthesis — invalid Python
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    assert "could not be parsed" in f.message


# ---------------------------------------------------------------------------
# Scaffold template compatibility
# ---------------------------------------------------------------------------


def test_scaffold_template_passes_rule(tmp_path: Path) -> None:
    """Spec: Scaffold Template Passes Rule.

    The existing scaffold template uses a local redact_data() helper that is
    both defined and called — this must satisfy pattern (2) in design D6 and
    produce PASS (not WARN).
    """
    # Reproduce the scaffold template content verbatim (local redact_data defined+called)
    src = """\
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# Add any keys that should be redacted from diagnostics output.
# Common sensitive fields: API keys, tokens, passwords, location data.
# Upgrade path: use homeassistant.components.diagnostics.async_redact_data
# for the official HA redaction helper instead of a local implementation.
TO_REDACT: list[str] = [
    "api_key",
    "password",
    "token",
    "latitude",
    "longitude",
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    \"\"\"Return diagnostics for a config entry.\"\"\"
    return {
        "entry": redact_data(dict(entry.data), TO_REDACT),
        "options": redact_data(dict(entry.options), TO_REDACT),
    }


def redact_data(data: dict[str, Any], to_redact: list[str]) -> dict[str, Any]:
    \"\"\"Redact sensitive data from a dict.\"\"\"
    redacted = dict(data)
    for key in to_redact:
        if key in redacted:
            redacted[key] = "**REDACTED**"
    return redacted
"""
    _write_integration(tmp_path, diagnostics_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.PASS, (
        f"scaffold template should PASS diagnostics.redaction.used, got {f.status}: {f.message}"
    )
