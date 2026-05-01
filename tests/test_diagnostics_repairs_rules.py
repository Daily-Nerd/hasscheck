from hasscheck.checker import run_check
from hasscheck.models import RuleStatus


def write_integration(
    root, *, diagnostics: bool = False, repairs: bool = False
) -> None:
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text('{"domain":"demo"}', encoding="utf-8")
    if diagnostics:
        (integration / "diagnostics.py").write_text(
            '"""Diagnostics fixture."""\n', encoding="utf-8"
        )
    if repairs:
        (integration / "repairs.py").write_text(
            '"""Repairs fixture."""\n', encoding="utf-8"
        )


def findings_for(root):
    return {finding.rule_id: finding for finding in run_check(root).findings}


def test_diagnostics_and_repairs_pass_when_files_exist(tmp_path) -> None:
    write_integration(tmp_path, diagnostics=True, repairs=True)

    findings = findings_for(tmp_path)

    assert findings["diagnostics.file.exists"].status is RuleStatus.PASS
    assert findings["repairs.file.exists"].status is RuleStatus.PASS


def test_diagnostics_and_repairs_warn_when_files_are_missing(tmp_path) -> None:
    write_integration(tmp_path)

    findings = findings_for(tmp_path)

    assert findings["diagnostics.file.exists"].status is RuleStatus.WARN
    assert findings["diagnostics.file.exists"].fix is not None
    assert findings["repairs.file.exists"].status is RuleStatus.WARN
    assert findings["repairs.file.exists"].fix is not None


def test_diagnostics_and_repairs_not_applicable_without_integration(tmp_path) -> None:
    findings = findings_for(tmp_path)

    assert findings["diagnostics.file.exists"].status is RuleStatus.NOT_APPLICABLE
    assert findings["repairs.file.exists"].status is RuleStatus.NOT_APPLICABLE


def test_diagnostics_and_repairs_use_diagnostics_repairs_category(tmp_path) -> None:
    write_integration(tmp_path, diagnostics=True, repairs=True)

    findings = findings_for(tmp_path)

    assert findings["diagnostics.file.exists"].category == "diagnostics_repairs"
    assert findings["repairs.file.exists"].category == "diagnostics_repairs"
