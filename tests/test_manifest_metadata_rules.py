import json

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus

REQUIRED_FIELD_RULES = {
    "name": "manifest.name.exists",
    "version": "manifest.version.exists",
    "documentation": "manifest.documentation.exists",
    "issue_tracker": "manifest.issue_tracker.exists",
    "codeowners": "manifest.codeowners.exists",
}


def write_manifest(root, payload: dict) -> None:
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def findings_for(root):
    return {finding.rule_id: finding for finding in run_check(root).findings}


def test_required_manifest_metadata_fields_pass_when_present(tmp_path) -> None:
    write_manifest(
        tmp_path,
        {
            "domain": "demo",
            "name": "Demo",
            "documentation": "https://example.com/docs",
            "issue_tracker": "https://example.com/issues",
            "codeowners": ["@demo"],
            "version": "0.1.0",
        },
    )

    findings = findings_for(tmp_path)

    for rule_id in REQUIRED_FIELD_RULES.values():
        assert findings[rule_id].status is RuleStatus.PASS
        assert (
            findings[rule_id].source.url
            == "https://www.hacs.xyz/docs/publish/integration/"
        )
        assert findings[rule_id].rule_version == "1.0.0"


def test_required_manifest_metadata_fields_fail_when_missing(tmp_path) -> None:
    write_manifest(tmp_path, {"domain": "demo"})

    findings = findings_for(tmp_path)

    for rule_id in REQUIRED_FIELD_RULES.values():
        assert findings[rule_id].status is RuleStatus.FAIL
        assert findings[rule_id].fix is not None


def test_required_manifest_metadata_fields_are_not_applicable_without_manifest(
    tmp_path,
) -> None:
    findings = findings_for(tmp_path)

    for rule_id in REQUIRED_FIELD_RULES.values():
        assert findings[rule_id].status is RuleStatus.NOT_APPLICABLE
        assert "manifest.json must exist" in findings[rule_id].applicability.reason


def test_codeowners_requires_non_empty_list_of_strings(tmp_path) -> None:
    write_manifest(
        tmp_path,
        {
            "domain": "demo",
            "name": "Demo",
            "documentation": "https://example.com/docs",
            "issue_tracker": "https://example.com/issues",
            "codeowners": [],
            "version": "0.1.0",
        },
    )

    assert (
        findings_for(tmp_path)["manifest.codeowners.exists"].status is RuleStatus.FAIL
    )
