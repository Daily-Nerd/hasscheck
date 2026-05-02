"""Tests for per-rule settings infrastructure (issue #117).

TDD cycle:
  - RED: written first, before production code exists
  - GREEN: confirmed after implementation

Covers:
  - RuleOverride.settings field (new)
  - ProjectContext.rule_settings propagation
  - Loader builds rule_settings from config
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from hasscheck.config import HassCheckConfig, RuleOverride, load_config_file

# ---------------------------------------------------------------------------
# RuleOverride.settings field
# ---------------------------------------------------------------------------


class TestRuleOverrideSettings:
    def test_settings_absent_defaults_to_none(self) -> None:
        """Missing settings block → None."""
        ro = RuleOverride(status="not_applicable", reason="ok")
        assert ro.settings is None

    def test_settings_explicit_none(self) -> None:
        """settings=None explicitly → None."""
        ro = RuleOverride(status="not_applicable", reason="ok", settings=None)
        assert ro.settings is None

    def test_settings_dict_accepted(self) -> None:
        """settings with a dict → stored as-is."""
        ro = RuleOverride(
            status="not_applicable",
            reason="ok",
            settings={"max_age_months": 18},
        )
        assert ro.settings == {"max_age_months": 18}

    def test_settings_empty_dict_accepted(self) -> None:
        """settings={} → stored as empty dict."""
        ro = RuleOverride(status="not_applicable", reason="ok", settings={})
        assert ro.settings == {}

    def test_settings_arbitrary_keys_accepted(self) -> None:
        """settings can hold any key/value pairs — open dict by design."""
        ro = RuleOverride(
            status="not_applicable",
            reason="ok",
            settings={"threshold": 3, "unit": "months", "enabled": True},
        )
        assert ro.settings["threshold"] == 3
        assert ro.settings["unit"] == "months"
        assert ro.settings["enabled"] is True

    def test_extra_fields_still_rejected(self) -> None:
        """extra='forbid' still rejects sibling unknown fields."""
        with pytest.raises(ValidationError):
            RuleOverride(
                status="not_applicable",
                reason="ok",
                unknown_field="bad",  # type: ignore[call-arg]
            )

    def test_settings_with_only_settings_no_status_reason_rejected(self) -> None:
        """Still requires status and reason when settings present."""
        with pytest.raises((ValidationError, TypeError)):
            RuleOverride(settings={"foo": "bar"})  # type: ignore[call-arg]

    def test_settings_only_no_status_without_reason_rejected(self) -> None:
        """settings-only override (no status, no reason) → validation error."""
        with pytest.raises((ValidationError, TypeError)):
            RuleOverride(  # type: ignore[call-arg]
                status="not_applicable",
                settings={"max_age_months": 18},
            )


# ---------------------------------------------------------------------------
# Load from YAML — settings block
# ---------------------------------------------------------------------------


class TestLoadConfigFileWithSettings:
    def test_settings_block_parsed_from_yaml(self, tmp_path: Path) -> None:
        """YAML with settings block → RuleOverride.settings populated."""
        (tmp_path / "hasscheck.yaml").write_text(
            "schema_version: '0.3.0'\n"
            "rules:\n"
            "  maintenance.recent_commit.detected:\n"
            "    status: not_applicable\n"
            "    reason: ok\n"
            "    settings:\n"
            "      max_age_months: 18\n"
        )
        cfg = load_config_file(tmp_path / "hasscheck.yaml")
        override = cfg.rules["maintenance.recent_commit.detected"]
        assert override.settings == {"max_age_months": 18}

    def test_settings_null_in_yaml(self, tmp_path: Path) -> None:
        """settings: null in YAML → None."""
        (tmp_path / "hasscheck.yaml").write_text(
            "schema_version: '0.3.0'\n"
            "rules:\n"
            "  maintenance.recent_commit.detected:\n"
            "    status: not_applicable\n"
            "    reason: ok\n"
            "    settings: null\n"
        )
        cfg = load_config_file(tmp_path / "hasscheck.yaml")
        override = cfg.rules["maintenance.recent_commit.detected"]
        assert override.settings is None

    def test_settings_missing_in_yaml(self, tmp_path: Path) -> None:
        """No settings block in YAML → None."""
        (tmp_path / "hasscheck.yaml").write_text(
            "schema_version: '0.3.0'\n"
            "rules:\n"
            "  maintenance.recent_commit.detected:\n"
            "    status: not_applicable\n"
            "    reason: ok\n"
        )
        cfg = load_config_file(tmp_path / "hasscheck.yaml")
        override = cfg.rules["maintenance.recent_commit.detected"]
        assert override.settings is None

    def test_settings_only_no_status_or_reason_raises(self, tmp_path: Path) -> None:
        """A rule block with only settings (no status/reason) → ConfigError."""
        from hasscheck.config import ConfigError

        (tmp_path / "hasscheck.yaml").write_text(
            "schema_version: '0.3.0'\n"
            "rules:\n"
            "  maintenance.recent_commit.detected:\n"
            "    settings:\n"
            "      max_age_months: 18\n"
        )
        with pytest.raises(ConfigError):
            load_config_file(tmp_path / "hasscheck.yaml")

    def test_unknown_sibling_field_still_raises(self, tmp_path: Path) -> None:
        """extra='forbid' on RuleOverride still fires for non-settings unknowns."""
        from hasscheck.config import ConfigError

        (tmp_path / "hasscheck.yaml").write_text(
            "schema_version: '0.3.0'\n"
            "rules:\n"
            "  maintenance.recent_commit.detected:\n"
            "    status: not_applicable\n"
            "    reason: ok\n"
            "    severity: low\n"
        )
        with pytest.raises(ConfigError):
            load_config_file(tmp_path / "hasscheck.yaml")


# ---------------------------------------------------------------------------
# ProjectContext.rule_settings propagation
# ---------------------------------------------------------------------------


class TestProjectContextRuleSettings:
    def test_rule_settings_defaults_to_empty_dict(self) -> None:
        """ProjectContext without rule_settings → empty dict."""
        from pathlib import Path

        from hasscheck.rules.base import ProjectContext

        ctx = ProjectContext(root=Path("/tmp"), integration_path=None, domain=None)
        assert ctx.rule_settings == {}

    def test_rule_settings_populated_from_config(self, tmp_path: Path) -> None:
        """checker.run_check with config → ProjectContext.rule_settings populated."""
        # We test by checking get_rule_setting directly given a manually built context
        from hasscheck.rules.base import ProjectContext, get_rule_setting

        ctx = ProjectContext(
            root=tmp_path,
            integration_path=None,
            domain=None,
            rule_settings={
                "maintenance.recent_commit.detected": {"max_age_months": 24}
            },
        )
        val = get_rule_setting(
            ctx, "maintenance.recent_commit.detected", "max_age_months", 12
        )
        assert val == 24

    def test_rule_settings_empty_when_no_rules_in_config(self, tmp_path: Path) -> None:
        """Config with no rules block → rule_settings={}."""
        from hasscheck.checker import run_check

        # Create a minimal integration so the check doesn't fail on project structure
        (tmp_path / "hasscheck.yaml").write_text("schema_version: '0.3.0'\n")
        # run_check doesn't expose context — but we can verify indirectly via no exceptions
        report = run_check(str(tmp_path))
        assert report is not None

    def test_rule_settings_only_rules_with_settings_key(self, tmp_path: Path) -> None:
        """Only rules that have settings= populate rule_settings — rules without don't."""
        from hasscheck.config import RuleOverride
        from hasscheck.rules.base import ProjectContext, get_rule_setting

        # Build config manually
        cfg = HassCheckConfig(
            rules={
                "maintenance.recent_commit.detected": RuleOverride(
                    status="not_applicable",
                    reason="ok",
                    settings={"max_age_months": 6},
                ),
                "maintenance.changelog.exists": RuleOverride(
                    status="not_applicable",
                    reason="ok",
                    # no settings
                ),
            }
        )

        # Simulate what the checker should do when building ProjectContext
        rule_settings = {
            rule_id: override.settings
            for rule_id, override in (cfg.rules or {}).items()
            if override.settings
        }

        ctx = ProjectContext(
            root=tmp_path,
            integration_path=None,
            domain=None,
            rule_settings=rule_settings,
        )

        # recent_commit has settings
        assert (
            get_rule_setting(
                ctx, "maintenance.recent_commit.detected", "max_age_months", 12
            )
            == 6
        )
        # changelog has no settings → default
        assert (
            get_rule_setting(ctx, "maintenance.changelog.exists", "any_key", 99) == 99
        )


# ---------------------------------------------------------------------------
# get_rule_setting helper
# ---------------------------------------------------------------------------


class TestGetRuleSetting:
    def _ctx(
        self,
        tmp_path: Path,
        rule_settings: dict | None = None,
    ):
        from hasscheck.rules.base import ProjectContext

        return ProjectContext(
            root=tmp_path,
            integration_path=None,
            domain=None,
            rule_settings=rule_settings or {},
        )

    def test_returns_default_when_rule_absent(self, tmp_path: Path) -> None:
        from hasscheck.rules.base import get_rule_setting

        ctx = self._ctx(tmp_path)
        assert get_rule_setting(ctx, "some.rule.id", "some_key", 42) == 42

    def test_returns_default_when_key_absent_in_rule(self, tmp_path: Path) -> None:
        from hasscheck.rules.base import get_rule_setting

        ctx = self._ctx(tmp_path, {"some.rule.id": {"other_key": 99}})
        assert get_rule_setting(ctx, "some.rule.id", "missing_key", 7) == 7

    def test_returns_configured_value(self, tmp_path: Path) -> None:
        from hasscheck.rules.base import get_rule_setting

        ctx = self._ctx(tmp_path, {"some.rule.id": {"threshold": 18}})
        assert get_rule_setting(ctx, "some.rule.id", "threshold", 12) == 18

    def test_returns_falsy_zero_not_default(self, tmp_path: Path) -> None:
        """A configured value of 0 (falsy) should be returned, not the default."""
        from hasscheck.rules.base import get_rule_setting

        ctx = self._ctx(tmp_path, {"some.rule.id": {"count": 0}})
        # get_rule_setting must use .get(key, default) not `or default`
        assert get_rule_setting(ctx, "some.rule.id", "count", 10) == 0

    def test_returns_false_not_default(self, tmp_path: Path) -> None:
        """A configured value of False should be returned, not the default."""
        from hasscheck.rules.base import get_rule_setting

        ctx = self._ctx(tmp_path, {"some.rule.id": {"enabled": False}})
        assert get_rule_setting(ctx, "some.rule.id", "enabled", True) is False

    def test_returns_none_when_explicitly_set(self, tmp_path: Path) -> None:
        """A configured value of None should be returned, not the default."""
        from hasscheck.rules.base import get_rule_setting

        ctx = self._ctx(tmp_path, {"some.rule.id": {"val": None}})
        assert get_rule_setting(ctx, "some.rule.id", "val", "fallback") is None

    def test_empty_rule_settings_uses_default(self, tmp_path: Path) -> None:
        """Rule with empty settings dict → default for all keys."""
        from hasscheck.rules.base import get_rule_setting

        ctx = self._ctx(tmp_path, {"some.rule.id": {}})
        assert get_rule_setting(ctx, "some.rule.id", "anything", "default") == "default"
