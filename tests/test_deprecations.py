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


# ---------------------------------------------------------------------------
# Group 5: Rules 6–10
# ---------------------------------------------------------------------------


class TestRuntimeDataMissing:
    """Rule 6: config_entry.runtime_data.missing"""

    def test_fires_on_hass_data_domain_usage(self, tmp_path: Path) -> None:
        """Spec S6: fires on hass.data[DOMAIN] usage."""
        source = (
            "async def async_setup_entry(hass, entry):\n"
            "    hass.data[DOMAIN] = MyCoordinator(hass, entry)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"__init__.py": source})

        from hasscheck.rules.deprecations import check_runtime_data_missing

        finding = check_runtime_data_missing(ctx)
        assert finding.status == RuleStatus.WARN

    def test_fires_on_hass_data_get_usage(self, tmp_path: Path) -> None:
        """Fires on hass.data.get(DOMAIN) usage."""
        source = (
            "async def async_setup_entry(hass, entry):\n"
            "    coordinator = hass.data.get(DOMAIN)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"__init__.py": source})

        from hasscheck.rules.deprecations import check_runtime_data_missing

        finding = check_runtime_data_missing(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_runtime_data_used(self, tmp_path: Path) -> None:
        source = (
            "async def async_setup_entry(hass, entry):\n"
            "    entry.runtime_data = MyCoordinator(hass, entry)\n"
        )
        ctx = _make_context(tmp_path, integration_content={"__init__.py": source})

        from hasscheck.rules.deprecations import check_runtime_data_missing

        finding = check_runtime_data_missing(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_init_file(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)  # no __init__.py

        from hasscheck.rules.deprecations import check_runtime_data_missing

        finding = check_runtime_data_missing(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_path(self) -> None:
        ctx = _make_context_no_integration()

        from hasscheck.rules.deprecations import check_runtime_data_missing

        finding = check_runtime_data_missing(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestEntityUniqueIdMutableSource:
    """Rule 7: entity.unique_id.mutable_source"""

    def test_fires_when_unique_id_uses_name_attr(self, tmp_path: Path) -> None:
        source = (
            "class MySensor:\n"
            "    @property\n"
            "    def unique_id(self):\n"
            "        return self._name\n"
        )
        ctx = _make_context(tmp_path, integration_content={"sensor.py": source})

        from hasscheck.rules.deprecations import check_entity_unique_id_mutable

        finding = check_entity_unique_id_mutable(ctx)
        assert finding.status == RuleStatus.WARN

    def test_fires_when_unique_id_uses_ip_attr(self, tmp_path: Path) -> None:
        source = (
            "class MySensor:\n"
            "    @property\n"
            "    def unique_id(self):\n"
            "        return self._ip_address\n"
        )
        ctx = _make_context(tmp_path, integration_content={"sensor.py": source})

        from hasscheck.rules.deprecations import check_entity_unique_id_mutable

        finding = check_entity_unique_id_mutable(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_stable_attr_used(self, tmp_path: Path) -> None:
        source = (
            "class MySensor:\n"
            "    @property\n"
            "    def unique_id(self):\n"
            "        return self._serial_number\n"
        )
        ctx = _make_context(tmp_path, integration_content={"sensor.py": source})

        from hasscheck.rules.deprecations import check_entity_unique_id_mutable

        finding = check_entity_unique_id_mutable(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_entity_files(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)  # no entity files

        from hasscheck.rules.deprecations import check_entity_unique_id_mutable

        finding = check_entity_unique_id_mutable(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_path(self) -> None:
        ctx = _make_context_no_integration()

        from hasscheck.rules.deprecations import check_entity_unique_id_mutable

        finding = check_entity_unique_id_mutable(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestAsyncSetupEntryMissing:
    """Rule 8: setup.async_setup_entry.missing"""

    def test_fires_when_async_setup_present_but_entry_missing(
        self, tmp_path: Path
    ) -> None:
        """Spec S9: fires when async_setup present but async_setup_entry absent."""
        source = "async def async_setup(hass, config):\n    return True\n"
        ctx = _make_context(tmp_path, integration_content={"__init__.py": source})

        from hasscheck.rules.deprecations import check_async_setup_entry_missing

        finding = check_async_setup_entry_missing(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_async_setup_entry_present(self, tmp_path: Path) -> None:
        source = (
            "async def async_setup(hass, config):\n"
            "    return True\n"
            "\n"
            "async def async_setup_entry(hass, entry):\n"
            "    return True\n"
        )
        ctx = _make_context(tmp_path, integration_content={"__init__.py": source})

        from hasscheck.rules.deprecations import check_async_setup_entry_missing

        finding = check_async_setup_entry_missing(ctx)
        assert finding.status == RuleStatus.PASS

    def test_passes_when_neither_setup_function_exists(self, tmp_path: Path) -> None:
        source = "DOMAIN = 'my_integration'\n"
        ctx = _make_context(tmp_path, integration_content={"__init__.py": source})

        from hasscheck.rules.deprecations import check_async_setup_entry_missing

        finding = check_async_setup_entry_missing(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_init_file(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)

        from hasscheck.rules.deprecations import check_async_setup_entry_missing

        finding = check_async_setup_entry_missing(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestHelpersDeprecatedImport:
    """Rule 9: helpers.deprecated_import"""

    def test_fires_on_deprecated_helpers_entity_import(self, tmp_path: Path) -> None:
        """Spec S7: fires on deprecated HA helper import."""
        source = "from homeassistant.helpers.entity import Entity\n"
        ctx = _make_context(tmp_path, integration_content={"sensor.py": source})

        from hasscheck.rules.deprecations import check_helpers_deprecated_import

        finding = check_helpers_deprecated_import(ctx)
        assert finding.status == RuleStatus.WARN

    def test_fires_on_deprecated_entity_platform_import(self, tmp_path: Path) -> None:
        source = "from homeassistant.helpers.entity_platform import EntityPlatform\n"
        ctx = _make_context(tmp_path, integration_content={"sensor.py": source})

        from hasscheck.rules.deprecations import check_helpers_deprecated_import

        finding = check_helpers_deprecated_import(ctx)
        assert finding.status == RuleStatus.WARN

    def test_fires_on_deprecated_entity_registry_import(self, tmp_path: Path) -> None:
        source = "from homeassistant.helpers.entity_registry import async_get\n"
        ctx = _make_context(tmp_path, integration_content={"sensor.py": source})

        from hasscheck.rules.deprecations import check_helpers_deprecated_import

        finding = check_helpers_deprecated_import(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_modern_import_used(self, tmp_path: Path) -> None:
        source = "from homeassistant.components.sensor import SensorEntity\n"
        ctx = _make_context(tmp_path, integration_content={"sensor.py": source})

        from hasscheck.rules.deprecations import check_helpers_deprecated_import

        finding = check_helpers_deprecated_import(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_python_files(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)  # no .py files

        from hasscheck.rules.deprecations import check_helpers_deprecated_import

        finding = check_helpers_deprecated_import(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_path(self) -> None:
        ctx = _make_context_no_integration()

        from hasscheck.rules.deprecations import check_helpers_deprecated_import

        finding = check_helpers_deprecated_import(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


class TestManifestConfigFlowTrueButNoClass:
    """Rule 10: manifest.config_flow.true_but_no_class"""

    def test_fires_when_manifest_true_but_no_class(self, tmp_path: Path) -> None:
        """Spec S8: fires when manifest config_flow: true but no ConfigFlow class."""
        manifest = '{"domain": "my_integration", "name": "My Integration", "config_flow": true}'
        config_flow_source = "# no ConfigFlow class here\nDOMAIN = 'test'\n"
        ctx = _make_context(
            tmp_path,
            integration_content={
                "manifest.json": manifest,
                "config_flow.py": config_flow_source,
            },
        )

        from hasscheck.rules.deprecations import (
            check_manifest_config_flow_true_but_no_class,
        )

        finding = check_manifest_config_flow_true_but_no_class(ctx)
        assert finding.status == RuleStatus.WARN

    def test_passes_when_config_flow_class_exists(self, tmp_path: Path) -> None:
        manifest = '{"domain": "my_integration", "name": "My Integration", "config_flow": true}'
        config_flow_source = (
            "from homeassistant.config_entries import ConfigFlow as BaseConfigFlow\n"
            "class ConfigFlow(BaseConfigFlow):\n"
            "    async def async_step_user(self, user_input):\n"
            "        pass\n"
        )
        ctx = _make_context(
            tmp_path,
            integration_content={
                "manifest.json": manifest,
                "config_flow.py": config_flow_source,
            },
        )

        from hasscheck.rules.deprecations import (
            check_manifest_config_flow_true_but_no_class,
        )

        finding = check_manifest_config_flow_true_but_no_class(ctx)
        assert finding.status == RuleStatus.PASS

    def test_passes_when_manifest_config_flow_is_false(self, tmp_path: Path) -> None:
        manifest = '{"domain": "my_integration", "name": "My Integration", "config_flow": false}'
        ctx = _make_context(tmp_path, integration_content={"manifest.json": manifest})

        from hasscheck.rules.deprecations import (
            check_manifest_config_flow_true_but_no_class,
        )

        finding = check_manifest_config_flow_true_but_no_class(ctx)
        assert finding.status == RuleStatus.PASS

    def test_not_applicable_when_no_manifest(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)  # no manifest.json

        from hasscheck.rules.deprecations import (
            check_manifest_config_flow_true_but_no_class,
        )

        finding = check_manifest_config_flow_true_but_no_class(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_integration_path(self) -> None:
        ctx = _make_context_no_integration()

        from hasscheck.rules.deprecations import (
            check_manifest_config_flow_true_but_no_class,
        )

        finding = check_manifest_config_flow_true_but_no_class(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE
