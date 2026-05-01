"""Tests for hasscheck.config — YAML schema models and override engine."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from hasscheck.config import (
    ConfigError,
    HassCheckConfig,
    ProjectConfig,
    RuleOverride,
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
