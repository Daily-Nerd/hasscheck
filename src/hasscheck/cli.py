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
from hasscheck.config import ConfigError, discover_config
from hasscheck.docs_render import check_drift, render_all
from hasscheck.init import init_project
from hasscheck.models import HassCheckReport, RuleStatus
from hasscheck.output import print_terminal_report, report_to_json, report_to_md
from hasscheck.publish import (
    PublishError,
    publish_report,
    resolve_endpoint,
    resolve_oidc_token,
    split_slug,
    withdraw_report,
)
from hasscheck.rules.registry import RULES_BY_ID
from hasscheck.scaffold.cli import scaffold_app
from hasscheck.slug import detect_repo_slug

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


@app.command()
def publish(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Repository path to inspect and publish."
    ),
    to: str | None = typer.Option(
        None,
        "--to",
        help=(
            "Publish endpoint URL. Defaults to $HASSCHECK_PUBLISH_ENDPOINT or "
            "https://hasscheck.io."
        ),
    ),
    oidc_token: str | None = typer.Option(
        None,
        "--oidc-token",
        help="GitHub OIDC token. Falls back to $HASSCHECK_OIDC_TOKEN.",
    ),
    no_config: bool = typer.Option(
        False,
        "--no-config",
        help="Ignore hasscheck.yaml even if present (useful for CI debugging).",
    ),
    withdraw: bool = typer.Option(
        False,
        "--withdraw",
        help="Withdraw a single report. Requires --report-id.",
    ),
    withdraw_all: bool = typer.Option(
        False,
        "--withdraw-all",
        help="Withdraw all reports for the slug. Mutually exclusive with --withdraw.",
    ),
    report_id: str | None = typer.Option(
        None, "--report-id", help="Report ID to withdraw (with --withdraw)."
    ),
    slug: str | None = typer.Option(
        None,
        "--slug",
        help=(
            "owner/repo slug for withdrawal commands. Auto-detected from git "
            "remote when omitted."
        ),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip the withdraw confirmation prompt. Required in CI / non-TTY.",
    ),
) -> None:
    """Opt-in upload of a HassCheck report to a hosted service.

    Publishing requires a GitHub Actions OIDC token. The CLI never publishes
    by default — invoke this command explicitly or set the action input
    `emit-publish: 'true'`.

    Examples:
      hasscheck publish --path .
      hasscheck publish --path . --to https://my-host.example
      hasscheck publish --withdraw --report-id abc123
      hasscheck publish --withdraw-all
    """
    if withdraw and withdraw_all:
        typer.echo(
            "hasscheck: error: --withdraw and --withdraw-all are mutually exclusive.",
            err=True,
        )
        raise typer.Exit(code=1)

    if withdraw and report_id is None:
        typer.echo("hasscheck: error: --withdraw requires --report-id.", err=True)
        raise typer.Exit(code=1)

    if not path.exists():
        console.print(f"[red]Error:[/] Path '{path}' does not exist.")
        raise typer.Exit(code=1)

    try:
        cfg = discover_config(path.resolve())
    except ConfigError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        endpoint = resolve_endpoint(to, config=cfg)
        token = resolve_oidc_token(oidc_token)
    except PublishError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if withdraw or withdraw_all:
        resolved_slug = slug or detect_repo_slug(path.resolve())
        if resolved_slug is None:
            typer.echo(
                "hasscheck: error: could not detect repo slug; pass --slug owner/repo.",
                err=True,
            )
            raise typer.Exit(code=1)
        try:
            owner, repo = split_slug(resolved_slug)
        except PublishError as exc:
            typer.echo(f"hasscheck: error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        if not force:
            target_desc = (
                f"report {report_id}"
                if report_id
                else f"all reports for {owner}/{repo}"
            )
            typer.confirm(
                f"Withdraw {target_desc} from {endpoint}? This is irreversible and cannot be undone.",
                abort=True,
            )
        try:
            withdraw_report(
                endpoint=endpoint,
                oidc_token=token,
                owner=owner,
                repo=repo,
                report_id=report_id,
            )
        except PublishError as exc:
            typer.echo(f"hasscheck: error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        target = (
            f"report {report_id}" if report_id else f"all reports for {resolved_slug}"
        )
        typer.echo(f"Withdrew {target} from {endpoint}.")
        return

    try:
        result = publish_report(
            path,
            endpoint=endpoint,
            oidc_token=token,
            no_config=no_config,
        )
    except ConfigError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except PublishError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Published report {result.report_id} to {result.report_url}")


@app.command()
def init(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Repository path to initialize."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print would-be content; do not write."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing hasscheck.yaml / workflow."
    ),
    skip_action: bool = typer.Option(
        False,
        "--skip-action",
        help="Skip generating .github/workflows/hasscheck.yml.",
    ),
    enable_publish: bool = typer.Option(
        False,
        "--enable-publish",
        help=(
            "Scaffold a publish-aware workflow with id-token: write permission "
            "and emit-publish enabled. Use --force to overwrite an existing workflow."
        ),
    ),
) -> None:
    """Bootstrap a repository for HassCheck.

    Creates a conservative `hasscheck.yaml` and the GitHub Actions workflow.
    Refuses to overwrite existing files unless `--force` is passed.

    Examples:
      hasscheck init --path .
      hasscheck init --dry-run
      hasscheck init --skip-action
      hasscheck init --force
    """
    resolved = path.resolve()
    if not resolved.exists() or not resolved.is_dir():
        console.print(f"[red]Error:[/] Path '{path}' is not a valid directory.")
        raise typer.Exit(code=1)

    try:
        artifacts = init_project(
            resolved,
            dry_run=dry_run,
            force=force,
            skip_action=skip_action,
            enable_publish=enable_publish,
        )
    except FileExistsError as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(code=1) from exc

    if dry_run:
        return
    for artifact in artifacts:
        console.print(f"[green]Created:[/] {artifact.target}")


@app.command("docs-render")
def docs_render(
    out_dir: Path = typer.Option(Path("docs/rules"), "--out-dir"),
    check: bool = typer.Option(
        False, "--check", help="Exit non-zero if any page is stale"
    ),
) -> None:
    """Generate per-rule docs pages from RuleDefinition metadata.

    Examples:
      hasscheck docs-render
      hasscheck docs-render --out-dir docs/rules
      hasscheck docs-render --check
    """
    if check:
        drift = check_drift(out_dir)
        if drift:
            for rule_id, diff in drift.items():
                typer.echo(f"DRIFT: {rule_id}")
                typer.echo(diff)
            raise typer.Exit(1)
        typer.echo("OK: all rule docs are up to date")
    else:
        results = render_all(out_dir)
        changed = sum(1 for v in results.values() if v)
        typer.echo(f"Rendered {len(results)} pages ({changed} changed)")


app.add_typer(scaffold_app, name="scaffold")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
