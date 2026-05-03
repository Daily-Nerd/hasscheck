"""`hasscheck baseline` subapp — create, update, drop."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import typer
from rich.console import Console

from hasscheck import __version__
from hasscheck.baseline.core import (
    BaselineError,
    baseline_from_findings,
    drop_from_baseline,
    load_baseline,
    merge_baseline,
    write_baseline,
)
from hasscheck.checker import run_check
from hasscheck.config import ConfigError, discover_config

baseline_app = typer.Typer(
    name="baseline",
    help="Manage the baseline file (accepted pre-existing findings).",
    no_args_is_help=True,
)

console = Console()

_DEFAULT_BASELINE_PATH = Path("hasscheck-baseline.yaml")


def _now_today() -> tuple[datetime, date]:
    now = datetime.now(UTC)
    return now, now.date()


def _run_check_or_exit(project_path: Path) -> object:  # returns HassCheckReport
    try:
        cfg = discover_config(project_path.resolve())
    except ConfigError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    try:
        return run_check(project_path, config=cfg)
    except (ConfigError, ValueError) as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@baseline_app.command("create")
def create(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Repository path to inspect."
    ),
    out: Path = typer.Option(
        _DEFAULT_BASELINE_PATH,
        "--out",
        "-o",
        help="Baseline file path (default: hasscheck-baseline.yaml).",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing baseline file (D5)."
    ),
) -> None:
    """Snapshot current FAIL/WARN findings into a baseline file (D5, D6)."""
    if out.exists() and not force:
        typer.echo(
            f"hasscheck: error: {out} already exists. "
            f"Use `hasscheck baseline update` to merge new findings, "
            f"or pass --force to overwrite.",
            err=True,
        )
        raise typer.Exit(code=1)

    if not path.exists():
        typer.echo(f"hasscheck: error: path '{path}' does not exist.", err=True)
        raise typer.Exit(code=1)

    report = _run_check_or_exit(path)
    now, today = _now_today()
    baseline = baseline_from_findings(
        report.findings,  # type: ignore[arg-type]
        hasscheck_version=__version__,
        ruleset=report.ruleset.id,  # type: ignore[union-attr]
        now=now,
        today=today,
    )
    write_baseline(baseline, out)
    console.print(
        f"[green]Created:[/] {out} ({len(baseline.accepted_findings)} accepted finding(s))"
    )


@baseline_app.command("update")
def update(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Repository path to inspect."
    ),
    file: Path = typer.Option(
        _DEFAULT_BASELINE_PATH,
        "--file",
        "-f",
        help="Baseline file path (default: hasscheck-baseline.yaml).",
    ),
) -> None:
    """Merge current findings into an existing baseline (D1).

    Preserves `reason` and `accepted_at` for entries that still match a live
    FAIL/WARN finding by hash. Drops stale entries. Adds new findings with
    empty reason and today's date.
    """
    if not path.exists():
        typer.echo(f"hasscheck: error: path '{path}' does not exist.", err=True)
        raise typer.Exit(code=1)

    try:
        existing = load_baseline(file)
    except BaselineError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    report = _run_check_or_exit(path)
    now, today = _now_today()
    merged = merge_baseline(
        existing,
        report.findings,  # type: ignore[arg-type]
        hasscheck_version=__version__,
        ruleset=report.ruleset.id,  # type: ignore[union-attr]
        now=now,
        today=today,
    )
    write_baseline(merged, file)
    console.print(
        f"[green]Updated:[/] {file} ({len(merged.accepted_findings)} accepted finding(s))"
    )


@baseline_app.command("drop")
def drop(
    rule: str = typer.Option(..., "--rule", help="Rule ID to remove (D2)."),
    path: str | None = typer.Option(
        None,
        "--path",
        help=(
            "Optional path to narrow removal to a single (rule_id, path) entry. "
            "Without --path, ALL entries for --rule are removed."
        ),
    ),
    file: Path = typer.Option(
        _DEFAULT_BASELINE_PATH,
        "--file",
        "-f",
        help="Baseline file path (default: hasscheck-baseline.yaml).",
    ),
) -> None:
    """Remove baseline entries by rule_id (and optionally path).

    NOTE: The `--path` flag here narrows the deletion within the baseline file.
    It is NOT the project path; `drop` only edits the file, it does not run checks.
    """
    try:
        existing = load_baseline(file)
    except BaselineError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    now, _ = _now_today()
    try:
        new_baseline, removed = drop_from_baseline(
            existing, rule_id=rule, path=path, now=now
        )
    except BaselineError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    write_baseline(new_baseline, file)
    scope = f"--rule {rule}" + (f" --path {path}" if path is not None else "")
    console.print(f"[green]Dropped[/] {removed} entry/ies ({scope}) from {file}")
