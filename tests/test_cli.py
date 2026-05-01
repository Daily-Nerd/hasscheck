import json

from typer.testing import CliRunner

from hasscheck.cli import app


runner = CliRunner()


def test_check_json_outputs_report(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "0.2.0"
    assert payload["summary"]["security_review"] == "not_performed"
    assert payload["summary"]["official_ha_tier"] == "not_assigned"
    assert payload["summary"]["hacs_acceptance"] == "not_guaranteed"
    assert payload["findings"][0]["rule_id"]


def test_schema_command_outputs_json_schema() -> None:
    result = runner.invoke(app, ["schema"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["title"] == "HassCheckReport"


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

def test_no_config_flag_exists_in_help(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "--no-config" in result.stdout


def test_no_config_flag_skips_yaml(tmp_path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--json", "--no-config"])
    assert result.exit_code == 0
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
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "overrides_applied" in payload["summary"]
    assert "count" in payload["summary"]["overrides_applied"]
    assert "rule_ids" in payload["summary"]["overrides_applied"]


# ---------- Phase 6: terminal banner + JSON source field ----------

def test_json_finding_applicability_source_present(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path), "--json"])
    assert result.exit_code == 0
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
    assert result.exit_code == 0
    assert "1 override" in result.output.lower() or "override" in result.output.lower()


def test_terminal_banner_not_shown_when_no_overrides(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "override" not in result.output.lower()


def test_terminal_overridden_finding_has_config_marker(tmp_path) -> None:
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "(config)" in result.output


def test_terminal_non_overridden_finding_no_config_marker(tmp_path) -> None:
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "(config)" not in result.output
