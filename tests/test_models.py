import pytest
from pydantic import ValidationError

from hasscheck.models import (
    Applicability,
    HassCheckReport,
    OverridesApplied,
    ReportSummary,
    RuleStatus,
)


def test_rule_status_includes_applicability_states() -> None:
    assert RuleStatus.PASS == "pass"
    assert RuleStatus.WARN == "warn"
    assert RuleStatus.FAIL == "fail"
    assert RuleStatus.NOT_APPLICABLE == "not_applicable"
    assert RuleStatus.MANUAL_REVIEW == "manual_review"


def test_report_schema_exposes_status_enum_and_disclaimers() -> None:
    schema = HassCheckReport.model_json_schema()
    schema_text = str(schema)

    assert "not_applicable" in schema_text
    assert "manual_review" in schema_text
    assert "security_review" in schema_text
    assert "official_ha_tier" in schema_text
    assert "hacs_acceptance" in schema_text


def test_applicability_source_defaults_to_default() -> None:
    app = Applicability(reason="why")
    assert app.source == "default"


def test_applicability_source_accepts_known_values() -> None:
    for src in ("default", "detected", "config"):
        app = Applicability(reason="why", source=src)
        assert app.source == src


def test_applicability_source_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        Applicability(reason="why", source="invalid")


def test_overrides_applied_default_is_empty() -> None:
    oa = OverridesApplied()
    assert oa.count == 0
    assert oa.rule_ids == []


def test_overrides_applied_with_valid_data_constructs() -> None:
    oa = OverridesApplied(count=2, rule_ids=["a.rule", "b.rule"])
    assert oa.count == 2
    assert oa.rule_ids == ["a.rule", "b.rule"]


def test_overrides_applied_count_must_match_rule_ids_length() -> None:
    with pytest.raises(ValidationError):
        OverridesApplied(count=2, rule_ids=["only.one"])


def test_overrides_applied_rule_ids_must_be_alphabetical() -> None:
    with pytest.raises(ValidationError):
        OverridesApplied(count=2, rule_ids=["b.rule", "a.rule"])


def test_report_summary_overrides_applied_default_is_empty_overrides_applied() -> None:
    summary = ReportSummary()
    assert summary.overrides_applied == OverridesApplied()
    assert summary.overrides_applied.count == 0
    assert summary.overrides_applied.rule_ids == []


# ---------- Phase 8.2: JSON contract — additive-only verification ----------


def test_json_contract_v01_fields_still_present(tmp_path) -> None:
    """All v0.1 JSON paths must exist in v0.2 output — no breaking changes."""
    import json

    from hasscheck.checker import run_check
    from hasscheck.output import report_to_json

    report = run_check(tmp_path)
    payload = json.loads(report_to_json(report))

    assert "schema_version" in payload
    assert "tool" in payload
    assert "name" in payload["tool"]
    assert "version" in payload["tool"]
    assert "project" in payload
    assert "summary" in payload
    assert "overall" in payload["summary"]
    assert "security_review" in payload["summary"]
    assert "official_ha_tier" in payload["summary"]
    assert "hacs_acceptance" in payload["summary"]
    assert "categories" in payload["summary"]
    assert "findings" in payload
    finding = payload["findings"][0]
    assert "rule_id" in finding
    assert "status" in finding
    assert "applicability" in finding
    assert "status" in finding["applicability"]
    assert "reason" in finding["applicability"]


def test_pyproject_version_matches_tool_info() -> None:
    import tomllib
    from pathlib import Path

    from hasscheck.models import ToolInfo

    pyproject = tomllib.loads(
        (Path(__file__).parent.parent / "pyproject.toml").read_text()
    )
    assert pyproject["project"]["version"] == ToolInfo().version


def test_yaml_importable() -> None:
    import yaml  # noqa: F401  — pyyaml runtime dep present


def test_json_contract_v02_additive_fields_present(tmp_path) -> None:
    """New v0.2 fields present without breaking v0.1 consumers."""
    import json

    from hasscheck.checker import run_check
    from hasscheck.output import report_to_json

    report = run_check(tmp_path)
    payload = json.loads(report_to_json(report))

    assert "overrides_applied" in payload["summary"]
    assert "count" in payload["summary"]["overrides_applied"]
    assert "rule_ids" in payload["summary"]["overrides_applied"]
    finding = payload["findings"][0]
    assert "source" in finding["applicability"]


def test_applicability_applied_default_is_empty() -> None:
    from hasscheck.models import ApplicabilityApplied

    applied = ApplicabilityApplied()

    assert applied.count == 0
    assert applied.rule_ids == []
    assert applied.flags == []


def test_applicability_applied_enforces_count_and_sorting() -> None:
    from hasscheck.models import ApplicabilityApplied

    ApplicabilityApplied(
        count=2,
        rule_ids=["diagnostics.file.exists", "repairs.file.exists"],
        flags=["has_user_fixable_repairs", "supports_diagnostics"],
    )

    with pytest.raises(ValidationError):
        ApplicabilityApplied(count=2, rule_ids=["diagnostics.file.exists"], flags=[])

    with pytest.raises(ValidationError):
        ApplicabilityApplied(
            count=2,
            rule_ids=["repairs.file.exists", "diagnostics.file.exists"],
            flags=[],
        )

    with pytest.raises(ValidationError):
        ApplicabilityApplied(
            count=1, rule_ids=["diagnostics.file.exists"], flags=["z", "a"]
        )


def test_report_summary_applicability_applied_default_is_empty() -> None:
    from hasscheck.models import ApplicabilityApplied

    summary = ReportSummary()

    assert summary.applicability_applied == ApplicabilityApplied()
