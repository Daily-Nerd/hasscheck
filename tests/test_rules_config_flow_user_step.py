"""Tests for config_flow.user_step.exists rule (PR3, #54).

TDD cycle:
  - RED: written first, references production code that does not yet exist
  - GREEN: confirmed after implementation

Spec: sdd/v0-8-rule-depth/spec — Domain: config-flow-rules (#54)
Design: D1 (AST helpers), D7 (exact message strings)
"""

from __future__ import annotations

from pathlib import Path

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RULE_ID = "config_flow.user_step.exists"


def _write_integration(
    root: Path,
    *,
    dir_name: str = "test_integration",
    manifest: str | None = None,
    config_flow_src: str | None = None,
) -> Path:
    """Create custom_components/<dir_name>/ with optional manifest and config_flow.py."""
    integration = root / "custom_components" / dir_name
    integration.mkdir(parents=True)

    # Write a minimal manifest so other rules don't interfere
    mf = manifest or (
        '{"domain": "'
        + dir_name
        + '", "name": "Test", "documentation": "https://example.com",'
        ' "issue_tracker": "https://example.com/issues", "codeowners": ["@test"],'
        ' "version": "0.1.0", "config_flow": true}'
    )
    (integration / "manifest.json").write_text(mf, encoding="utf-8")

    if config_flow_src is not None:
        (integration / "config_flow.py").write_text(config_flow_src, encoding="utf-8")

    return integration


def _finding_for(root: Path):
    return {f.rule_id: f for f in run_check(root).findings}[RULE_ID]


# ---------------------------------------------------------------------------
# Rule registration — explain reachability + metadata
# ---------------------------------------------------------------------------


def test_rule_is_registered() -> None:
    rule = RULES_BY_ID[RULE_ID]
    assert rule.id == RULE_ID
    assert rule.version == "1.0.0"
    assert rule.category == "modern_ha_patterns"
    assert str(rule.severity) == "recommended"
    assert rule.overridable is True
    assert rule.why, "why must be non-empty"


def test_why_mentions_ast_limitation() -> None:
    """Spec: AST Limitation Documented — why must mention inherited methods."""
    rule = RULES_BY_ID[RULE_ID]
    why_lower = rule.why.lower()
    assert (
        "inherit" in why_lower or "base class" in why_lower or "mixin" in why_lower
    ), "why must mention inherited/base-class limitation per spec"


# ---------------------------------------------------------------------------
# PASS: config_flow.py with class-method async_step_user
# ---------------------------------------------------------------------------


def test_pass_when_async_step_user_is_class_method(tmp_path: Path) -> None:
    """Typical pattern: async_step_user defined as a method inside a class."""
    src = """\
from homeassistant import config_entries

class DemoConfigFlow(config_entries.ConfigFlow, domain="test_integration"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        return self.async_show_form(step_id="user")
"""
    _write_integration(tmp_path, config_flow_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# PASS: async_step_user at module level (rare but allowed)
# ---------------------------------------------------------------------------


def test_pass_when_async_step_user_is_at_module_level(tmp_path: Path) -> None:
    """Edge case: async_step_user as a module-level function, not a method."""
    src = """\
async def async_step_user(user_input=None):
    pass
"""
    _write_integration(tmp_path, config_flow_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# WARN: config_flow.py exists but no async_step_user
# ---------------------------------------------------------------------------


def test_warn_when_async_step_user_absent(tmp_path: Path) -> None:
    """WARN when config_flow.py exists but async_step_user is not found."""
    src = """\
from homeassistant import config_entries

class DemoConfigFlow(config_entries.ConfigFlow, domain="test_integration"):
    VERSION = 1

    async def async_step_setup(self, user_input=None):
        return self.async_show_form(step_id="setup")
"""
    _write_integration(tmp_path, config_flow_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    assert "async_step_user" in f.message


# ---------------------------------------------------------------------------
# WARN: sync def step_user must NOT match (only AsyncFunctionDef counts)
# ---------------------------------------------------------------------------


def test_sync_def_does_not_match(tmp_path: Path) -> None:
    """Edge case: sync 'def async_step_user' should NOT count — only async def."""
    src = """\
class DemoConfigFlow:
    def async_step_user(self, user_input=None):
        pass
"""
    _write_integration(tmp_path, config_flow_src=src)
    f = _finding_for(tmp_path)
    # Sync def named async_step_user does NOT satisfy the rule
    assert f.status is RuleStatus.WARN


# ---------------------------------------------------------------------------
# NOT_APPLICABLE: no config_flow.py in integration directory
# ---------------------------------------------------------------------------


def test_not_applicable_when_no_config_flow_file(tmp_path: Path) -> None:
    """No config_flow.py → NOT_APPLICABLE."""
    _write_integration(tmp_path)  # no config_flow_src
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# NOT_APPLICABLE: no integration directory at all
# ---------------------------------------------------------------------------


def test_not_applicable_when_no_integration_directory(tmp_path: Path) -> None:
    """No custom_components/ → NOT_APPLICABLE."""
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# NOT_APPLICABLE: uses_config_flow=False in hasscheck.yaml applicability
# ---------------------------------------------------------------------------


def test_not_applicable_when_uses_config_flow_false(tmp_path: Path) -> None:
    """Applicability flag uses_config_flow=False → NOT_APPLICABLE even if file exists."""
    src = """\
async def async_step_user(user_input=None):
    pass
"""
    _write_integration(tmp_path, config_flow_src=src)

    # Write hasscheck.yaml that declares uses_config_flow: false
    (tmp_path / "hasscheck.yaml").write_text(
        "applicability:\n  uses_config_flow: false\n", encoding="utf-8"
    )

    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# WARN: syntax error in config_flow.py (parse fails → conservative WARN)
# ---------------------------------------------------------------------------


def test_warn_when_config_flow_has_syntax_error(tmp_path: Path) -> None:
    """Parse error → WARN with message containing 'could not be parsed'."""
    src = """\
def broken(
    # unclosed parenthesis — invalid Python
"""
    _write_integration(tmp_path, config_flow_src=src)
    f = _finding_for(tmp_path)
    assert f.status is RuleStatus.WARN
    assert "could not be parsed" in f.message
