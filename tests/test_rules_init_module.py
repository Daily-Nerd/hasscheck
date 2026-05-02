"""Tests for init_module rules (issue #107, v0.10 third batch).

TDD cycle:
  - RED: written first, before production code exists
  - GREEN: confirmed after implementation

Rules covered:
  - init.async_setup_entry.defined
  - init.runtime_data.used

Spec: issue #107 — modern HA pattern checks
"""

from __future__ import annotations

from pathlib import Path

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_integration(
    root: Path,
    *,
    dir_name: str = "test_integration",
    manifest: str | None = None,
    init_src: str | None = None,
) -> Path:
    """Create custom_components/<dir_name>/ with optional manifest and __init__.py."""
    integration = root / "custom_components" / dir_name
    integration.mkdir(parents=True)

    mf = manifest or (
        '{"domain": "'
        + dir_name
        + '", "name": "Test", "documentation": "https://example.com",'
        ' "issue_tracker": "https://example.com/issues", "codeowners": ["@test"],'
        ' "version": "0.1.0"}'
    )
    (integration / "manifest.json").write_text(mf, encoding="utf-8")

    if init_src is not None:
        (integration / "__init__.py").write_text(init_src, encoding="utf-8")

    return integration


def _finding_for(root: Path, rule_id: str):
    return {f.rule_id: f for f in run_check(root).findings}[rule_id]


# ===========================================================================
# init.async_setup_entry.defined
# ===========================================================================

ASYNC_SETUP_ENTRY_RULE = "init.async_setup_entry.defined"


class TestAsyncSetupEntryDefined:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[ASYNC_SETUP_ENTRY_RULE]
        assert rule.id == ASYNC_SETUP_ENTRY_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_when_async_setup_entry_at_module_level(self, tmp_path: Path) -> None:
        """PASS: __init__.py defines async_setup_entry at module level."""
        src = """\
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry.runtime_data = MyCoordinator(hass, entry)
    return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, ASYNC_SETUP_ENTRY_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_when_async_setup_entry_inside_class(self, tmp_path: Path) -> None:
        """PASS: ast.walk finds async_setup_entry at any depth."""
        src = """\
class FakeModule:
    async def async_setup_entry(self, hass, entry):
        return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, ASYNC_SETUP_ENTRY_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_pattern_absent(self, tmp_path: Path) -> None:
        """WARN: __init__.py exists but no async_setup_entry."""
        src = """\
DOMAIN = "test_integration"

def setup(hass, config):
    return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, ASYNC_SETUP_ENTRY_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: no integration_path detected."""
        f = _finding_for(tmp_path, ASYNC_SETUP_ENTRY_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_init_file(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: integration exists but no __init__.py."""
        _write_integration(tmp_path)  # no init_src
        f = _finding_for(tmp_path, ASYNC_SETUP_ENTRY_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        """WARN: parse error in __init__.py."""
        src = """\
def broken(
    # unclosed paren
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, ASYNC_SETUP_ENTRY_RULE)
        assert f.status is RuleStatus.WARN
        assert "could not be parsed" in f.message

    def test_sync_setup_entry_does_not_pass(self, tmp_path: Path) -> None:
        """WARN: sync def setup_entry does not qualify — must be AsyncFunctionDef."""
        src = """\
def async_setup_entry(hass, entry):
    return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, ASYNC_SETUP_ENTRY_RULE)
        assert f.status is RuleStatus.WARN


# ===========================================================================
# init.runtime_data.used
# ===========================================================================

RUNTIME_DATA_RULE = "init.runtime_data.used"


class TestRuntimeDataUsed:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[RUNTIME_DATA_RULE]
        assert rule.id == RUNTIME_DATA_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_when_entry_runtime_data_assigned(self, tmp_path: Path) -> None:
        """PASS: entry.runtime_data = ... assignment detected."""
        src = """\
async def async_setup_entry(hass, entry):
    entry.runtime_data = MyCoordinator(hass, entry)
    return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_when_config_entry_runtime_data_read(self, tmp_path: Path) -> None:
        """PASS: config_entry.runtime_data access detected."""
        src = """\
async def async_unload_entry(hass, config_entry):
    coordinator = config_entry.runtime_data
    return await coordinator.async_unload()
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_when_underscore_entry_used(self, tmp_path: Path) -> None:
        """PASS: _entry.runtime_data access detected."""
        src = """\
async def async_setup_entry(hass, _entry):
    data = _entry.runtime_data
    return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_pattern_absent(self, tmp_path: Path) -> None:
        """WARN: __init__.py exists but no runtime_data usage."""
        src = """\
async def async_setup_entry(hass, entry):
    hass.data.setdefault("test", {})
    hass.data["test"][entry.entry_id] = MyClass(hass, entry)
    return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: no integration_path detected."""
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_init_file(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: integration exists but no __init__.py."""
        _write_integration(tmp_path)  # no init_src
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        """WARN: parse error in __init__.py."""
        src = """\
def broken(
    # unclosed paren
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.WARN
        assert "could not be parsed" in f.message

    def test_other_runtime_data_attribute_does_not_pass(self, tmp_path: Path) -> None:
        """WARN: other.runtime_data (not entry/config_entry/_entry) does not qualify."""
        src = """\
async def async_setup_entry(hass, entry):
    value = hass.runtime_data
    return True
"""
        _write_integration(tmp_path, init_src=src)
        f = _finding_for(tmp_path, RUNTIME_DATA_RULE)
        assert f.status is RuleStatus.WARN
