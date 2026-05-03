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


# ---------- Gate modes — CliRunner ----------


def write_config_with_gate(tmp_path: Path, mode: str, schema: str = "0.6.0") -> None:
    """Write a hasscheck.yaml with a gate stanza to tmp_path."""
    (tmp_path / "hasscheck.yaml").write_text(
        f"schema_version: '{schema}'\ngate:\n  mode: {mode}\n",
        encoding="utf-8",
    )


def test_check_exit_code_advisory_no_exit_on_fail(tmp_path: Path) -> None:
    """Advisory gate: FAIL findings present but exit code must be 0."""
    write_config_with_gate(tmp_path, "advisory")
    # Empty tmp_path → manifest.exists FAIL (REQUIRED) → gate=advisory → exit 0
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])
    payload = json.loads(result.stdout)
    assert any(f["status"] == "fail" for f in payload["findings"]), (
        "Expected FAIL findings to confirm gate suppression is being tested"
    )
    assert result.exit_code == 0


def test_check_exit_code_strict_required_exits_on_required_fail(
    tmp_path: Path,
) -> None:
    """Strict-required gate: REQUIRED FAIL → exit 1."""
    write_config_with_gate(tmp_path, "strict-required")
    # Empty tmp_path → manifest.exists FAIL (REQUIRED) → exit 1
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])
    payload = json.loads(result.stdout)
    assert any(
        f["status"] == "fail" and f["severity"] == "required"
        for f in payload["findings"]
    ), "Expected a REQUIRED FAIL finding for strict-required test"
    assert result.exit_code == 1


def test_check_legacy_no_gate_stanza_fail_exits_nonzero(tmp_path: Path) -> None:
    """Legacy (no gate): any FAIL → exit 1 (backward-compat regression guard)."""
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.5.0'\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])
    payload = json.loads(result.stdout)
    assert any(f["status"] == "fail" for f in payload["findings"])
    assert result.exit_code == 1


def test_check_legacy_no_gate_stanza_no_fail_exits_zero(tmp_path: Path) -> None:
    """Legacy (no gate): no FAIL findings → exit 0."""
    examples = Path(__file__).parent.parent / "examples" / "good_integration"
    result = runner.invoke(app, ["check", "--path", str(examples), "--format", "json"])
    payload = json.loads(result.stdout)
    assert all(f["status"] != "fail" for f in payload["findings"])
    assert result.exit_code == 0


# ---------- Phase 6: --profile flag (#146) ----------


def test_check_profile_flag_accepted(tmp_path: Path) -> None:
    """--profile cloud-service is accepted and runs without error (exit depends on findings)."""
    result = runner.invoke(
        app,
        [
            "check",
            "--path",
            str(tmp_path),
            "--profile",
            "cloud-service",
            "--format",
            "json",
        ],
    )
    # exit code can be 0 or 1 (findings); what matters is not 2 (usage error)
    assert result.exit_code in (0, 1), (
        f"Unexpected exit code: {result.exit_code}\n{result.output}"
    )
    # output is valid JSON
    payload = json.loads(result.stdout)
    findings_by_id = {f["rule_id"]: f for f in payload["findings"]}
    # cloud-service boosts config_flow.reauth_step.exists to required
    assert findings_by_id["config_flow.reauth_step.exists"]["severity"] == "required", (
        "cloud-service profile should boost config_flow.reauth_step.exists to required"
    )


def test_check_profile_flag_wins_over_config(tmp_path: Path) -> None:
    """CLI --profile overrides profile: in hasscheck.yaml."""
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.7.0'\nprofile: helper\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "check",
            "--path",
            str(tmp_path),
            "--profile",
            "cloud-service",
            "--format",
            "json",
        ],
    )
    assert result.exit_code in (0, 1)
    payload = json.loads(result.stdout)
    findings_by_id = {f["rule_id"]: f for f in payload["findings"]}
    # cloud-service boosts diagnostics.redaction.used (helper does not)
    assert findings_by_id["diagnostics.redaction.used"]["severity"] == "required", (
        "CLI --profile cloud-service should win over config profile: helper"
    )


def test_check_unknown_profile_exits_nonzero_with_error_message(tmp_path: Path) -> None:
    """--profile unknown-profile exits 1 and prints 'Unknown profile' to stderr."""
    result = runner.invoke(
        app,
        ["check", "--path", str(tmp_path), "--profile", "unknown-bogus-profile"],
    )
    assert result.exit_code == 1
    combined_output = (result.output or "") + (result.stderr or "")
    assert "Unknown profile" in combined_output or "unknown" in combined_output.lower()


# ---------- Phase 6: baseline subapp (#149) ----------


def test_baseline_subcommand_is_registered() -> None:
    """hasscheck baseline --help exits 0 and mentions the subcommands."""
    result = runner.invoke(app, ["baseline", "--help"])
    assert result.exit_code == 0
    assert "baseline" in result.output.lower()


def test_baseline_create_writes_valid_file(tmp_path: Path) -> None:
    """baseline create writes hasscheck-baseline.yaml that passes load_baseline."""
    from hasscheck.baseline import load_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    result = runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    assert result.exit_code == 0, result.output
    assert out_file.exists()
    loaded = load_baseline(out_file)
    assert loaded.hasscheck_version is not None


def test_baseline_create_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """baseline create exits 1 when file exists and --force is not passed (D5)."""
    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    # Create the file first
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    assert out_file.exists()
    # Try again without --force
    result = runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    assert result.exit_code == 1
    combined = (result.output or "") + (result.stderr or "")
    assert "update" in combined.lower() or "force" in combined.lower()


def test_baseline_create_force_overwrites(tmp_path: Path) -> None:
    """baseline create --force overwrites an existing file."""
    from hasscheck.baseline import load_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    result = runner.invoke(
        app,
        [
            "baseline",
            "create",
            "--path",
            str(tmp_path),
            "--out",
            str(out_file),
            "--force",
        ],
    )
    assert result.exit_code == 0, result.output
    loaded = load_baseline(out_file)
    assert loaded.accepted_findings is not None


def test_baseline_create_only_includes_fail_and_warn(tmp_path: Path) -> None:
    """baseline create produces entries only for FAIL and WARN findings (D6)."""
    from hasscheck.baseline import load_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    loaded = load_baseline(out_file)
    # Run a live check and verify only FAIL/WARN entries in baseline
    from hasscheck.checker import run_check
    from hasscheck.models import RuleStatus

    report = run_check(tmp_path)
    baseline_ids = {e.rule_id for e in loaded.accepted_findings}
    # All baseline entries must correspond to eligible findings
    assert baseline_ids.issubset({f.rule_id for f in report.findings}), (
        "Baseline entries should only come from actual findings"
    )
    # PASS findings must not be in baseline entries
    pass_ids = {f.rule_id for f in report.findings if f.status == RuleStatus.PASS}
    assert not baseline_ids.intersection(pass_ids), (
        "PASS findings should not appear in baseline"
    )


def test_baseline_update_preserves_reason(tmp_path: Path) -> None:
    """baseline update keeps the reason for hash-matched entries (D1)."""
    import yaml

    from hasscheck.baseline import load_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    # Create initial baseline
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    # Manually inject a reason into the first entry
    loaded = load_baseline(out_file)
    if not loaded.accepted_findings:
        pytest.skip("no findings to baseline in this integration fixture")
    raw = yaml.safe_load(out_file.read_text())
    raw["accepted_findings"][0]["reason"] = "preserved reason"
    out_file.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    # Run update
    result = runner.invoke(
        app,
        ["baseline", "update", "--path", str(tmp_path), "--file", str(out_file)],
    )
    assert result.exit_code == 0, result.output
    updated = load_baseline(out_file)
    reasons = [e.reason for e in updated.accepted_findings]
    assert "preserved reason" in reasons


def test_baseline_update_drops_stale_entries(tmp_path: Path) -> None:
    """baseline update removes entries that don't match any live finding."""
    import yaml

    from hasscheck.baseline import load_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    # Create initial baseline
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    # Inject a stale entry with a hash that no live finding can match
    raw = yaml.safe_load(out_file.read_text())
    raw["accepted_findings"].append(
        {
            "rule_id": "nonexistent.rule",
            "path": None,
            "finding_hash": "dead1234",
            "accepted_at": "2026-01-01",
            "reason": "stale",
        }
    )
    out_file.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    result = runner.invoke(
        app,
        ["baseline", "update", "--path", str(tmp_path), "--file", str(out_file)],
    )
    assert result.exit_code == 0, result.output
    updated = load_baseline(out_file)
    assert all(e.rule_id != "nonexistent.rule" for e in updated.accepted_findings)


def test_baseline_update_missing_file_errors(tmp_path: Path) -> None:
    """baseline update exits 1 when baseline file does not exist."""
    write_minimal_integration(tmp_path)
    result = runner.invoke(
        app,
        [
            "baseline",
            "update",
            "--path",
            str(tmp_path),
            "--file",
            str(tmp_path / "missing.yaml"),
        ],
    )
    assert result.exit_code == 1
    combined = (result.output or "") + (result.stderr or "")
    assert "error" in combined.lower()


def test_baseline_drop_rule_removes_all(tmp_path: Path) -> None:
    """baseline drop --rule removes all entries for that rule (D2)."""
    from hasscheck.baseline import load_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    loaded = load_baseline(out_file)
    if not loaded.accepted_findings:
        pytest.skip("no findings to drop in this integration fixture")
    target_rule = loaded.accepted_findings[0].rule_id
    result = runner.invoke(
        app,
        ["baseline", "drop", "--rule", target_rule, "--file", str(out_file)],
    )
    assert result.exit_code == 0, result.output
    updated = load_baseline(out_file)
    assert all(e.rule_id != target_rule for e in updated.accepted_findings)


def test_baseline_drop_rule_path_narrows(tmp_path: Path) -> None:
    """baseline drop --rule --path removes only that exact (rule, path) entry (D2)."""
    from datetime import UTC, date, datetime

    from hasscheck.baseline import (
        BaselineEntry,
        BaselineFile,
        load_baseline,
        write_baseline,
    )

    out_file = tmp_path / "baseline.yaml"
    entries = [
        BaselineEntry(
            rule_id="demo.rule",
            path="file_a.py",
            finding_hash="aaaa1111",
            accepted_at=date(2026, 5, 1),
        ),
        BaselineEntry(
            rule_id="demo.rule",
            path="file_b.py",
            finding_hash="bbbb2222",
            accepted_at=date(2026, 5, 1),
        ),
    ]
    bl = BaselineFile(
        generated_at=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        hasscheck_version="0.14.0",
        ruleset="test",
        accepted_findings=entries,
    )
    write_baseline(bl, out_file)
    result = runner.invoke(
        app,
        [
            "baseline",
            "drop",
            "--rule",
            "demo.rule",
            "--path",
            "file_a.py",
            "--file",
            str(out_file),
        ],
    )
    assert result.exit_code == 0, result.output
    updated = load_baseline(out_file)
    paths = [e.path for e in updated.accepted_findings]
    assert "file_a.py" not in paths
    assert "file_b.py" in paths


def test_baseline_drop_unknown_rule_errors(tmp_path: Path) -> None:
    """baseline drop exits 1 when no entries match the rule (D2 guard)."""
    from datetime import UTC, date, datetime

    from hasscheck.baseline import BaselineEntry, BaselineFile, write_baseline

    out_file = tmp_path / "baseline.yaml"
    entries = [
        BaselineEntry(
            rule_id="real.rule",
            path=None,
            finding_hash="aaaa1111",
            accepted_at=date(2026, 5, 1),
        )
    ]
    bl = BaselineFile(
        generated_at=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        hasscheck_version="0.14.0",
        ruleset="test",
        accepted_findings=entries,
    )
    write_baseline(bl, out_file)
    result = runner.invoke(
        app,
        ["baseline", "drop", "--rule", "nonexistent.rule", "--file", str(out_file)],
    )
    assert result.exit_code == 1
    combined = (result.output or "") + (result.stderr or "")
    assert "error" in combined.lower()


# ---------- Phase 7: check --baseline integration (#149) ----------


def test_check_with_baseline_round_trip_exits_zero(tmp_path: Path) -> None:
    """After `baseline create`, `check --baseline` exits 0 (all findings accepted)."""
    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    create_result = runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    assert create_result.exit_code == 0, create_result.output
    result = runner.invoke(
        app,
        [
            "check",
            "--path",
            str(tmp_path),
            "--baseline",
            str(out_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output


def test_check_with_baseline_new_finding_exits_nonzero(tmp_path: Path) -> None:
    """A new FAIL/WARN finding not in baseline causes exit 1."""
    from datetime import UTC, datetime

    from hasscheck.baseline import BaselineFile, write_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    # Write an EMPTY baseline (no accepted findings) — all findings will be new
    bl = BaselineFile(
        generated_at=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        hasscheck_version="0.14.0",
        ruleset="hasscheck-ha-2026.5",
        accepted_findings=[],
    )
    write_baseline(bl, out_file)
    result = runner.invoke(
        app,
        ["check", "--path", str(tmp_path), "--baseline", str(out_file)],
    )
    assert result.exit_code == 1, result.output


def test_check_with_baseline_corrupt_yaml_errors(tmp_path: Path) -> None:
    """check --baseline with corrupt YAML exits 1 and shows error."""
    write_minimal_integration(tmp_path)
    out_file = tmp_path / "baseline.yaml"
    out_file.write_text("{bad: yaml: :\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["check", "--path", str(tmp_path), "--baseline", str(out_file)],
    )
    assert result.exit_code == 1
    combined = (result.output or "") + (result.stderr or "")
    assert "error" in combined.lower()


def test_check_with_baseline_missing_file_errors(tmp_path: Path) -> None:
    """check --baseline with non-existent file exits 1 and shows error."""
    write_minimal_integration(tmp_path)
    result = runner.invoke(
        app,
        [
            "check",
            "--path",
            str(tmp_path),
            "--baseline",
            str(tmp_path / "missing.yaml"),
        ],
    )
    assert result.exit_code == 1
    combined = (result.output or "") + (result.stderr or "")
    assert "error" in combined.lower()


def test_check_with_baseline_accepted_label_in_terminal(tmp_path: Path) -> None:
    """Terminal output shows [accepted] for findings in the baseline."""
    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    result = runner.invoke(
        app,
        ["check", "--path", str(tmp_path), "--baseline", str(out_file)],
    )
    # At least some findings should be accepted if create worked
    assert "[accepted]" in result.output, (
        f"Expected [accepted] label in output but got:\n{result.output}"
    )


def test_check_with_baseline_new_label_in_terminal(tmp_path: Path) -> None:
    """Terminal output shows [new] for FAIL/WARN findings not in baseline."""
    from datetime import UTC, datetime

    from hasscheck.baseline import BaselineFile, write_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    # Empty baseline → all findings are [new]
    bl = BaselineFile(
        generated_at=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        hasscheck_version="0.14.0",
        ruleset="hasscheck-ha-2026.5",
        accepted_findings=[],
    )
    write_baseline(bl, out_file)
    result = runner.invoke(
        app,
        ["check", "--path", str(tmp_path), "--baseline", str(out_file)],
    )
    assert "[new]" in result.output, (
        f"Expected [new] label in output but got:\n{result.output}"
    )


def test_check_with_baseline_fixed_summary_in_terminal(tmp_path: Path) -> None:
    """Terminal output shows 'fixed since baseline' summary for stale entries."""
    from datetime import UTC, date, datetime

    from hasscheck.baseline import BaselineEntry, BaselineFile, write_baseline

    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    # Add a stale entry that won't match any live finding
    bl = BaselineFile(
        generated_at=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        hasscheck_version="0.14.0",
        ruleset="hasscheck-ha-2026.5",
        accepted_findings=[
            BaselineEntry(
                rule_id="stale.rule",
                path=None,
                finding_hash="stale000",
                accepted_at=date(2026, 5, 1),
                reason="",
            )
        ],
    )
    write_baseline(bl, out_file)
    result = runner.invoke(
        app,
        ["check", "--path", str(tmp_path), "--baseline", str(out_file)],
    )
    assert "fixed since baseline" in result.output.lower(), (
        f"Expected 'fixed since baseline' in output but got:\n{result.output}"
    )


def test_check_with_baseline_does_not_change_json_output(tmp_path: Path) -> None:
    """JSON output is identical whether or not --baseline is passed (D3)."""
    write_minimal_integration(tmp_path)
    out_file = tmp_path / "hasscheck-baseline.yaml"
    runner.invoke(
        app,
        ["baseline", "create", "--path", str(tmp_path), "--out", str(out_file)],
    )
    # JSON without baseline
    without = runner.invoke(app, ["check", "--path", str(tmp_path), "--format", "json"])
    # JSON with baseline
    with_bl = runner.invoke(
        app,
        [
            "check",
            "--path",
            str(tmp_path),
            "--format",
            "json",
            "--baseline",
            str(out_file),
        ],
    )
    payload_without = json.loads(without.stdout)
    payload_with = json.loads(with_bl.stdout)
    # The JSON structure must be identical (no extra baseline keys)
    assert payload_without["findings"] == payload_with["findings"]
    assert payload_without["summary"] == payload_with["summary"]


def test_check_no_baseline_flag_unchanged(tmp_path: Path) -> None:
    """Without --baseline, check behavior is identical to pre-baseline behavior."""
    write_minimal_integration(tmp_path)
    result_new = runner.invoke(
        app, ["check", "--path", str(tmp_path), "--format", "json"]
    )
    result_json = json.loads(result_new.stdout)
    # Must still have FAIL findings and exit 1 (no PASS for empty integration)
    assert any(f["status"] == "fail" for f in result_json["findings"])
    assert result_new.exit_code == 1


def test_check_advisory_gate_with_baseline_always_exits_zero(tmp_path: Path) -> None:
    """advisory gate mode + --baseline → always exit 0 even if new findings exist."""
    write_minimal_integration(tmp_path)
    # Create baseline with zero entries (so all findings are "new")
    baseline_path = tmp_path / "hasscheck-baseline.yaml"
    runner.invoke(app, ["baseline", "create", "--path", str(tmp_path)])
    # Clear the baseline so all findings are treated as new
    baseline_path.write_text(
        "generated_at: '2026-01-01T00:00:00'\n"
        "hasscheck_version: '0.0.0'\n"
        "ruleset: 'test'\n"
        "accepted_findings: []\n",
        encoding="utf-8",
    )
    # Write a hasscheck.yaml with advisory gate
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.7.0'\ngate:\n  mode: advisory\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app, ["check", "--path", str(tmp_path), "--baseline", str(baseline_path)]
    )
    assert result.exit_code == 0, result.output


def test_smoke_sub_command_reachable_from_root_app() -> None:
    """hasscheck smoke --help exits 0 from the root app (Group 8)."""
    result = runner.invoke(app, ["smoke", "--help"])
    assert result.exit_code == 0, result.output
    assert "run" in result.output.lower()
