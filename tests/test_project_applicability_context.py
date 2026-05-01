import json
from pathlib import Path

from hasscheck.checker import run_check
from hasscheck.config import HassCheckConfig, ProjectApplicability
from hasscheck.models import RuleStatus


def write_integration(root: Path, manifest: dict | None = None) -> Path:
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps(manifest or {"domain": "demo"}), encoding="utf-8"
    )
    return integration


def findings_for(root: Path, config: HassCheckConfig | None = None):
    return {
        finding.rule_id: finding for finding in run_check(root, config=config).findings
    }


def test_project_applicability_softens_missing_optional_files(tmp_path: Path) -> None:
    write_integration(tmp_path)
    config = HassCheckConfig(
        applicability=ProjectApplicability(
            supports_diagnostics=False,
            has_user_fixable_repairs=False,
            uses_config_flow=False,
        )
    )

    report = run_check(tmp_path, config=config)
    findings = {finding.rule_id: finding for finding in report.findings}

    for rule_id in (
        "diagnostics.file.exists",
        "diagnostics.redaction.used",  # v0.8 PR4 — also responds to supports_diagnostics
        "repairs.file.exists",
        "config_flow.file.exists",
        "config_flow.manifest_flag_consistent",
        "config_flow.user_step.exists",  # v0.8 PR3 — also responds to uses_config_flow
    ):
        assert findings[rule_id].status is RuleStatus.NOT_APPLICABLE
        assert findings[rule_id].applicability.source == "config"

    assert report.summary.applicability_applied.count == 6
    assert report.summary.applicability_applied.rule_ids == [
        "config_flow.file.exists",
        "config_flow.manifest_flag_consistent",
        "config_flow.user_step.exists",
        "diagnostics.file.exists",
        "diagnostics.redaction.used",
        "repairs.file.exists",
    ]
    assert report.summary.applicability_applied.flags == [
        "has_user_fixable_repairs",
        "supports_diagnostics",
        "uses_config_flow",
    ]


def test_project_applicability_natural_pass_wins(tmp_path: Path) -> None:
    integration = write_integration(tmp_path, {"domain": "demo", "config_flow": True})
    (integration / "diagnostics.py").write_text('"""diagnostics"""\n', encoding="utf-8")
    (integration / "repairs.py").write_text('"""repairs"""\n', encoding="utf-8")
    (integration / "config_flow.py").write_text('"""config flow"""\n', encoding="utf-8")
    config = HassCheckConfig(
        applicability=ProjectApplicability(
            supports_diagnostics=False,
            has_user_fixable_repairs=False,
            uses_config_flow=False,
        )
    )

    report = run_check(tmp_path, config=config)
    findings = {finding.rule_id: finding for finding in report.findings}

    for rule_id in (
        "diagnostics.file.exists",
        "repairs.file.exists",
        "config_flow.file.exists",
        "config_flow.manifest_flag_consistent",
    ):
        assert findings[rule_id].status is RuleStatus.PASS
        assert findings[rule_id].applicability.source == "default"

    # config_flow.user_step.exists is NOT_APPLICABLE via config even when config_flow.py
    # exists — per spec, uses_config_flow=False always suppresses user-step inspection.
    assert findings["config_flow.user_step.exists"].status is RuleStatus.NOT_APPLICABLE
    assert findings["config_flow.user_step.exists"].applicability.source == "config"
    # diagnostics.redaction.used is also suppressed via config (supports_diagnostics=False).
    assert findings["diagnostics.redaction.used"].status is RuleStatus.NOT_APPLICABLE
    assert findings["diagnostics.redaction.used"].applicability.source == "config"
    # Both config_flow.user_step.exists and diagnostics.redaction.used suppressed via config.
    assert report.summary.applicability_applied.count == 2


def test_project_applicability_does_not_hide_config_flow_mismatch(
    tmp_path: Path,
) -> None:
    integration = write_integration(tmp_path, {"domain": "demo"})
    (integration / "config_flow.py").write_text('"""config flow"""\n', encoding="utf-8")
    config = HassCheckConfig(applicability=ProjectApplicability(uses_config_flow=False))

    finding = findings_for(tmp_path, config=config)[
        "config_flow.manifest_flag_consistent"
    ]

    assert finding.status is RuleStatus.FAIL
    assert finding.applicability.source == "default"


def test_project_applicability_loaded_from_disk(tmp_path: Path) -> None:
    write_integration(tmp_path)
    (tmp_path / "hasscheck.yaml").write_text(
        "applicability:\n"
        "  supports_diagnostics: false\n"
        "  has_user_fixable_repairs: false\n"
    )

    report = run_check(tmp_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["diagnostics.file.exists"].status is RuleStatus.NOT_APPLICABLE
    assert findings["diagnostics.redaction.used"].status is RuleStatus.NOT_APPLICABLE
    assert findings["repairs.file.exists"].status is RuleStatus.NOT_APPLICABLE
    assert report.summary.applicability_applied.count == 3
