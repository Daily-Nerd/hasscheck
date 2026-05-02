from datetime import UTC

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


# ---------- Phase 141: Schema 0.5.0 model assertions (RED) ----------


def test_schema_version_is_0_5_0() -> None:
    from hasscheck.models import SCHEMA_VERSION

    assert SCHEMA_VERSION == "0.5.0"


def test_project_info_new_fields_default_none_or_unknown() -> None:
    from hasscheck.models import ProjectInfo

    pi = ProjectInfo(path="/tmp/test")
    assert pi.integration_version is None
    assert pi.integration_version_source == "unknown"
    assert pi.manifest_hash is None
    assert pi.requirements_hash is None


def test_report_target_model_constructs_with_defaults() -> None:
    from hasscheck.models import ReportTarget

    t = ReportTarget()
    assert t.integration_domain is None
    assert t.integration_version is None
    assert t.integration_version_source == "unknown"
    assert t.integration_release_tag is None
    assert t.commit_sha is None
    assert t.ha_version is None
    assert t.python_version is None
    assert t.check_mode == "static"


def test_report_target_check_mode_rejects_invalid_literal() -> None:
    from hasscheck.models import ReportTarget

    with pytest.raises(ValidationError):
        ReportTarget(check_mode="dynamic")


def test_report_validity_claim_scope_frozen() -> None:
    from datetime import datetime

    from hasscheck.models import ReportValidity

    with pytest.raises(ValidationError):
        ReportValidity(
            claim_scope="anything_else", checked_at=datetime(2026, 1, 1, tzinfo=UTC)
        )


def test_hasscheck_report_target_and_validity_optional() -> None:
    from hasscheck.models import HassCheckReport, ProjectInfo, ReportSummary

    report = HassCheckReport(
        project=ProjectInfo(path="/tmp"),
        summary=ReportSummary(),
        findings=[],
    )
    serialized = report.to_json_dict()
    deserialized = HassCheckReport.model_validate(serialized)
    assert deserialized.target is None
    assert deserialized.validity is None


def test_hasscheck_report_serializes_target_and_validity_when_set() -> None:
    from datetime import datetime

    from hasscheck.models import (
        HassCheckReport,
        ProjectInfo,
        ReportSummary,
        ReportTarget,
        ReportValidity,
    )

    target = ReportTarget(integration_version="1.2.3", check_mode="static")
    validity = ReportValidity(
        checked_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    report = HassCheckReport(
        project=ProjectInfo(path="/tmp"),
        summary=ReportSummary(),
        findings=[],
        target=target,
        validity=validity,
    )
    d = report.to_json_dict()
    assert "target" in d
    assert "validity" in d
    assert d["target"]["integration_version"] == "1.2.3"
    assert d["validity"]["claim_scope"] == "exact_build_only"


def test_old_0_4_0_report_still_parses_into_v0_5_0_model() -> None:
    from hasscheck.models import HassCheckReport

    old_dict = {
        "schema_version": "0.4.0",
        "tool": {"name": "hasscheck", "version": "0.13.0"},
        "project": {"path": "/old/path"},
        "ruleset": {"id": "hasscheck-ha-2026.5", "source_checked_at": "2026-05-01"},
        "summary": {
            "overall": "informational_only",
            "security_review": "not_performed",
            "official_ha_tier": "not_assigned",
            "hacs_acceptance": "not_guaranteed",
            "categories": [],
            "overrides_applied": {"count": 0, "rule_ids": []},
            "applicability_applied": {"count": 0, "rule_ids": [], "flags": []},
        },
        "findings": [],
    }
    report = HassCheckReport.model_validate(old_dict)
    assert report.target is None
    assert report.validity is None
