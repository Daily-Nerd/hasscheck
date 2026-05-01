"""Tests for the scaffold github-action, diagnostics, and repairs subcommands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hasscheck.cli import app

runner = CliRunner()

GOLDEN = Path(__file__).parent / "scaffold_golden" / "github_action.yml"
DIAGNOSTICS_GOLDEN = Path(__file__).parent / "scaffold_golden" / "diagnostics.py"
REPAIRS_GOLDEN = Path(__file__).parent / "scaffold_golden" / "repairs.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_minimal_integration_for_scaffold(root: Path, domain: str = "demo") -> Path:
    integration = root / "custom_components" / domain
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": domain, "name": "Demo"}), encoding="utf-8"
    )
    return integration


# ---------------------------------------------------------------------------
# github-action subcommand
# ---------------------------------------------------------------------------


def test_github_action_dry_run_prints_template(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "uses: actions/checkout@v6" in result.output


def test_github_action_writes_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    target = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "uses: actions/checkout@v6" in content
    # Verify ${{ is rendered correctly (not $${{)
    assert "${{ matrix.python-version }}" in content
    assert "$${{" not in content


def test_github_action_output_matches_golden(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    target = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    assert target.read_text(encoding="utf-8") == GOLDEN.read_text(encoding="utf-8")


def test_github_action_refuses_if_file_exists(tmp_path: Path) -> None:
    target = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    target.parent.mkdir(parents=True)
    target.write_text("existing content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "--force" in result.output or "--force" in (result.stderr or "")


def test_github_action_force_overwrites(tmp_path: Path) -> None:
    target = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    target.parent.mkdir(parents=True)
    target.write_text("old content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path), "--force"],
    )

    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8") != "old content"
    assert "uses: actions/checkout@v6" in target.read_text(encoding="utf-8")


def test_github_action_path_not_found(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist"

    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(nonexistent)],
    )

    assert result.exit_code != 0


def test_check_command_shows_scaffold_hint_for_missing_workflow(
    tmp_path: Path,
) -> None:
    """ci.github_actions.exists WARN fix command should reference scaffold hint."""
    # tmp_path has no .github/ directory so ci.github_actions.exists → WARN
    result = runner.invoke(app, ["check", "--path", str(tmp_path)])

    assert result.exit_code == 1
    assert "hasscheck scaffold github-action" in result.output


# ---------------------------------------------------------------------------
# diagnostics subcommand
# ---------------------------------------------------------------------------


def test_diagnostics_dry_run_prints_template(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(tmp_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "async_get_config_entry_diagnostics" in result.output


def test_diagnostics_writes_file(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    target = tmp_path / "custom_components" / "demo" / "diagnostics.py"
    assert target.exists()


def test_diagnostics_output_matches_golden(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    target = tmp_path / "custom_components" / "demo" / "diagnostics.py"
    assert target.read_text(encoding="utf-8") == DIAGNOSTICS_GOLDEN.read_text(
        encoding="utf-8"
    )


def test_diagnostics_refuses_if_file_exists(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    target = tmp_path / "custom_components" / "demo" / "diagnostics.py"
    target.write_text("existing content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "--force" in result.output


def test_diagnostics_force_overwrites(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    target = tmp_path / "custom_components" / "demo" / "diagnostics.py"
    target.write_text("old content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(tmp_path), "--force"],
    )

    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8") != "old content"
    assert "async_get_config_entry_diagnostics" in target.read_text(encoding="utf-8")


def test_diagnostics_applicability_gate_fires(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\napplicability:\n  supports_diagnostics: false\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "Warning" in result.output or "warning" in result.output.lower()


def test_diagnostics_force_bypasses_gate(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\napplicability:\n  supports_diagnostics: false\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(tmp_path), "--force"],
    )

    assert result.exit_code == 0
    target = tmp_path / "custom_components" / "demo" / "diagnostics.py"
    assert target.exists()


def test_diagnostics_path_not_found(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist"

    result = runner.invoke(
        app,
        ["scaffold", "diagnostics", "--path", str(nonexistent)],
    )

    assert result.exit_code != 0


def test_check_command_shows_diagnostics_scaffold_hint(tmp_path: Path) -> None:
    """diagnostics.file.exists WARN fix command should reference scaffold hint."""
    # Create a minimal integration without diagnostics.py → WARN
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(app, ["check", "--path", str(tmp_path)])

    assert result.exit_code == 1
    assert "hasscheck scaffold diagnostics" in result.output


# ---------------------------------------------------------------------------
# repairs subcommand
# ---------------------------------------------------------------------------


def test_repairs_dry_run_prints_template(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(tmp_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "async_create_fix_flow" in result.output


def test_repairs_writes_file(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    target = tmp_path / "custom_components" / "demo" / "repairs.py"
    assert target.exists()


def test_repairs_output_matches_golden(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    target = tmp_path / "custom_components" / "demo" / "repairs.py"
    assert target.read_text(encoding="utf-8") == REPAIRS_GOLDEN.read_text(
        encoding="utf-8"
    )


def test_repairs_refuses_if_file_exists(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    target = tmp_path / "custom_components" / "demo" / "repairs.py"
    target.write_text("existing content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "--force" in result.output


def test_repairs_force_overwrites(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    target = tmp_path / "custom_components" / "demo" / "repairs.py"
    target.write_text("old content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(tmp_path), "--force"],
    )

    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8") != "old content"
    assert "async_create_fix_flow" in target.read_text(encoding="utf-8")


def test_repairs_applicability_gate_fires(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\napplicability:\n  has_user_fixable_repairs: false\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "Warning" in result.output or "warning" in result.output.lower()


def test_repairs_force_bypasses_gate(tmp_path: Path) -> None:
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")
    (tmp_path / "hasscheck.yaml").write_text(
        "schema_version: '0.3.0'\napplicability:\n  has_user_fixable_repairs: false\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(tmp_path), "--force"],
    )

    assert result.exit_code == 0
    target = tmp_path / "custom_components" / "demo" / "repairs.py"
    assert target.exists()


def test_repairs_path_not_found(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist"

    result = runner.invoke(
        app,
        ["scaffold", "repairs", "--path", str(nonexistent)],
    )

    assert result.exit_code != 0


def test_check_command_shows_repairs_scaffold_hint(tmp_path: Path) -> None:
    """repairs.file.exists WARN fix command should reference scaffold hint."""
    write_minimal_integration_for_scaffold(tmp_path, domain="demo")

    result = runner.invoke(app, ["check", "--path", str(tmp_path)])

    assert result.exit_code == 1
    assert "hasscheck scaffold repairs" in result.output
