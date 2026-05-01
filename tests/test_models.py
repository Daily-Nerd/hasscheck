from hasscheck.models import RuleStatus, HassCheckReport


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
