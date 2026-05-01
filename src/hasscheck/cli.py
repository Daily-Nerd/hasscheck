from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from hasscheck import __version__
from hasscheck.checker import run_check
from hasscheck.models import HassCheckReport
from hasscheck.output import print_terminal_report, report_to_json
from hasscheck.rules.registry import RULES_BY_ID

# CLI philosophy: developer-friendly but scriptable. Human output is explanatory;
# --json is stable and machine-readable for CI, badges, and future hosted reports.
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
    version: bool = typer.Option(False, "--version", "-V", callback=version_callback, help="Show version and exit."),
) -> None:
    """Validate Home Assistant custom integration quality signals."""


@app.command()
def check(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Repository path to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON report."),
) -> None:
    """Check a custom integration repository and print actionable findings.

    Examples:
      hasscheck check --path .
      hasscheck check --path . --json
    """
    if not path.exists():
        console.print(f"[red]Error:[/] Path '{path}' does not exist.")
        console.print("[yellow]Suggestion:[/] Pass an existing repository path with --path.")
        raise typer.Exit(code=1)

    report = run_check(path)
    if json_output:
        typer.echo(report_to_json(report), nl=False)
        return

    print_terminal_report(report, console)


@app.command()
def schema() -> None:
    """Print the v0.1 JSON schema used by HassCheck reports."""
    typer.echo(json.dumps(HassCheckReport.model_json_schema(), indent=2))


@app.command()
def explain(rule_id: str = typer.Argument(..., help="Rule ID to explain, for example manifest.domain.exists.")) -> None:
    """Explain why a rule exists, how it is sourced, and what it checks."""
    rule = RULES_BY_ID.get(rule_id)
    if rule is None:
        console.print(f"[red]Error:[/] Unknown rule '{rule_id}'.")
        console.print("[yellow]Suggestion:[/] Run 'hasscheck check --json' to see emitted rule IDs.")
        raise typer.Exit(code=1)

    console.print(f"[bold]{rule.id}[/bold]")
    console.print(f"Version: {rule.version}")
    console.print(f"Category: {rule.category}")
    console.print(f"Severity: {rule.severity.value}")
    console.print(f"Why: {rule.why}")
    console.print(f"Source: {rule.source_url}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
