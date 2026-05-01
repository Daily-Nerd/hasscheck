import pytest
from pydantic import ValidationError

from hasscheck.models import Applicability, OverridesApplied, RuleStatus, HassCheckReport


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
