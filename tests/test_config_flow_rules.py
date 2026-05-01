import json

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus


def write_integration(root, manifest: dict, *, config_flow: bool = False) -> None:
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if config_flow:
        (integration / "config_flow.py").write_text(
            "class DemoConfigFlow: ...\n", encoding="utf-8"
        )


def findings_for(root):
    return {finding.rule_id: finding for finding in run_check(root).findings}


def test_config_flow_file_presence_passes_when_file_exists(tmp_path) -> None:
    write_integration(
        tmp_path, {"domain": "demo", "config_flow": True}, config_flow=True
    )

    findings = findings_for(tmp_path)

    assert findings["config_flow.file.exists"].status is RuleStatus.PASS


def test_config_flow_file_presence_warns_when_file_missing(tmp_path) -> None:
    write_integration(tmp_path, {"domain": "demo"})

    findings = findings_for(tmp_path)

    assert findings["config_flow.file.exists"].status is RuleStatus.WARN
    assert findings["config_flow.file.exists"].fix is not None


def test_config_flow_manifest_consistency_passes_when_file_and_manifest_flag_match(
    tmp_path,
) -> None:
    write_integration(
        tmp_path, {"domain": "demo", "config_flow": True}, config_flow=True
    )

    findings = findings_for(tmp_path)

    assert findings["config_flow.manifest_flag_consistent"].status is RuleStatus.PASS
    assert findings["config_flow.manifest_flag_consistent"].source.url == (
        "https://developers.home-assistant.io/docs/core/integration/config_flow"
    )


def test_config_flow_manifest_consistency_fails_when_file_exists_but_flag_is_not_true(
    tmp_path,
) -> None:
    write_integration(tmp_path, {"domain": "demo"}, config_flow=True)

    findings = findings_for(tmp_path)

    assert findings["config_flow.manifest_flag_consistent"].status is RuleStatus.FAIL
    assert (
        "config_flow: true" in findings["config_flow.manifest_flag_consistent"].message
    )


def test_config_flow_manifest_consistency_fails_when_manifest_flag_true_but_file_missing(
    tmp_path,
) -> None:
    write_integration(tmp_path, {"domain": "demo", "config_flow": True})

    findings = findings_for(tmp_path)

    assert findings["config_flow.manifest_flag_consistent"].status is RuleStatus.FAIL
    assert "config_flow.py" in findings["config_flow.manifest_flag_consistent"].message


def test_config_flow_manifest_consistency_not_applicable_when_no_config_flow_signal(
    tmp_path,
) -> None:
    write_integration(tmp_path, {"domain": "demo"})

    findings = findings_for(tmp_path)

    assert (
        findings["config_flow.manifest_flag_consistent"].status
        is RuleStatus.NOT_APPLICABLE
    )


def test_config_flow_rules_not_applicable_without_integration(tmp_path) -> None:
    findings = findings_for(tmp_path)

    assert findings["config_flow.file.exists"].status is RuleStatus.NOT_APPLICABLE
    assert (
        findings["config_flow.manifest_flag_consistent"].status
        is RuleStatus.NOT_APPLICABLE
    )
