"""Tests for the 'scaffold github-action' subcommand."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hasscheck.cli import app

runner = CliRunner()

GOLDEN = Path(__file__).parent / "scaffold_golden" / "github_action.yml"


def write_minimal_integration(root: Path) -> None:
    """Mirror of helper in test_cli.py."""
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": "demo"}),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# github-action subcommand
# ---------------------------------------------------------------------------


def test_github_action_dry_run_prints_template(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "uses: actions/checkout@v4" in result.output


def test_github_action_writes_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    target = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "uses: actions/checkout@v4" in content
    # Verify ${{ is rendered correctly (not $${{)
    assert "${{ matrix.python-version }}" in content
    assert "$${{" not in content


def test_github_action_output_matches_golden(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["scaffold", "github-action", "--path", str(tmp_path)],
    )

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
    assert "uses: actions/checkout@v4" in target.read_text(encoding="utf-8")


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

    assert result.exit_code == 0
    assert "hasscheck scaffold github-action" in result.output
