"""Tests for deprecation rules (rules/deprecations.py)."""

from __future__ import annotations

from pathlib import Path

from hasscheck.models import RuleStatus
from hasscheck.rules.base import ProjectContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(
    tmp_path: Path, *, integration_content: dict[str, str] | None = None
) -> ProjectContext:
    """Build a ProjectContext with a synthetic integration under tmp_path."""
    integration_path = tmp_path / "custom_components" / "my_integration"
    integration_path.mkdir(parents=True)

    if integration_content:
        for filename, content in integration_content.items():
            (integration_path / filename).write_text(content, encoding="utf-8")

    return ProjectContext(
        root=tmp_path,
        integration_path=integration_path,
        domain="my_integration",
    )


def _make_context_no_integration() -> ProjectContext:
    """Build a ProjectContext with no integration path."""
    return ProjectContext(
        root=Path("/tmp/no-integration"),
        integration_path=None,
        domain=None,
    )


# ---------------------------------------------------------------------------
# Group 4: Rules 1–5 (config_flow.unique_id.*)
# ---------------------------------------------------------------------------


class TestUsesIpAddress:
    """Rule 1: config_flow.unique_id.uses_ip_address"""

    def test_fires_when_unique_id_uses_ip_variable(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        ip_address = user_input['host']\n"
            "        await self.async_set_unique_id(ip_address)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_uses_ip_address

        finding = check_uses_ip_address(ctx)
        assert finding.status == RuleStatus.WARN

    def test_fires_when_unique_id_uses_host_variable(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        host = user_input['host']\n"
            "        await self.async_set_unique_id(host)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_uses_ip_address

        finding = check_uses_ip_address(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_stable_id_used(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        mac = get_device_mac()\n"
            "        await self.async_set_unique_id(mac)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_uses_ip_address

        finding = check_uses_ip_address(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_integration_path(self) -> None:
        ctx = _make_context_no_integration()

        from hasscheck.rules.deprecations import check_uses_ip_address

        finding = check_uses_ip_address(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)  # no config_flow.py

        from hasscheck.rules.deprecations import check_uses_ip_address

        finding = check_uses_ip_address(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestUsesDeviceName:
    """Rule 2: config_flow.unique_id.uses_device_name"""

    def test_fires_when_unique_id_uses_name_variable(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        device_name = user_input['name']\n"
            "        await self.async_set_unique_id(device_name)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_uses_device_name

        finding = check_uses_device_name(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_stable_id_used(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        serial = device.serial_number\n"
            "        await self.async_set_unique_id(serial)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_uses_device_name

        finding = check_uses_device_name(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)

        from hasscheck.rules.deprecations import check_uses_device_name

        finding = check_uses_device_name(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestUsesUrl:
    """Rule 3: config_flow.unique_id.uses_url"""

    def test_fires_when_unique_id_uses_url_variable(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        url = user_input['url']\n"
            "        await self.async_set_unique_id(url)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_uses_url

        finding = check_uses_url(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_stable_id_used(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        serial = device.serial\n"
            "        await self.async_set_unique_id(serial)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_uses_url

        finding = check_uses_url(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)

        from hasscheck.rules.deprecations import check_uses_url

        finding = check_uses_url(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestMissingAbortIfConfigured:
    """Rule 4: config_flow.unique_id.missing_abort_if_configured"""

    def test_fires_when_set_unique_id_without_abort(self, tmp_path: Path) -> None:
        """Spec S4: fires when async_set_unique_id present but _abort_if_unique_id_configured absent."""
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        await self.async_set_unique_id(device_id)\n"
            "        return self.async_create_entry(title='ok', data={})\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_missing_abort_if_configured

        finding = check_missing_abort_if_configured(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_both_calls_present(self, tmp_path: Path) -> None:
        """Spec S5: passes when both set_unique_id and abort_if_configured present."""
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        await self.async_set_unique_id(device_id)\n"
            "        self._abort_if_unique_id_configured()\n"
            "        return self.async_create_entry(title='ok', data={})\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_missing_abort_if_configured

        finding = check_missing_abort_if_configured(ctx)
        assert finding.status == RuleStatus.PASS

    def test_passes_when_no_unique_id_at_all(self, tmp_path: Path) -> None:
        """No async_set_unique_id → rule is not applicable."""
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        return self.async_create_entry(title='ok', data={})\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_missing_abort_if_configured

        finding = check_missing_abort_if_configured(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)

        from hasscheck.rules.deprecations import check_missing_abort_if_configured

        finding = check_missing_abort_if_configured(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestNotNormalized:
    """Rule 5: config_flow.unique_id.not_normalized"""

    def test_fires_when_no_normalization(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        device_id = get_device_id()\n"
            "        await self.async_set_unique_id(device_id)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_not_normalized

        finding = check_not_normalized(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_lower_used(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        device_id = get_device_id().lower()\n"
            "        await self.async_set_unique_id(device_id)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_not_normalized

        finding = check_not_normalized(ctx)
        assert finding.status == RuleStatus.PASS

    def test_passes_when_strip_used(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        device_id = get_device_id().strip()\n"
            "        await self.async_set_unique_id(device_id)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_not_normalized

        finding = check_not_normalized(ctx)
        assert finding.status == RuleStatus.PASS

    def test_passes_when_no_unique_id_set(self, tmp_path: Path) -> None:
        source = (
            "class ConfigFlow:\n"
            "    async def async_step_user(self, user_input):\n"
            "        return self.async_create_entry(title='ok', data={})\n"
        )
        ctx = _make_context(tmp_path, integration_content={"config_flow.py": source})

        from hasscheck.rules.deprecations import check_not_normalized

        finding = check_not_normalized(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_config_flow_file(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)

        from hasscheck.rules.deprecations import check_not_normalized

        finding = check_not_normalized(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE
