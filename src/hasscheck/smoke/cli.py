"""Typer CLI surface for `hasscheck smoke`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

from hasscheck.models import RuleStatus
from hasscheck.output import print_terminal_report
from hasscheck.smoke.core import run_smoke
from hasscheck.smoke.errors import SmokeRunnerMissingError
from hasscheck.smoke.models import RunSmokeResult
from hasscheck.smoke.runner import ensure_uv_available

smoke_app = typer.Typer(
    name="smoke",
    help="Probe imports of an integration against one or more Home Assistant versions.",
    no_args_is_help=True,
)

console = Console()


@smoke_app.command("run")
def run(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Repository path."),
    ha_version: str | None = typer.Option(
        None,
        "--ha-version",
        help="Single HA version to probe against, e.g. 2025.4.",
    ),
    ha_version_matrix: str | None = typer.Option(
        None,
        "--ha-version-matrix",
        help="Comma-separated HA versions, e.g. 2025.4,2025.5,2025.6.",
    ),
    python: str = typer.Option(
        f"{sys.version_info.major}.{sys.version_info.minor}",
        "--python",
        help="Python version for the probe venv.",
    ),
    timeout: float = typer.Option(
        120.0,
        "--timeout",
        help="Per-version timeout in seconds.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json/--no-json",
        help="Emit JSON output instead of terminal table.",
    ),
) -> None:
    """Probe an integration against one or more HA versions using isolated venvs."""
    # XOR validation: exactly one of --ha-version / --ha-version-matrix must be set
    if (ha_version is None) == (ha_version_matrix is None):
        typer.echo(
            "hasscheck: error: pass exactly one of --ha-version or --ha-version-matrix.",
            err=True,
        )
        raise typer.Exit(code=2)

    versions = (
        [ha_version]
        if ha_version
        else [v.strip() for v in ha_version_matrix.split(",") if v.strip()]
    )

    # uv guard — must be available before we do anything
    try:
        ensure_uv_available()
    except SmokeRunnerMissingError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    results: list[RunSmokeResult] = []
    for v in versions:
        result = run_smoke(
            path,
            ha_version=v,
            python_version=python,
            timeout_s=timeout,
        )
        results.append(result)

    # Output
    if json_out:
        payload = [r.report.model_dump(mode="json") for r in results]
        typer.echo(json.dumps(payload, indent=2))
    else:
        for r in results:
            cache_hint = "(cached venv)" if r.venv_reused else "(fresh venv)"
            console.print(f"[bold]HA {r.ha_version}[/bold] {cache_hint}")
            print_terminal_report(r.report, console)

    # Exit code mapping (D5 / AD-07)
    has_fail = any(
        f.status is RuleStatus.FAIL
        for r in results
        for f in r.report.findings
        if f.rule_id != "smoke.harness.error"
    )
    has_error = any(
        f.rule_id == "smoke.harness.error" for r in results for f in r.report.findings
    )
    if has_error:
        raise typer.Exit(code=2)
    if has_fail:
        raise typer.Exit(code=1)
