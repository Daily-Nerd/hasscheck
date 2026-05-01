import json

import pytest

from hasscheck.checker import run_check
from hasscheck.config import HassCheckConfig, RuleOverride
from hasscheck.models import RuleStatus


def test_missing_custom_components_and_manifest_are_reported(tmp_path) -> None:
    report = run_check(tmp_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["hacs.custom_components.exists"].status is RuleStatus.FAIL
    assert findings["manifest.exists"].status is RuleStatus.FAIL
    assert findings["manifest.domain.exists"].status is RuleStatus.NOT_APPLICABLE


def test_manifest_domain_passes_for_custom_integration(tmp_path) -> None:
    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "demo",
                "name": "Demo",
                "documentation": "https://example.com",
                "issue_tracker": "https://example.com/issues",
                "codeowners": ["@demo"],
                "version": "0.1.0",
            }
        ),
        encoding="utf-8",
    )

    report = run_check(tmp_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["hacs.custom_components.exists"].status is RuleStatus.PASS
    assert findings["manifest.exists"].status is RuleStatus.PASS
    assert findings["manifest.domain.exists"].status is RuleStatus.PASS


# ---------- Phase 4: config kwarg + discovery ----------

def test_run_check_config_and_no_config_conflict(tmp_path) -> None:
    with pytest.raises(ValueError, match="no_config"):
        run_check(tmp_path, config=HassCheckConfig(), no_config=True)


def test_run_check_no_config_flag_skips_yaml(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — a real override target
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    report = run_check(tmp_path, no_config=True)
    assert report.summary.overrides_applied.count == 0


def test_run_check_discovers_yaml_at_root(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — confirms the override is actually applied
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    report = run_check(tmp_path)
    assert report.summary.overrides_applied.count == 1
    assert "tests.folder.exists" in report.summary.overrides_applied.rule_ids


def test_run_check_applies_overrides_from_config_kwarg(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — confirms source="config" is set
    config = HassCheckConfig(
        rules={"tests.folder.exists": RuleOverride(status="not_applicable", reason="test")}
    )
    report = run_check(tmp_path, config=config)
    findings = {f.rule_id: f for f in report.findings}
    assert findings["tests.folder.exists"].status is RuleStatus.NOT_APPLICABLE
    assert findings["tests.folder.exists"].applicability.source == "config"
    assert report.summary.overrides_applied.count == 1


def test_run_check_no_yaml_overrides_applied_is_empty(tmp_path) -> None:
    report = run_check(tmp_path)
    assert report.summary.overrides_applied.count == 0
    assert report.summary.overrides_applied.rule_ids == []


def test_run_check_schema_version_is_0_2_0(tmp_path) -> None:
    report = run_check(tmp_path)
    assert report.schema_version == "0.2.0"
