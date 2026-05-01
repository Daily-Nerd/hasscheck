"""Tests for hasscheck.config — YAML schema models and override engine."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from hasscheck.config import (
    ConfigError,
    HassCheckConfig,
    ProjectConfig,
    RuleOverride,
    discover_config,
    load_config_file,
)


# ---------- RuleOverride ----------

def test_rule_override_valid_not_applicable() -> None:
    ro = RuleOverride(status="not_applicable", reason="legitimately does not apply")
    assert ro.status == "not_applicable"
    assert ro.reason == "legitimately does not apply"


def test_rule_override_valid_manual_review() -> None:
    ro = RuleOverride(status="manual_review", reason="needs human judgment")
    assert ro.status == "manual_review"


def test_rule_override_rejects_status_pass() -> None:
    with pytest.raises(ValidationError):
        RuleOverride(status="pass", reason="some reason")


def test_rule_override_rejects_status_warn() -> None:
    with pytest.raises(ValidationError):
        RuleOverride(status="warn", reason="some reason")


def test_rule_override_rejects_status_fail() -> None:
    with pytest.raises(ValidationError):
        RuleOverride(status="fail", reason="some reason")


def test_rule_override_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        RuleOverride(status="informational", reason="some reason")


def test_rule_override_requires_reason() -> None:
    with pytest.raises(ValidationError):
        RuleOverride(status="not_applicable")  # type: ignore[call-arg]


def test_rule_override_rejects_empty_reason() -> None:
    with pytest.raises(ValidationError):
        RuleOverride(status="not_applicable", reason="")


def test_rule_override_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RuleOverride(
            status="not_applicable",
            reason="ok",
            severity="low",  # type: ignore[call-arg]
        )


# ---------- ProjectConfig ----------

def test_project_config_defaults_to_integration() -> None:
    pc = ProjectConfig()
    assert pc.type == "integration"


def test_project_config_rejects_other_types() -> None:
    with pytest.raises(ValidationError):
        ProjectConfig(type="other")  # type: ignore[arg-type]


def test_project_config_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProjectConfig(name="my-project")  # type: ignore[call-arg]


# ---------- HassCheckConfig ----------

def test_hasscheck_config_empty_defaults() -> None:
    cfg = HassCheckConfig()
    assert cfg.schema_version == "0.2.0"
    assert cfg.project is None
    assert cfg.rules == {}


def test_hasscheck_config_with_rules() -> None:
    cfg = HassCheckConfig(
        rules={
            "repairs.file.exists": RuleOverride(
                status="not_applicable", reason="no repair scenarios"
            ),
        }
    )
    assert "repairs.file.exists" in cfg.rules
    assert cfg.rules["repairs.file.exists"].status == "not_applicable"


def test_hasscheck_config_with_project_block() -> None:
    cfg = HassCheckConfig(project=ProjectConfig())
    assert cfg.project is not None
    assert cfg.project.type == "integration"


def test_hasscheck_config_rejects_unknown_top_level_key() -> None:
    """Block A's `applicability:` block is deferred to v0.3 — extra=forbid rejects it."""
    with pytest.raises(ValidationError):
        HassCheckConfig(
            applicability={"auth_required": False},  # type: ignore[call-arg]
        )


def test_hasscheck_config_rejects_wrong_schema_version() -> None:
    with pytest.raises(ValidationError):
        HassCheckConfig(schema_version="0.1.0")  # type: ignore[arg-type]


# ---------- ConfigError ----------

def test_config_error_is_exception() -> None:
    assert issubclass(ConfigError, Exception)


def test_config_error_carries_message() -> None:
    err = ConfigError("rule 'foo' is not overridable")
    assert "foo" in str(err)


# ---------- load_config_file ----------

def test_load_config_file_minimal_valid(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("schema_version: '0.2.0'\n")
    cfg = load_config_file(tmp_path / "hasscheck.yaml")
    assert cfg.schema_version == "0.2.0"
    assert cfg.rules == {}


def test_load_config_file_empty_file_returns_defaults(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("")
    cfg = load_config_file(tmp_path / "hasscheck.yaml")
    assert isinstance(cfg, HassCheckConfig)
    assert cfg.rules == {}


def test_load_config_file_with_rule_override(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.2.0'\n"
        "rules:\n"
        "  repairs.file.exists:\n"
        "    status: not_applicable\n"
        "    reason: no repair scenarios\n"
    )
    cfg = load_config_file(tmp_path / "hasscheck.yaml")
    assert "repairs.file.exists" in cfg.rules
    assert cfg.rules["repairs.file.exists"].status == "not_applicable"


def test_load_config_file_malformed_yaml_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("rules: [unclosed\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config_file(tmp_path / "hasscheck.yaml")
    assert "YAML" in str(exc_info.value) or "parse" in str(exc_info.value).lower()


def test_load_config_file_non_mapping_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("- item1\n- item2\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config_file(tmp_path / "hasscheck.yaml")
    assert "mapping" in str(exc_info.value).lower()


def test_load_config_file_forbidden_status_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  repairs.file.exists:\n"
        "    status: pass\n"
        "    reason: some reason\n"
    )
    with pytest.raises(ConfigError):
        load_config_file(tmp_path / "hasscheck.yaml")


def test_load_config_file_missing_reason_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  repairs.file.exists:\n"
        "    status: not_applicable\n"
    )
    with pytest.raises(ConfigError):
        load_config_file(tmp_path / "hasscheck.yaml")


def test_load_config_file_extra_fields_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  repairs.file.exists:\n"
        "    status: not_applicable\n"
        "    reason: ok\n"
        "    severity: low\n"
    )
    with pytest.raises(ConfigError):
        load_config_file(tmp_path / "hasscheck.yaml")


# ---------- discover_config ----------

def test_discover_config_returns_none_when_file_absent(tmp_path: Path) -> None:
    assert discover_config(tmp_path) is None


def test_discover_config_returns_config_when_file_present(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("schema_version: '0.2.0'\n")
    cfg = discover_config(tmp_path)
    assert isinstance(cfg, HassCheckConfig)
    assert cfg.schema_version == "0.2.0"


def test_discover_config_propagates_config_error_on_malformed(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("rules: [unclosed\n")
    with pytest.raises(ConfigError):
        discover_config(tmp_path)


def test_discover_config_looks_only_at_repo_root_not_parents(tmp_path: Path) -> None:
    subdir = tmp_path / "integration"
    subdir.mkdir()
    (tmp_path / "hasscheck.yaml").write_text("schema_version: '0.2.0'\n")
    assert discover_config(subdir) is None
