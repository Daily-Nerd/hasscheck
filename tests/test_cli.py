import json
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from hasscheck.cli import app, should_exit_nonzero
from hasscheck.config import GateConfig, GateMode
from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)

runner = CliRunner()


def write_minimal_integration(root: Path) -> None:
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": "demo"}),
        encoding="utf-8",
    )


def test_check_json_outputs_report(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.5.0"
    assert payload["summary"]["security_review"] == "not_performed"
    assert payload["summary"]["official_ha_tier"] == "not_assigned"
    assert payload["summary"]["hacs_acceptance"] == "not_guaranteed"
    assert payload["findings"][0]["rule_id"]


def test_schema_command_outputs_json_schema() -> None:
    result = runner.invoke(app, ["schema"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["title"] == "HassCheckReport"


def test_schema_help_does_not_reference_v01() -> None:
    result = runner.invoke(app, ["schema", "--help"])
    assert "v0.1" not in result.output


def test_explain_known_rule() -> None:
    result = runner.invoke(app, ["explain", "manifest.domain.exists"])

    assert result.exit_code == 0
    assert "manifest.domain.exists" in result.stdout
    assert "Source:" in result.stdout


def test_explain_shows_overridable_false_for_locked_rule() -> None:
    result = runner.invoke(app, ["explain", "manifest.exists"])
    assert result.exit_code == 0
    assert "overridable: false" in result.output.lower()


def test_explain_shows_overridable_true_for_softable_rule() -> None:
    result = runner.invoke(app, ["explain", "repairs.file.exists"])
    assert result.exit_code == 0
    assert "overridable: true" in result.output.lower()


# ---------- Phase 5: --no-config flag + ConfigError handling ----------


def test_no_config_flag_is_registered() -> None:
    command = get_command(app).commands["check"]

    assert any("--no-config" in option.opts for option in command.params)


def test_scaffold_subcommand_is_registered() -> None:
    result = runner.invoke(app, ["scaffold", "--help"])
    assert result.exit_code == 0
    assert "scaffold" in result.output.lower()


def test_no_config_flag_skips_yaml(tmp_path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    result = runner.invoke(
        app, ["check", "--path", str(tmp_path), "--format", "json", "--no-config"]
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["overrides_applied"]["count"] == 0


def test_malformed_yaml_exits_nonzero(tmp_path) -> None:
    (tmp_path / "hasscheck.yaml").write_text("rules: [unclosed\n")
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code != 0
    assert "YAML" in result.output or "parse" in result.output.lower()


def test_locked_rule_override_exits_nonzero(tmp_path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  manifest.exists:\n"
        "    status: not_applicable\n"
        "    reason: we do not need this\n"
    )
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code != 0
    assert "manifest.exists" in result.output


def test_json_output_includes_overrides_applied(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert "overrides_applied" in payload["summary"]
    assert "count" in payload["summary"]["overrides_applied"]
    assert "rule_ids" in payload["summary"]["overrides_applied"]


def test_json_output_includes_applicability_applied(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["applicability_applied"] == {
        "count": 0,
        "rule_ids": [],
        "flags": [],
    }


# ---------- Phase 6: terminal banner + JSON source field ----------


def test_json_finding_applicability_source_present(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    for finding in payload["findings"]:
        assert "source" in finding["applicability"]


def test_terminal_banner_shown_when_overrides_applied(tmp_path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "1 override" in result.output.lower() or "override" in result.output.lower()


def test_terminal_banner_not_shown_when_no_overrides(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "override" not in result.output.lower()


def test_terminal_overridden_finding_has_config_marker(tmp_path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "(config)" in result.output


def test_terminal_non_overridden_finding_no_config_marker(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "(config)" not in result.output


# ---------- v0.3: project applicability disclosure ----------


def test_terminal_banner_shown_when_applicability_applied(tmp_path) -> None:
    write_minimal_integration(tmp_path)
    (tmp_path / "hasscheck.yaml").write_text(
        "applicability:\n"
        "  supports_diagnostics: false\n"
        "  has_user_fixable_repairs: false\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["check", "--path", str(tmp_path)])

    assert result.exit_code == 1
    assert "3 applicability decision(s) applied from hasscheck.yaml." in result.output


def test_terminal_banner_not_shown_when_no_applicability_applied(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])

    assert result.exit_code == 1
    assert "applicability decision" not in result.output.lower()


def test_terminal_applicability_finding_has_config_marker(tmp_path) -> None:
    write_minimal_integration(tmp_path)
    (tmp_path / "hasscheck.yaml").write_text(
        "applicability:\n  supports_diagnostics: false\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["check", "--path", str(tmp_path)])

    assert result.exit_code == 1
    # Rich may wrap long rule IDs across lines; check both parts appear in output
    assert "diagnostics.file.exists" in result.output
    assert "(config)" in result.output


# ---------- --format option ----------


def test_format_md_outputs_markdown_heading(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "md"])

    assert result.exit_code == 1
    assert "## HassCheck Signals" in result.output


def test_format_terminal_explicit_does_not_output_markdown(tmp_path) -> None:
    result = runner.invoke(
        app, ["check", "--path", str(tmp_path), "--format", "terminal"]
    )

    assert result.exit_code == 1
    assert "## HassCheck Signals" not in result.output


def test_format_json_shortflag_outputs_json(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "-f", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.5.0"


# ---------- Exit code behaviour ----------


def test_exit_code_zero_when_no_fail_findings() -> None:
    examples = Path(__file__).parent.parent / "examples" / "good_integration"
    result = runner.invoke(app, ["check", "--path", str(examples), "--format", "json"])

    payload = json.loads(result.stdout)
    assert all(f["status"] != "fail" for f in payload["findings"])
    assert result.exit_code == 0


def test_exit_code_one_when_fail_finding_present(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])

    payload = json.loads(result.stdout)
    assert any(f["status"] == "fail" for f in payload["findings"])
    assert result.exit_code == 1


def test_exit_code_zero_for_warn_only_findings() -> None:
    examples = Path(__file__).parent.parent / "examples" / "good_integration"
    result = runner.invoke(app, ["check", "--path", str(examples), "--format", "json"])

    payload = json.loads(result.stdout)
    non_fail = all(f["status"] != "fail" for f in payload["findings"])
    assert non_fail
    assert result.exit_code == 0


# ---------- publish --withdraw confirm guard (v0.8) ----------


def test_publish_withdraw_confirm_yes(tmp_path, monkeypatch) -> None:
    """User answers y → withdraw_report is called, exit 0."""
    monkeypatch.setenv("HASSCHECK_OIDC_TOKEN", "tok")
    called = {}

    def fake_withdraw(**kw):
        called.update(kw)

    monkeypatch.setattr("hasscheck.cli.withdraw_report", fake_withdraw)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        [
            "publish",
            "--path",
            str(tmp_path),
            "--withdraw",
            "--report-id",
            "rep_x",
            "--slug",
            "owner/repo",
        ],
        input="y\n",
    )
    assert result.exit_code == 0
    assert called.get("report_id") == "rep_x"


def test_publish_withdraw_confirm_no(tmp_path, monkeypatch) -> None:
    """User answers n → withdraw_report NOT called, exit != 0."""
    monkeypatch.setenv("HASSCHECK_OIDC_TOKEN", "tok")
    called = {}

    def fake_withdraw(**kw):
        called.update(kw)

    monkeypatch.setattr("hasscheck.cli.withdraw_report", fake_withdraw)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        [
            "publish",
            "--path",
            str(tmp_path),
            "--withdraw",
            "--report-id",
            "rep_x",
            "--slug",
            "owner/repo",
        ],
        input="n\n",
    )
    assert result.exit_code != 0
    assert not called


def test_publish_withdraw_force_skips_prompt(tmp_path, monkeypatch) -> None:
    """--force bypasses confirm prompt entirely."""
    monkeypatch.setenv("HASSCHECK_OIDC_TOKEN", "tok")
    called = {}

    def fake_withdraw(**kw):
        called.update(kw)

    monkeypatch.setattr("hasscheck.cli.withdraw_report", fake_withdraw)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        [
            "publish",
            "--path",
            str(tmp_path),
            "--withdraw",
            "--report-id",
            "rep_x",
            "--slug",
            "owner/repo",
            "--force",
        ],
    )
    assert result.exit_code == 0
    assert called.get("report_id") == "rep_x"
    assert "Withdraw" not in result.output


def test_publish_withdraw_non_tty_aborts(tmp_path, monkeypatch) -> None:
    """Empty stdin (non-TTY / CI without --force) → exit != 0, no withdraw call."""
    monkeypatch.setenv("HASSCHECK_OIDC_TOKEN", "tok")
    called = {}

    def fake_withdraw(**kw):
        called.update(kw)

    monkeypatch.setattr("hasscheck.cli.withdraw_report", fake_withdraw)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        [
            "publish",
            "--path",
            str(tmp_path),
            "--withdraw",
            "--report-id",
            "rep_x",
            "--slug",
            "owner/repo",
        ],
        input="",
    )
    assert result.exit_code != 0
    assert not called
    assert "Aborted" in result.output or "Aborted" in (result.stderr or "")


def test_publish_help_contains_force_flag(tmp_path) -> None:
    """--force is registered on publish and its help mentions CI/non-TTY usage."""
    cmd = get_command(app)
    publish_cmd = cmd.commands["publish"]
    force_param = next((p for p in publish_cmd.params if p.name == "force"), None)
    assert force_param is not None, "publish must declare a --force option"
    assert "--force" in force_param.opts
    help_text = (force_param.help or "").lower()
    assert any(token in help_text for token in ("ci", "non-tty", "skip"))


# ---------- init --enable-publish (v0.8) ----------


def test_init_enable_publish_cli_writes_publish_workflow(tmp_path) -> None:
    """CLI: hasscheck init --enable-publish → workflow with id-token: write + emit-publish."""
    result = runner.invoke(
        app,
        ["init", "--path", str(tmp_path), "--enable-publish"],
    )
    assert result.exit_code == 0
    workflow = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    content = workflow.read_text()
    assert "id-token: write" in content
    assert "emit-publish: 'true'" in content


def test_init_default_cli_does_not_write_publish_workflow(tmp_path) -> None:
    """CLI: hasscheck init (no --enable-publish) → standard workflow without emit-publish."""
    result = runner.invoke(app, ["init", "--path", str(tmp_path)])
    assert result.exit_code == 0
    workflow = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    content = workflow.read_text()
    assert "emit-publish" not in content


# ---------- publish --dry-run (v0.13) ----------


def test_publish_dry_run_no_network_request(tmp_path, monkeypatch) -> None:
    """--dry-run exits 0 and makes no HTTP requests."""
    write_minimal_integration(tmp_path)
    monkeypatch.delenv("HASSCHECK_OIDC_TOKEN", raising=False)

    http_called = []

    def mock_post(*args, **kwargs):
        http_called.append(True)

    monkeypatch.setattr("httpx.Client.post", mock_post)

    result = runner.invoke(
        app,
        ["publish", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert not http_called
    assert "dry-run: no network request made" in result.output


def test_publish_dry_run_shows_endpoint(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HASSCHECK_OIDC_TOKEN", raising=False)
    monkeypatch.delenv("HASSCHECK_PUBLISH_ENDPOINT", raising=False)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        ["publish", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "https://hasscheck.io" in result.output
    assert "endpoint resolved from: default" in result.output


def test_publish_dry_run_shows_endpoint_from_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HASSCHECK_OIDC_TOKEN", raising=False)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        ["publish", "--path", str(tmp_path), "--dry-run", "--to", "https://my.host"],
    )
    assert result.exit_code == 0
    assert "https://my.host" in result.output
    assert "endpoint resolved from: --to flag" in result.output


def test_publish_dry_run_token_not_detected(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HASSCHECK_OIDC_TOKEN", raising=False)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        ["publish", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "not detected" in result.output


def test_publish_dry_run_token_detected_via_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HASSCHECK_OIDC_TOKEN", "tok123")
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        ["publish", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "$HASSCHECK_OIDC_TOKEN" in result.output


def test_publish_dry_run_shows_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HASSCHECK_OIDC_TOKEN", raising=False)
    write_minimal_integration(tmp_path)

    result = runner.invoke(
        app,
        ["publish", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "schema_version: 0.5.0" in result.output


def test_publish_dry_run_withdraw_no_network(tmp_path, monkeypatch) -> None:
    """--dry-run --withdraw shows what would be withdrawn, makes no DELETE."""
    monkeypatch.delenv("HASSCHECK_OIDC_TOKEN", raising=False)
    write_minimal_integration(tmp_path)

    http_called = []

    def mock_delete(*args, **kwargs):
        http_called.append(True)

    monkeypatch.setattr("httpx.Client.delete", mock_delete)

    result = runner.invoke(
        app,
        [
            "publish",
            "--path",
            str(tmp_path),
            "--dry-run",
            "--withdraw",
            "--report-id",
            "rep_abc",
            "--slug",
            "owner/repo",
            "--force",
        ],
    )
    assert result.exit_code == 0, result.output
    assert not http_called
    assert "dry-run: no network request made" in result.output
    assert "rep_abc" in result.output


def test_publish_dry_run_flag_registered() -> None:
    cmd = get_command(app)
    publish_cmd = cmd.commands["publish"]
    dry_run_param = next((p for p in publish_cmd.params if p.name == "dry_run"), None)
    assert dry_run_param is not None, "publish must declare a --dry-run option"


# ---------- Gate modes — pure function ----------


def make_finding(
    *,
    rule_id: str = "manifest.domain.exists",
    severity: RuleSeverity = RuleSeverity.REQUIRED,
    status: RuleStatus = RuleStatus.FAIL,
) -> Finding:
    """Build a minimal Finding for gate-mode unit tests."""
    app_status = (
        ApplicabilityStatus.APPLICABLE
        if status not in (RuleStatus.NOT_APPLICABLE, RuleStatus.MANUAL_REVIEW)
        else ApplicabilityStatus.NOT_APPLICABLE
    )
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category="test",
        status=status,
        severity=severity,
        title="Test finding",
        message="Test message",
        applicability=Applicability(status=app_status, reason="test"),
        source=RuleSource(url="https://example.com"),
    )


# Legacy behavior (gate=None)


def test_should_exit_nonzero_legacy_fail_returns_true() -> None:
    findings = [make_finding(status=RuleStatus.FAIL)]
    assert should_exit_nonzero(findings, gate=None) is True


def test_should_exit_nonzero_legacy_warn_returns_false() -> None:
    findings = [make_finding(status=RuleStatus.WARN)]
    assert should_exit_nonzero(findings, gate=None) is False


def test_should_exit_nonzero_legacy_multiple_findings_any_fail() -> None:
    findings = [
        make_finding(status=RuleStatus.WARN),
        make_finding(rule_id="other.rule", status=RuleStatus.FAIL),
    ]
    assert should_exit_nonzero(findings, gate=None) is True


# Advisory mode


@pytest.mark.parametrize("status", [RuleStatus.FAIL, RuleStatus.WARN])
def test_should_exit_nonzero_advisory_always_false(status: RuleStatus) -> None:
    gate = GateConfig(mode=GateMode.ADVISORY)
    findings = [make_finding(status=status)]
    assert should_exit_nonzero(findings, gate=gate) is False


# Strict-required mode


@pytest.mark.parametrize(
    "severity,status,expected",
    [
        (RuleSeverity.REQUIRED, RuleStatus.FAIL, True),
        (RuleSeverity.REQUIRED, RuleStatus.WARN, True),
        (RuleSeverity.REQUIRED, RuleStatus.PASS, False),
        (RuleSeverity.RECOMMENDED, RuleStatus.FAIL, False),
        (RuleSeverity.INFORMATIONAL, RuleStatus.FAIL, False),
    ],
)
def test_should_exit_nonzero_strict_required(
    severity: RuleSeverity, status: RuleStatus, expected: bool
) -> None:
    gate = GateConfig(mode=GateMode.STRICT_REQUIRED)
    findings = [make_finding(severity=severity, status=status)]
    assert should_exit_nonzero(findings, gate=gate) is expected


# HACS-publish mode


@pytest.mark.parametrize(
    "severity,status,expected",
    [
        (RuleSeverity.REQUIRED, RuleStatus.FAIL, True),
        (RuleSeverity.REQUIRED, RuleStatus.WARN, True),
        (RuleSeverity.RECOMMENDED, RuleStatus.FAIL, True),
        (RuleSeverity.RECOMMENDED, RuleStatus.WARN, True),
        (RuleSeverity.INFORMATIONAL, RuleStatus.FAIL, False),
    ],
)
def test_should_exit_nonzero_hacs_publish(
    severity: RuleSeverity, status: RuleStatus, expected: bool
) -> None:
    gate = GateConfig(mode=GateMode.HACS_PUBLISH)
    findings = [make_finding(severity=severity, status=status)]
    assert should_exit_nonzero(findings, gate=gate) is expected


# Upgrade-radar mode


@pytest.mark.parametrize(
    "rule_id,status,expected",
    [
        ("version.foo", RuleStatus.WARN, True),
        ("version.bar", RuleStatus.FAIL, True),
        ("manifest.domain", RuleStatus.FAIL, False),
    ],
)
def test_should_exit_nonzero_upgrade_radar(
    rule_id: str, status: RuleStatus, expected: bool
) -> None:
    gate = GateConfig(mode=GateMode.UPGRADE_RADAR)
    findings = [make_finding(rule_id=rule_id, status=status)]
    assert should_exit_nonzero(findings, gate=gate) is expected


# Boundary cases


@pytest.mark.parametrize(
    "gate",
    [
        None,
        GateConfig(mode=GateMode.ADVISORY),
        GateConfig(mode=GateMode.STRICT_REQUIRED),
        GateConfig(mode=GateMode.HACS_PUBLISH),
        GateConfig(mode=GateMode.UPGRADE_RADAR),
    ],
)
def test_should_exit_nonzero_empty_findings_all_modes(
    gate: GateConfig | None,
) -> None:
    assert should_exit_nonzero([], gate=gate) is False


@pytest.mark.parametrize(
    "gate",
    [
        None,
        GateConfig(mode=GateMode.ADVISORY),
        GateConfig(mode=GateMode.STRICT_REQUIRED),
        GateConfig(mode=GateMode.HACS_PUBLISH),
        GateConfig(mode=GateMode.UPGRADE_RADAR),
    ],
)
def test_should_exit_nonzero_all_pass_findings(gate: GateConfig | None) -> None:
    findings = [
        make_finding(severity=RuleSeverity.REQUIRED, status=RuleStatus.PASS),
        make_finding(
            rule_id="other.rule",
            severity=RuleSeverity.RECOMMENDED,
            status=RuleStatus.PASS,
        ),
    ]
    assert should_exit_nonzero(findings, gate=gate) is False
