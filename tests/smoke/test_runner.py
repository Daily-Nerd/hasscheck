"""Group 2: Tests for hasscheck.smoke.runner — subprocess boundary."""

from __future__ import annotations

import sys

import pytest

from hasscheck.smoke.errors import SmokeRunnerMissingError, SmokeTimeoutError
from hasscheck.smoke.runner import ensure_uv_available, run_command


def test_run_command_returns_returncode_stdout_stderr() -> None:
    """run_command returns (rc, stdout, stderr) for a real fast subprocess."""
    rc, stdout, stderr = run_command(
        [sys.executable, "-c", "print('ok')"],
        timeout=10.0,
    )
    assert rc == 0
    assert stdout.strip() == "ok"
    assert stderr == ""


def test_run_command_captures_stderr() -> None:
    """run_command captures stderr separately from stdout."""
    rc, stdout, stderr = run_command(
        [sys.executable, "-c", "import sys; sys.stderr.write('err\\n')"],
        timeout=10.0,
    )
    assert rc == 0
    assert stdout == ""
    assert stderr.strip() == "err"


def test_run_command_nonzero_returncode() -> None:
    """run_command returns non-zero rc without raising."""
    rc, _stdout, _stderr = run_command(
        [sys.executable, "-c", "raise SystemExit(42)"],
        timeout=10.0,
    )
    assert rc == 42


def test_run_command_raises_smoke_timeout_error(monkeypatch) -> None:
    """run_command raises SmokeTimeoutError when timeout expires."""
    import subprocess

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=0.001)

    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", fake_run)
    with pytest.raises(SmokeTimeoutError):
        run_command([sys.executable, "-c", "pass"], timeout=0.001)


def test_run_command_raises_smoke_runner_missing_error(monkeypatch) -> None:
    """run_command raises SmokeRunnerMissingError when binary not found."""

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no such file or directory")

    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", fake_run)
    with pytest.raises(SmokeRunnerMissingError):
        run_command(["nonexistent-binary-xyz", "--version"], timeout=5.0)


def test_ensure_uv_available_raises_when_uv_absent(monkeypatch) -> None:
    """ensure_uv_available raises SmokeRunnerMissingError when uv not on PATH."""
    monkeypatch.setattr("hasscheck.smoke.runner.shutil.which", lambda _: None)
    with pytest.raises(SmokeRunnerMissingError, match="uv"):
        ensure_uv_available()


def test_ensure_uv_available_passes_when_uv_present(monkeypatch) -> None:
    """ensure_uv_available does not raise when uv is on PATH."""
    monkeypatch.setattr("hasscheck.smoke.runner.shutil.which", lambda _: "/usr/bin/uv")
    ensure_uv_available()  # should not raise
