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
