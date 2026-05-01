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
    apply_overrides,
    discover_config,
    load_config_file,
)
from hasscheck.models import Finding

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
    assert cfg.schema_version == "0.3.0"
    assert cfg.project is None
    assert cfg.applicability is None
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
    with pytest.raises(ValidationError):
        HassCheckConfig(
            unexpected={"value": False},  # type: ignore[call-arg]
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
        "rules:\n  repairs.file.exists:\n    status: pass\n    reason: some reason\n"
    )
    with pytest.raises(ConfigError):
        load_config_file(tmp_path / "hasscheck.yaml")


def test_load_config_file_missing_reason_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n  repairs.file.exists:\n    status: not_applicable\n"
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


# ---------- apply_overrides helpers ----------


def _make_finding(
    rule_id: str = "repairs.file.exists",
    status: str = "warn",
) -> Finding:
    from hasscheck.models import (
        Applicability,
        ApplicabilityStatus,
        RuleSeverity,
        RuleSource,
        RuleStatus,
    )

    app_status = {
        "warn": ApplicabilityStatus.APPLICABLE,
        "fail": ApplicabilityStatus.APPLICABLE,
        "pass": ApplicabilityStatus.APPLICABLE,
        "not_applicable": ApplicabilityStatus.NOT_APPLICABLE,
        "manual_review": ApplicabilityStatus.MANUAL_REVIEW,
    }[status]
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category="test_category",
        status=RuleStatus(status),
        severity=RuleSeverity.RECOMMENDED,
        title=f"{rule_id} title",
        message=f"{rule_id} message",
        applicability=Applicability(status=app_status, reason="test reason"),
        source=RuleSource(url="https://example.com"),
    )


def _config_with_rule(
    rule_id: str,
    override_status: str = "not_applicable",
    reason: str = "test reason",
) -> HassCheckConfig:
    return HassCheckConfig(
        rules={rule_id: RuleOverride(status=override_status, reason=reason)}
    )


# ---------- apply_overrides — Task 3.1: happy path ----------


def test_apply_overrides_warn_to_not_applicable() -> None:
    from hasscheck.models import RuleStatus

    finding = _make_finding("repairs.file.exists", "warn")
    config = _config_with_rule("repairs.file.exists", "not_applicable", "no repairs")
    new_findings, applied = apply_overrides([finding], config)
    assert new_findings[0].status is RuleStatus.NOT_APPLICABLE
    assert applied.count == 1
    assert "repairs.file.exists" in applied.rule_ids


def test_apply_overrides_warn_to_manual_review() -> None:
    from hasscheck.models import RuleStatus

    finding = _make_finding("repairs.file.exists", "warn")
    config = _config_with_rule("repairs.file.exists", "manual_review", "needs human")
    new_findings, applied = apply_overrides([finding], config)
    assert new_findings[0].status is RuleStatus.MANUAL_REVIEW
    assert applied.count == 1


def test_apply_overrides_overridden_source_is_config() -> None:
    finding = _make_finding("repairs.file.exists", "warn")
    config = _config_with_rule("repairs.file.exists", "not_applicable", "no repairs")
    new_findings, _ = apply_overrides([finding], config)
    assert new_findings[0].applicability.source == "config"


def test_apply_overrides_overridden_reason_from_config() -> None:
    finding = _make_finding("repairs.file.exists", "warn")
    config = _config_with_rule(
        "repairs.file.exists", "not_applicable", "my custom reason"
    )
    new_findings, _ = apply_overrides([finding], config)
    assert new_findings[0].applicability.reason == "my custom reason"


def test_apply_overrides_fail_to_not_applicable() -> None:
    from hasscheck.models import RuleStatus

    finding = _make_finding("repairs.file.exists", "fail")
    config = _config_with_rule("repairs.file.exists", "not_applicable", "no repairs")
    new_findings, applied = apply_overrides([finding], config)
    assert new_findings[0].status is RuleStatus.NOT_APPLICABLE
    assert applied.count == 1


def test_apply_overrides_empty_config_returns_unchanged(
    capsys: pytest.CaptureFixture,
) -> None:
    finding = _make_finding("repairs.file.exists", "warn")
    config = HassCheckConfig()
    new_findings, applied = apply_overrides([finding], config)
    assert new_findings[0].status == finding.status
    assert applied.count == 0
    assert capsys.readouterr().err == ""


# ---------- apply_overrides — Task 3.2: unknown rule_id ----------


def test_apply_overrides_unknown_rule_id_warns_stderr(
    capsys: pytest.CaptureFixture,
) -> None:
    finding = _make_finding("repairs.file.exists", "warn")
    config = _config_with_rule("nonexistent.rule.id", "not_applicable", "no such rule")
    apply_overrides([finding], config)
    err = capsys.readouterr().err
    assert "nonexistent.rule.id" in err
    assert "unknown" in err.lower()


def test_apply_overrides_unknown_rule_id_not_counted(
    capsys: pytest.CaptureFixture,
) -> None:
    finding = _make_finding("repairs.file.exists", "warn")
    config = _config_with_rule("nonexistent.rule.id", "not_applicable", "no such rule")
    _, applied = apply_overrides([finding], config)
    capsys.readouterr()
    assert applied.count == 0


# ---------- apply_overrides — Task 3.3: locked rule ----------


def test_apply_overrides_locked_rule_raises_config_error() -> None:
    finding = _make_finding("manifest.exists", "fail")
    config = _config_with_rule(
        "manifest.exists", "not_applicable", "we don't need this"
    )
    with pytest.raises(ConfigError) as exc_info:
        apply_overrides([finding], config)
    assert "manifest.exists" in str(exc_info.value)
    assert "not overridable" in str(exc_info.value).lower()


def test_apply_overrides_locked_rule_error_even_when_passing() -> None:
    """Locked rule precedence: hard fail even if natural status is PASS."""
    finding = _make_finding("manifest.exists", "pass")
    config = _config_with_rule(
        "manifest.exists", "not_applicable", "we don't need this"
    )
    with pytest.raises(ConfigError):
        apply_overrides([finding], config)


# ---------- apply_overrides — Task 3.4: PASS-skip ----------


def test_apply_overrides_natural_pass_not_applied(
    capsys: pytest.CaptureFixture,
) -> None:
    from hasscheck.models import RuleStatus

    finding = _make_finding("repairs.file.exists", "pass")
    config = _config_with_rule("repairs.file.exists", "not_applicable", "no repairs")
    new_findings, applied = apply_overrides([finding], config)
    capsys.readouterr()
    assert new_findings[0].status is RuleStatus.PASS
    assert applied.count == 0


def test_apply_overrides_natural_pass_emits_stale_warning(
    capsys: pytest.CaptureFixture,
) -> None:
    finding = _make_finding("repairs.file.exists", "pass")
    config = _config_with_rule("repairs.file.exists", "not_applicable", "no repairs")
    apply_overrides([finding], config)
    err = capsys.readouterr().err
    assert "repairs.file.exists" in err
    assert "stale" in err.lower()


# ---------- apply_overrides — Task 3.5: NA-noop ----------


def test_apply_overrides_natural_not_applicable_silent_noop(
    capsys: pytest.CaptureFixture,
) -> None:
    from hasscheck.models import RuleStatus

    finding = _make_finding("repairs.file.exists", "not_applicable")
    config = _config_with_rule("repairs.file.exists", "not_applicable", "no repairs")
    new_findings, applied = apply_overrides([finding], config)
    assert new_findings[0].status is RuleStatus.NOT_APPLICABLE
    assert applied.count == 0
    assert capsys.readouterr().err == ""


# ---------- apply_overrides — Task 3.6: MR-redundant-skip ----------


def test_apply_overrides_mr_override_mr_warns_redundant(
    capsys: pytest.CaptureFixture,
) -> None:
    finding = _make_finding("repairs.file.exists", "manual_review")
    config = _config_with_rule("repairs.file.exists", "manual_review", "needs human")
    _, applied = apply_overrides([finding], config)
    err = capsys.readouterr().err
    assert applied.count == 0
    assert "redundant" in err.lower() or "manual_review" in err.lower()


def test_apply_overrides_mr_to_na_is_applied() -> None:
    """MR + override=not_applicable → APPLY (not redundant, step 5 only blocks MR→MR)."""
    from hasscheck.models import RuleStatus

    finding = _make_finding("repairs.file.exists", "manual_review")
    config = _config_with_rule("repairs.file.exists", "not_applicable", "superseded")
    new_findings, applied = apply_overrides([finding], config)
    assert new_findings[0].status is RuleStatus.NOT_APPLICABLE
    assert applied.count == 1


# ---------- apply_overrides — multiple rules / alphabetical ----------


def test_apply_overrides_rule_ids_alphabetical() -> None:
    findings = [
        _make_finding("repairs.file.exists", "warn"),
        _make_finding("tests.folder.exists", "warn"),
        _make_finding("brand.icon.exists", "warn"),
    ]
    config = HassCheckConfig(
        rules={
            "repairs.file.exists": RuleOverride(status="not_applicable", reason="r1"),
            "tests.folder.exists": RuleOverride(status="not_applicable", reason="r2"),
            "brand.icon.exists": RuleOverride(status="not_applicable", reason="r3"),
        }
    )
    _, applied = apply_overrides(findings, config)
    assert applied.rule_ids == sorted(applied.rule_ids)
    assert applied.count == 3


# ---------- v0.3 ProjectApplicability ----------


def test_project_applicability_accepts_initial_v03_flags() -> None:
    from hasscheck.config import ProjectApplicability

    app = ProjectApplicability(
        supports_diagnostics=False,
        has_user_fixable_repairs=False,
        uses_config_flow=False,
    )

    assert app.supports_diagnostics is False
    assert app.has_user_fixable_repairs is False
    assert app.uses_config_flow is False


def test_project_applicability_rejects_unknown_flags() -> None:
    from hasscheck.config import ProjectApplicability

    with pytest.raises(ValidationError):
        ProjectApplicability(auth_required=False)  # type: ignore[call-arg]


def test_hasscheck_config_accepts_applicability_block() -> None:
    from hasscheck.config import ProjectApplicability

    cfg = HassCheckConfig(
        applicability=ProjectApplicability(supports_diagnostics=False)
    )

    assert cfg.schema_version == "0.3.0"
    assert cfg.applicability is not None
    assert cfg.applicability.supports_diagnostics is False


def test_hasscheck_config_accepts_v02_schema_when_no_applicability_block() -> None:
    cfg = HassCheckConfig(schema_version="0.2.0")

    assert cfg.schema_version == "0.2.0"
    assert cfg.rules == {}


def test_hasscheck_config_rejects_v02_schema_with_applicability_block() -> None:
    from hasscheck.config import ProjectApplicability

    with pytest.raises(ValidationError):
        HassCheckConfig(
            schema_version="0.2.0",
            applicability=ProjectApplicability(supports_diagnostics=False),
        )


def test_load_config_file_with_v03_applicability(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\n"
        "applicability:\n"
        "  supports_diagnostics: false\n"
        "  has_user_fixable_repairs: false\n"
        "  uses_config_flow: false\n"
    )

    cfg = load_config_file(tmp_path / "hasscheck.yaml")

    assert cfg.schema_version == "0.3.0"
    assert cfg.applicability is not None
    assert cfg.applicability.supports_diagnostics is False


# ---------- PublishConfig ----------


def test_publish_config_defaults_endpoint_none() -> None:
    from hasscheck.config import PublishConfig

    pc = PublishConfig()
    assert pc.endpoint is None


def test_publish_config_accepts_valid_endpoint() -> None:
    from hasscheck.config import PublishConfig

    pc = PublishConfig(endpoint="https://custom.example")
    assert pc.endpoint == "https://custom.example"


def test_publish_config_rejects_unknown_key() -> None:
    from hasscheck.config import PublishConfig

    with pytest.raises(ValidationError):
        PublishConfig(unknown_key="foo")  # type: ignore[call-arg]


def test_hasscheck_config_publish_defaults_to_none() -> None:
    cfg = HassCheckConfig()
    assert cfg.publish is None


def test_hasscheck_config_accepts_publish_block() -> None:
    from hasscheck.config import PublishConfig

    cfg = HassCheckConfig(publish=PublishConfig(endpoint="https://custom.example"))
    assert cfg.publish is not None
    assert cfg.publish.endpoint == "https://custom.example"


def test_load_config_file_missing_publish_block_returns_none(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("schema_version: '0.3.0'\n")
    cfg = load_config_file(tmp_path / "hasscheck.yaml")
    assert cfg.publish is None


def test_load_config_file_publish_block_with_endpoint(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\npublish:\n  endpoint: 'https://custom.example'\n"
    )
    cfg = load_config_file(tmp_path / "hasscheck.yaml")
    assert cfg.publish is not None
    assert cfg.publish.endpoint == "https://custom.example"


def test_load_config_file_publish_block_null_endpoint(tmp_path: Path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\npublish:\n  endpoint: null\n"
    )
    cfg = load_config_file(tmp_path / "hasscheck.yaml")
    assert cfg.publish is not None
    assert cfg.publish.endpoint is None


def test_load_config_file_publish_unknown_key_raises_config_error(
    tmp_path: Path,
) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\npublish:\n  unknown_key: foo\n"
    )
    with pytest.raises(ConfigError):
        load_config_file(tmp_path / "hasscheck.yaml")


def test_load_config_file_v03_backward_compat_no_publish(tmp_path: Path) -> None:
    """Existing 0.3.0 configs without a publish block stay valid."""
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\n"
        "rules:\n"
        "  repairs.file.exists:\n"
        "    status: not_applicable\n"
        "    reason: no repairs\n"
    )
    cfg = load_config_file(tmp_path / "hasscheck.yaml")
    assert cfg.schema_version == "0.3.0"
    assert cfg.publish is None
