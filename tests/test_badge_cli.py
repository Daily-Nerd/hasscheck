from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hasscheck.cli import app

runner = CliRunner()

EXAMPLES = Path(__file__).parent.parent / "examples"
examples_good_integration = EXAMPLES / "good_integration"
examples_partial_integration = EXAMPLES / "partial_integration"


# 1. Basic invocation — writes badges to tmp dir
def test_badge_command_writes_files(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["badge", "--path", str(examples_good_integration), "--out-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert (tmp_path / "manifest.json").exists()
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) >= 2  # at least 1 category + manifest


# 2. Exit code 0 even when check has FAILs (bad integration example)
def test_badge_command_exits_0_on_fail_findings(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "badge",
            "--path",
            str(examples_partial_integration),
            "--out-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0


# 3. --no-umbrella omits hasscheck.json
def test_badge_command_no_umbrella(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "badge",
            "--path",
            str(examples_good_integration),
            "--out-dir",
            str(tmp_path),
            "--no-umbrella",
        ],
    )
    assert result.exit_code == 0
    assert not (tmp_path / "hasscheck.json").exists()


# 4. --include filters to specific categories
def test_badge_command_include_filter(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "badge",
            "--path",
            str(examples_good_integration),
            "--out-dir",
            str(tmp_path),
            "--include",
            "hacs_structure",
            "--no-umbrella",
        ],
    )
    assert result.exit_code == 0
    json_files = [f for f in tmp_path.glob("*.json") if f.name != "manifest.json"]
    assert all("hacs_structure" in f.name for f in json_files)


# 5. Output summary line is printed
def test_badge_command_prints_summary(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["badge", "--path", str(examples_good_integration), "--out-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "badge(s) to" in result.output


# 6. --no-config flag is wired
def test_badge_command_no_config_flag(tmp_path: Path) -> None:
    (
        examples_good_integration.parent.parent / "hasscheck.yaml"
    ) if False else None  # just ensure flag exists
    result = runner.invoke(
        app,
        [
            "badge",
            "--path",
            str(examples_good_integration),
            "--out-dir",
            str(tmp_path),
            "--no-config",
        ],
    )
    assert result.exit_code == 0


# 7. Non-existent path exits 1
def test_badge_command_nonexistent_path_exits_1(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "badge",
            "--path",
            str(tmp_path / "does_not_exist"),
            "--out-dir",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 1
