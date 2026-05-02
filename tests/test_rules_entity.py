"""Tests for entity rules (issue #107, v0.10 third batch).

TDD cycle:
  - RED: written first, before production code exists
  - GREEN: confirmed after implementation

Rules covered:
  - entity.unique_id.set
  - entity.has_entity_name.set
  - entity.device_info.set

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
    platform_files: dict[str, str] | None = None,
) -> Path:
    """Create custom_components/<dir_name>/ with optional manifest and platform files.

    platform_files: dict mapping filename (e.g. 'sensor.py') to source content.
    """
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

    if platform_files:
        for fname, src in platform_files.items():
            (integration / fname).write_text(src, encoding="utf-8")

    return integration


def _finding_for(root: Path, rule_id: str):
    return {f.rule_id: f for f in run_check(root).findings}[rule_id]


# ===========================================================================
# entity.unique_id.set
# ===========================================================================

UNIQUE_ID_RULE = "entity.unique_id.set"

_UNIQUE_ID_CLASS_ATTR = """\
class MySensor:
    _attr_unique_id = "my-sensor-uid"
"""

_UNIQUE_ID_SELF_ATTR = """\
class MySensor:
    def __init__(self, entry):
        self._attr_unique_id = entry.entry_id
"""

_UNIQUE_ID_ABSENT = """\
class MySensor:
    def __init__(self, entry):
        self._attr_name = "My Sensor"
"""

_UNIQUE_ID_ANNOTATED = """\
class MySensor:
    _attr_unique_id: str = "annotated-uid"
"""


class TestEntityUniqueIdSet:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[UNIQUE_ID_RULE]
        assert rule.id == UNIQUE_ID_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_class_attribute(self, tmp_path: Path) -> None:
        """PASS: class-level _attr_unique_id = ... assignment."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _UNIQUE_ID_CLASS_ATTR}
        )
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_self_attr_in_init(self, tmp_path: Path) -> None:
        """PASS: self._attr_unique_id = ... in __init__."""
        _write_integration(tmp_path, platform_files={"sensor.py": _UNIQUE_ID_SELF_ATTR})
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_annotated_class_attribute(self, tmp_path: Path) -> None:
        """PASS: annotated class attribute _attr_unique_id: str = ..."""
        _write_integration(tmp_path, platform_files={"sensor.py": _UNIQUE_ID_ANNOTATED})
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_pattern_absent(self, tmp_path: Path) -> None:
        """WARN: platform file exists but _attr_unique_id not set."""
        _write_integration(tmp_path, platform_files={"sensor.py": _UNIQUE_ID_ABSENT})
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: no integration detected."""
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_platform_files(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: integration exists but no platform files."""
        _write_integration(tmp_path)  # no platform files
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        """WARN: platform file has syntax error."""
        bad_src = "def broken(\n    # unclosed\n"
        _write_integration(tmp_path, platform_files={"sensor.py": bad_src})
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.WARN

    def test_pass_any_platform_file_qualifies(self, tmp_path: Path) -> None:
        """PASS: one platform has the pattern, another does not — any-match."""
        _write_integration(
            tmp_path,
            platform_files={
                "sensor.py": _UNIQUE_ID_ABSENT,
                "light.py": _UNIQUE_ID_CLASS_ATTR,
            },
        )
        f = _finding_for(tmp_path, UNIQUE_ID_RULE)
        assert f.status is RuleStatus.PASS


# ===========================================================================
# entity.has_entity_name.set
# ===========================================================================

HAS_ENTITY_NAME_RULE = "entity.has_entity_name.set"

_HAS_ENTITY_NAME_TRUE = """\
class MySensor:
    _attr_has_entity_name = True
"""

_HAS_ENTITY_NAME_FALSE = """\
class MySensor:
    _attr_has_entity_name = False
"""

_HAS_ENTITY_NAME_SELF_TRUE = """\
class MySensor:
    def __init__(self):
        self._attr_has_entity_name = True
"""

_HAS_ENTITY_NAME_ABSENT = """\
class MySensor:
    _attr_name = "My Sensor"
"""


class TestEntityHasEntityNameSet:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[HAS_ENTITY_NAME_RULE]
        assert rule.id == HAS_ENTITY_NAME_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_class_level_true(self, tmp_path: Path) -> None:
        """PASS: _attr_has_entity_name = True at class level."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _HAS_ENTITY_NAME_TRUE}
        )
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_self_attr_true(self, tmp_path: Path) -> None:
        """PASS: self._attr_has_entity_name = True in __init__."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _HAS_ENTITY_NAME_SELF_TRUE}
        )
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_set_to_false(self, tmp_path: Path) -> None:
        """WARN: _attr_has_entity_name = False should NOT trigger PASS — only True counts."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _HAS_ENTITY_NAME_FALSE}
        )
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.WARN

    def test_warn_when_pattern_absent(self, tmp_path: Path) -> None:
        """WARN: platform file exists but _attr_has_entity_name not set."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _HAS_ENTITY_NAME_ABSENT}
        )
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: no integration detected."""
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_platform_files(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: integration exists but no platform files."""
        _write_integration(tmp_path)
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        """WARN: platform file has syntax error."""
        bad_src = "def broken(\n    # unclosed\n"
        _write_integration(tmp_path, platform_files={"sensor.py": bad_src})
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.WARN

    def test_pass_any_platform_file_qualifies(self, tmp_path: Path) -> None:
        """PASS: second file has True — any-match semantics."""
        _write_integration(
            tmp_path,
            platform_files={
                "sensor.py": _HAS_ENTITY_NAME_ABSENT,
                "light.py": _HAS_ENTITY_NAME_TRUE,
            },
        )
        f = _finding_for(tmp_path, HAS_ENTITY_NAME_RULE)
        assert f.status is RuleStatus.PASS


# ===========================================================================
# entity.device_info.set
# ===========================================================================

DEVICE_INFO_RULE = "entity.device_info.set"

_DEVICE_INFO_CLASS_ATTR = """\
from homeassistant.helpers.device_registry import DeviceInfo

class MySensor:
    _attr_device_info = DeviceInfo(identifiers={("test", "uid")})
"""

_DEVICE_INFO_SELF_ATTR = """\
from homeassistant.helpers.device_registry import DeviceInfo

class MySensor:
    def __init__(self, entry):
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="My Device",
        )
"""

_DEVICE_INFO_PROPERTY = """\
from homeassistant.helpers.device_registry import DeviceInfo

class MySensor:
    @property
    def device_info(self):
        return DeviceInfo(identifiers={("test", "uid")}, name="Test")
"""

_DEVICE_INFO_ASYNC_PROPERTY = """\
from homeassistant.helpers.device_registry import DeviceInfo

class MySensor:
    async def device_info(self):
        return DeviceInfo(identifiers={("test", "uid")})
"""

_DEVICE_INFO_MODULE_ATTR = """\
from homeassistant.helpers.entity import DeviceInfo

class MySensor:
    _attr_device_info: DeviceInfo
"""

_DEVICE_INFO_ABSENT = """\
class MySensor:
    _attr_name = "My Sensor"
    _attr_unique_id = "uid-1"
"""


class TestEntityDeviceInfoSet:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[DEVICE_INFO_RULE]
        assert rule.id == DEVICE_INFO_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "modern_ha_patterns"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_class_attr(self, tmp_path: Path) -> None:
        """PASS: class-level _attr_device_info = ..."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _DEVICE_INFO_CLASS_ATTR}
        )
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_self_attr_in_init(self, tmp_path: Path) -> None:
        """PASS: self._attr_device_info = ... in __init__."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _DEVICE_INFO_SELF_ATTR}
        )
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_device_info_property_returning_device_info(
        self, tmp_path: Path
    ) -> None:
        """PASS: device_info property returns DeviceInfo(...)."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _DEVICE_INFO_PROPERTY}
        )
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_async_device_info_method(self, tmp_path: Path) -> None:
        """PASS: async device_info method returning DeviceInfo(...)."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _DEVICE_INFO_ASYNC_PROPERTY}
        )
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.PASS

    def test_pass_annotated_class_attribute(self, tmp_path: Path) -> None:
        """PASS: annotated _attr_device_info (no value) counts as assignment."""
        _write_integration(
            tmp_path, platform_files={"sensor.py": _DEVICE_INFO_MODULE_ATTR}
        )
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.PASS

    def test_warn_when_pattern_absent(self, tmp_path: Path) -> None:
        """WARN: platform file exists but no device_info pattern."""
        _write_integration(tmp_path, platform_files={"sensor.py": _DEVICE_INFO_ABSENT})
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.WARN

    def test_not_applicable_when_no_integration_directory(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: no integration detected."""
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_when_no_platform_files(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE: integration exists but no platform files."""
        _write_integration(tmp_path)
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.NOT_APPLICABLE

    def test_warn_on_syntax_error(self, tmp_path: Path) -> None:
        """WARN: platform file has syntax error."""
        bad_src = "def broken(\n    # unclosed\n"
        _write_integration(tmp_path, platform_files={"sensor.py": bad_src})
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.WARN

    def test_pass_any_platform_file_qualifies(self, tmp_path: Path) -> None:
        """PASS: one file has device_info, other does not — any-match."""
        _write_integration(
            tmp_path,
            platform_files={
                "sensor.py": _DEVICE_INFO_ABSENT,
                "light.py": _DEVICE_INFO_SELF_ATTR,
            },
        )
        f = _finding_for(tmp_path, DEVICE_INFO_RULE)
        assert f.status is RuleStatus.PASS
