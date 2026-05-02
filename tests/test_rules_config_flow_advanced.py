"""Tests for config_flow advanced detection rules (issue #101, v0.10 second batch).

TDD cycle:
  - RED: written first, before production code exists
  - GREEN: confirmed after implementation

Rules covered:
  - config_flow.reauth_step.exists
  - config_flow.reconfigure_step.exists
  - config_flow.unique_id.set
  - config_flow.connection_test

Spec: issue #101 — config_flow advanced detection
Source: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
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
    config_flow_src: str | None = None,
) -> Path:
    """Create custom_components/<dir_name>/ with optional manifest and config_flow.py."""
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

    if config_flow_src is not None:
        (integration / "config_flow.py").write_text(config_flow_src, encoding="utf-8")

    return integration


def _finding_for(root: Path, rule_id: str):
    return {f.rule_id: f for f in run_check(root).findings}[rule_id]


# ===========================================================================
# config_flow.reauth_step.exists
# ===========================================================================

REAUTH_RULE = "config_flow.reauth_step.exists"


class TestReauthStepExists:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[REAUTH_RULE]
        assert rule.id == REAUTH_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_with_async_step_reauth(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_reauth(self, entry_data=None):
        return self.async_show_form(step_id="reauth")
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, REAUTH_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_with_async_step_reauth_confirm(self, tmp_path: Path) -> None:
        """Alternate name: async_step_reauth_confirm also qualifies."""
        src = """\
class MyFlow:
    async def async_step_reauth_confirm(self, user_input=None):
        return self.async_show_form(step_id="reauth_confirm")
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, REAUTH_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_pattern_absent(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        return self.async_show_form(step_id="user")
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, REAUTH_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        f = _finding_for(tmp_path, REAUTH_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        f = _finding_for(tmp_path, REAUTH_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_uses_config_flow_false(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_reauth(self, entry_data=None):
        return {}
"""
        _write_integration(tmp_path, config_flow_src=src)
        (tmp_path / "hasscheck.yaml").write_text(
            "applicability:\n  uses_config_flow: false\n", encoding="utf-8"
        )
        f = _finding_for(tmp_path, REAUTH_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        src = """\
def broken(
    # unclosed paren
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, REAUTH_RULE)
        assert f.status is RuleStatus.WARN
        assert "could not be parsed" in f.message


# ===========================================================================
# config_flow.reconfigure_step.exists
# ===========================================================================

RECONFIG_RULE = "config_flow.reconfigure_step.exists"


class TestReconfigureStepExists:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[RECONFIG_RULE]
        assert rule.id == RECONFIG_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_with_async_step_reconfigure(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_reconfigure(self, user_input=None):
        return self.async_show_form(step_id="reconfigure")
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, RECONFIG_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_pattern_absent(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        return self.async_show_form(step_id="user")
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, RECONFIG_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        f = _finding_for(tmp_path, RECONFIG_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        f = _finding_for(tmp_path, RECONFIG_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_uses_config_flow_false(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_reconfigure(self, user_input=None):
        return {}
"""
        _write_integration(tmp_path, config_flow_src=src)
        (tmp_path / "hasscheck.yaml").write_text(
            "applicability:\n  uses_config_flow: false\n", encoding="utf-8"
        )
        f = _finding_for(tmp_path, RECONFIG_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        src = """\
def broken(
    # unclosed paren
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, RECONFIG_RULE)
        assert f.status is RuleStatus.WARN
        assert "could not be parsed" in f.message


# ===========================================================================
# config_flow.unique_id.set
# ===========================================================================

UNIQUE_ID_RULE = "config_flow.unique_id.set"


class TestUniqueIdSet:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[UNIQUE_ID_RULE]
        assert rule.id == UNIQUE_ID_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_with_self_async_set_unique_id(self, tmp_path: Path) -> None:
        """Most common: self.async_set_unique_id(value)."""
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id("my-device-id")
        return self.async_create_entry(title="Test", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_with_await_self_async_set_unique_id(self, tmp_path: Path) -> None:
        """await self.async_set_unique_id(...) form."""
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(self.device.serial)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Test", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_with_bare_name_async_set_unique_id(self, tmp_path: Path) -> None:
        """Less common: bare call async_set_unique_id(value) without self."""
        src = """\
async def async_set_unique_id(value):
    pass

async def configure():
    async_set_unique_id("some-id")
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_no_unique_id_call(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        return self.async_create_entry(title="Test", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_uses_config_flow_false(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id("id")
        return self.async_create_entry(title="Test", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        (tmp_path / "hasscheck.yaml").write_text(
            "applicability:\n  uses_config_flow: false\n", encoding="utf-8"
        )
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        src = """\
def broken(
    # unclosed paren
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.WARN
        assert "could not be parsed" in f.message


# ===========================================================================
# config_flow.connection_test
# ===========================================================================

CONN_TEST_RULE = "config_flow.connection_test"


class TestConnectionTest:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[CONN_TEST_RULE]
        assert rule.id == CONN_TEST_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_when_async_step_user_awaits_validate_input(
        self, tmp_path: Path
    ) -> None:
        """PASS: async_step_user awaits validate_input(...) — non-flow call."""
        src = """\
async def validate_input(hass, data):
    client = MyClient(data["host"])
    await client.connect()
    return {"title": data["host"]}

class MyFlow:
    async def async_step_user(self, user_input=None):
        info = await validate_input(self.hass, user_input)
        return self.async_create_entry(title=info["title"], data=user_input)
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_when_zeroconf_step_awaits_external_call(self, tmp_path: Path) -> None:
        """PASS: async_step_zeroconf awaits external_call(...) alongside plumbing calls."""
        src = """\
class MyFlow:
    async def async_step_zeroconf(self, discovery_info=None):
        await self.async_set_unique_id(discovery_info.hostname)
        await external_call(discovery_info.host)
        return self.async_abort(reason="already_configured")
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_async_step_user_only_calls_show_form_and_create_entry(
        self, tmp_path: Path
    ) -> None:
        """WARN: only plumbing calls — no connection testing."""
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="Test", data=user_input)
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.WARN

    def test_warn_when_async_step_user_only_calls_unique_id_and_abort(
        self, tmp_path: Path
    ) -> None:
        """WARN: only unique_id + abort — no real connection work."""
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id("fixed-id")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="T", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.WARN

    def test_warn_when_no_discovery_flow_steps_present(self, tmp_path: Path) -> None:
        """WARN: no async_step_user/zeroconf/dhcp/bluetooth/usb — vacuously WARN."""
        src = """\
class MyFlow:
    async def async_step_setup(self, user_input=None):
        return {}
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.WARN

    def test_pass_when_dhcp_step_awaits_real_call(self, tmp_path: Path) -> None:
        """PASS: async_step_dhcp awaits check_device(...)."""
        src = """\
class MyFlow:
    async def async_step_dhcp(self, discovery_info=None):
        result = await check_device(discovery_info.ip)
        if not result:
            return self.async_abort(reason="not_supported")
        return self.async_create_entry(title="Device", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.PASS

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_uses_config_flow_false(self, tmp_path: Path) -> None:
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        await validate_input(self.hass, user_input)
        return self.async_create_entry(title="T", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        (tmp_path / "hasscheck.yaml").write_text(
            "applicability:\n  uses_config_flow: false\n", encoding="utf-8"
        )
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        src = """\
def broken(
    # unclosed paren
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.WARN
        assert "could not be parsed" in f.message

    def test_async_step_flow_step_calls_do_not_qualify(self, tmp_path: Path) -> None:
        """WARN: awaiting another async_step_* call is still plumbing, not connection work."""
        src = """\
class MyFlow:
    async def async_step_user(self, user_input=None):
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        return self.async_create_entry(title="T", data={})
"""
        _write_integration(tmp_path, config_flow_src=src)
        f = _finding_for(tmp_path, CONN_TEST_RULE)
        assert f.status is RuleStatus.WARN
