import json

from hasscheck.checker import run_check
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
