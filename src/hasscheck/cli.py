from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console

from hasscheck import __version__
from hasscheck.badges import generate_badges
from hasscheck.badges.policy import BadgePolicyError
from hasscheck.checker import run_check
from hasscheck.config import ConfigError
from hasscheck.models import HassCheckReport, RuleStatus
from hasscheck.output import print_terminal_report, report_to_json, report_to_md
from hasscheck.rules.registry import RULES_BY_ID
from hasscheck.scaffold.cli import scaffold_app

# CLI philosophy: developer-friendly but scriptable. Human output is explanatory;
# --format controls output: terminal (default), json (machine-readable), or md (Markdown).


class OutputFormat(StrEnum):
    TERMINAL = "terminal"
    JSON = "json"
    MD = "md"


app = typer.Typer(
    name="hasscheck",
    help="Unofficial sourced checks for Home Assistant custom integration repos.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"hasscheck {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        help="Show version and exit.",
    ),
) -> None:
    """Validate Home Assistant custom integration quality signals."""


@app.command()
def check(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Repository path to inspect."
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TERMINAL,
        "--format",
        "-f",
        help="Output format: terminal, json, or md.",
    ),
    no_config: bool = typer.Option(
        False,
        "--no-config",
        help="Ignore hasscheck.yaml even if present (useful for CI debugging).",
    ),
) -> None:
    """Check a custom integration repository and print actionable findings.

    Reads hasscheck.yaml at the repo root if present, applying per-rule
    applicability overrides. Use --no-config to ignore.

    Examples:
      hasscheck check --path .
      hasscheck check --path . --format json
      hasscheck check --path . --format md
      hasscheck check --path . --no-config
    """
    if not path.exists():
        console.print(f"[red]Error:[/] Path '{path}' does not exist.")
        console.print(
            "[yellow]Suggestion:[/] Pass an existing repository path with --path."
        )
        raise typer.Exit(code=1)

    try:
        report = run_check(path, no_config=no_config)
    except ConfigError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if format == OutputFormat.JSON:
        typer.echo(report_to_json(report), nl=False)
    elif format == OutputFormat.MD:
        typer.echo(report_to_md(report), nl=False)
    else:
        print_terminal_report(report, console)

    if any(f.status == RuleStatus.FAIL for f in report.findings):
        raise typer.Exit(code=1)


@app.command()
def schema() -> None:
    """Print the JSON schema for HassCheck reports."""
    typer.echo(json.dumps(HassCheckReport.model_json_schema(), indent=2))


@app.command()
def explain(
    rule_id: str = typer.Argument(
        ..., help="Rule ID to explain, for example manifest.domain.exists."
    ),
) -> None:
    """Explain why a rule exists, how it is sourced, and what it checks."""
    rule = RULES_BY_ID.get(rule_id)
    if rule is None:
        console.print(f"[red]Error:[/] Unknown rule '{rule_id}'.")
        console.print(
            "[yellow]Suggestion:[/] Run 'hasscheck check --format json' to see emitted rule IDs."
        )
        raise typer.Exit(code=1)

    console.print(f"[bold]{rule.id}[/bold]")
    console.print(f"Version: {rule.version}")
    console.print(f"Category: {rule.category}")
    console.print(f"Severity: {rule.severity.value}")
    console.print(f"Overridable: {'true' if rule.overridable else 'false'}")
    console.print(f"Why: {rule.why}")
    console.print(f"Source: {rule.source_url}")


@app.command()
def badge(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Path to integration repo."
    ),
    out_dir: Path = typer.Option(
        Path("badges"), "--out-dir", help="Directory to write badge JSON files."
    ),
    include: str = typer.Option(
        "all", "--include", help="Comma-separated category IDs, or 'all'."
    ),
    no_umbrella: bool = typer.Option(
        False, "--no-umbrella", help="Omit the umbrella HassCheck badge."
    ),
    no_config: bool = typer.Option(
        False,
        "--no-config",
        help="Ignore hasscheck.yaml even if present (useful for CI debugging).",
    ),
) -> None:
    """Generate shields.io endpoint JSON badge files for a custom integration.

    Badge color reflects integration health. Exit code is always 0 even when
    checks have FAIL findings — the badge color communicates the state instead.

    Examples:
      hasscheck badge --path . --out-dir badges/
      hasscheck badge --path . --include hacs_structure,tests_ci
      hasscheck badge --path . --no-umbrella
    """
    if not path.exists():
        console.print(f"[red]Error:[/] Path '{path}' does not exist.")
        console.print(
            "[yellow]Suggestion:[/] Pass an existing repository path with --path."
        )
        raise typer.Exit(code=1)

    try:
        report = run_check(path, no_config=no_config)
    except ConfigError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    include_set: set[str] | None = None if include == "all" else set(include.split(","))

    try:
        artifacts = generate_badges(
            report,
            out_dir=out_dir,
            include=include_set,
            emit_umbrella=not no_umbrella,
        )
    except BadgePolicyError as exc:
        typer.echo(f"hasscheck: badge policy error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Wrote {len(artifacts)} badge(s) to {out_dir}")
    for a in artifacts:
        typer.echo(f"  {a.filename}: {a.label_left} — {a.label_right}")


app.add_typer(scaffold_app, name="scaffold")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
