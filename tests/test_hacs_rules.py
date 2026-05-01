from hasscheck.checker import run_check
from hasscheck.models import RuleStatus


def test_missing_hacs_json_is_warned_for_custom_integration(tmp_path) -> None:
    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text('{"domain":"demo"}', encoding="utf-8")

    findings = {finding.rule_id: finding for finding in run_check(tmp_path).findings}

    assert findings["hacs.file.parseable"].status is RuleStatus.WARN


def test_invalid_hacs_json_fails_when_present(tmp_path) -> None:
    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text('{"domain":"demo"}', encoding="utf-8")
    (tmp_path / "hacs.json").write_text('{not-json', encoding="utf-8")

    findings = {finding.rule_id: finding for finding in run_check(tmp_path).findings}

    assert findings["hacs.file.parseable"].status is RuleStatus.FAIL


def test_valid_hacs_json_passes(tmp_path) -> None:
    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text('{"domain":"demo"}', encoding="utf-8")
    (tmp_path / "hacs.json").write_text('{}', encoding="utf-8")

    findings = {finding.rule_id: finding for finding in run_check(tmp_path).findings}

    assert findings["hacs.file.parseable"].status is RuleStatus.PASS
