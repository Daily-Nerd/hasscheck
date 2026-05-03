"""Subprocess boundary for the smoke harness.

All subprocess.run calls in the smoke package go through run_command().
Monkeypatch hasscheck.smoke.runner.subprocess.run to intercept them in tests.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hasscheck.smoke.errors import SmokeRunnerMissingError, SmokeTimeoutError


def run_command(
    cmd: list[str],
    *,
    timeout: float,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run *cmd*; return ``(returncode, stdout, stderr)``.

    Raises:
        SmokeTimeoutError: if the subprocess exceeds *timeout* seconds.
        SmokeRunnerMissingError: if *cmd[0]* binary is not found.

    Never raises ``CalledProcessError`` — the caller inspects ``returncode``.
    """
    try:
        completed = subprocess.run(  # noqa: S603 — cmd is constructed internally
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SmokeTimeoutError(
            f"command timed out after {timeout}s: {' '.join(cmd)}"
        ) from exc
    except FileNotFoundError as exc:
        raise SmokeRunnerMissingError(f"binary not found: {cmd[0]}") from exc
    return completed.returncode, completed.stdout, completed.stderr


def ensure_uv_available() -> None:
    """Raise ``SmokeRunnerMissingError`` with actionable hint if ``uv`` is not on PATH."""
    if shutil.which("uv") is None:
        raise SmokeRunnerMissingError(
            "`uv` binary not found on PATH. "
            "Install: https://docs.astral.sh/uv/getting-started/installation/"
        )
