"""Group 7: Tests for hasscheck.smoke.cli — Typer CLI surface.

Note on invocation: smoke_app has a single command 'run'. When a Typer app
has exactly one command registered, CliRunner exposes that command's options
at the top level (i.e. invoke smoke_app without the 'run' subcommand word).
For the root CLI tests (Group 8) we use `app` and include "smoke run".
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from hasscheck.smoke.cli import smoke_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_integration(tmp_path: Path) -> Path:
    """Create a minimal integration structure."""
    integration = tmp_path / "custom_components" / "foo"
    integration.mkdir(parents=True)
    (integration / "__init__.py").write_text("", encoding="utf-8")
    manifest = {
        "domain": "foo",
        "name": "Foo",
        "documentation": "https://example.com",
        "issue_tracker": "https://example.com/issues",
        "codeowners": ["@foo"],
        "version": "0.1.0",
        "requirements": [],
    }
    (integration / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def _fake_run_success(*args, **kwargs):
    """subprocess.run fake returning success (rc=0)."""
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    m.stderr = ""
    return m


# ---------------------------------------------------------------------------
# Task 7.1 — help, XOR validation, uv guard
# ---------------------------------------------------------------------------


def test_smoke_help_exits_0() -> None:
    """hasscheck smoke --help exits 0."""
    result = runner.invoke(smoke_app, ["--help"])
    assert result.exit_code == 0


def test_smoke_run_help_mentions_run() -> None:
    """smoke app help output mentions 'run' (as the command name or option)."""
    result = runner.invoke(smoke_app, ["--help"])
    assert result.exit_code == 0
    # 'run' appears in the Usage line or option descriptions
    assert "run" in result.output.lower()


def test_smoke_missing_both_version_flags_exits_2(tmp_path) -> None:
    """Missing both --ha-version and --ha-version-matrix exits 2."""
    result = runner.invoke(smoke_app, ["--path", str(tmp_path)])
    assert result.exit_code == 2


def test_smoke_both_version_flags_simultaneously_exits_2(tmp_path) -> None:
    """Providing both --ha-version and --ha-version-matrix simultaneously exits 2."""
    result = runner.invoke(
        smoke_app,
        [
            "--path",
            str(tmp_path),
            "--ha-version",
            "2025.4",
            "--ha-version-matrix",
            "2025.4,2025.5",
        ],
    )
    assert result.exit_code == 2


def test_smoke_uv_absent_exits_2_with_uv_in_output(monkeypatch, tmp_path) -> None:
    """uv absent from PATH → exit 2 AND output contains 'uv' (S4)."""
    monkeypatch.setattr("hasscheck.smoke.runner.shutil.which", lambda _: None)
    result = runner.invoke(
        smoke_app,
        ["--path", str(tmp_path), "--ha-version", "2025.4"],
    )
    assert result.exit_code == 2
    assert "uv" in result.output


# ---------------------------------------------------------------------------
# Task 7.3 — exit codes
# ---------------------------------------------------------------------------


def test_smoke_all_pass_findings_exits_0(monkeypatch, tmp_path) -> None:
    """All PASS findings → exit code 0."""
    repo = _make_integration(tmp_path)
    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", _fake_run_success)

    result = runner.invoke(
        smoke_app,
        ["--path", str(repo), "--ha-version", "2025.4"],
    )
    assert result.exit_code == 0


def test_smoke_fail_finding_exits_1(monkeypatch, tmp_path) -> None:
    """At least one FAIL finding → exit code 1."""
    repo = _make_integration(tmp_path)

    def fake_run_fail(*args, **kwargs):
        m = MagicMock()
        cmd = args[0]
        if "pip" in cmd or "venv" in cmd:
            m.returncode = 0
            m.stdout = ""
            m.stderr = ""
        else:
            m.returncode = 1
            m.stdout = ""
            m.stderr = "ImportError: No module named 'homeassistant'"
        return m

    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", fake_run_fail)

    result = runner.invoke(
        smoke_app,
        ["--path", str(repo), "--ha-version", "2025.4"],
    )
    assert result.exit_code == 1


def test_smoke_harness_error_finding_exits_2(monkeypatch, tmp_path) -> None:
    """Harness error finding (smoke.harness.error) → exit code 2."""
    repo = _make_integration(tmp_path)
    import subprocess

    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=0.001)

    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", timeout_run)

    result = runner.invoke(
        smoke_app,
        ["--path", str(repo), "--ha-version", "2025.4"],
    )
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Task 7.5 — --json output
# ---------------------------------------------------------------------------


def test_smoke_json_single_version_stdout_is_valid_json(monkeypatch, tmp_path) -> None:
    """--json with one version → stdout is valid JSON (S7)."""
    repo = _make_integration(tmp_path)
    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", _fake_run_success)

    result = runner.invoke(
        smoke_app,
        ["--path", str(repo), "--ha-version", "2025.4", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) == 1


def test_smoke_json_matrix_stdout_is_valid_json_array(monkeypatch, tmp_path) -> None:
    """--json with matrix of 2 versions → stdout is valid JSON array (S7)."""
    repo = _make_integration(tmp_path)
    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", _fake_run_success)

    result = runner.invoke(
        smoke_app,
        [
            "--path",
            str(repo),
            "--ha-version-matrix",
            "2025.4,2025.5",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) == 2
