from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from hasscheck import __version__
from hasscheck.badges import generate_badges
from hasscheck.badges.policy import BadgePolicyError
from hasscheck.baseline import (
    BaselineError,
    FindingPartition,
    load_baseline,
    partition_findings,
)
from hasscheck.baseline.cli import baseline_app
from hasscheck.checker import run_check
from hasscheck.config import ConfigError, GateConfig, GateMode, discover_config
from hasscheck.diff import _load_report, compute_delta, delta_to_md
from hasscheck.docs_render import check_drift, render_all
from hasscheck.init import init_project
from hasscheck.inventory import InventoryResult, run_inventory
from hasscheck.models import Finding, HassCheckReport, RuleSeverity, RuleStatus
from hasscheck.output import print_terminal_report, report_to_json, report_to_md
from hasscheck.publish import (
    PublishError,
    detect_oidc_token,
    publish_report,
    resolve_endpoint,
    resolve_endpoint_with_source,
    resolve_oidc_token,
    split_slug,
    withdraw_report,
)
from hasscheck.rules.registry import RULES_BY_ID
from hasscheck.scaffold.cli import scaffold_app
from hasscheck.slug import detect_repo_slug
from hasscheck.smoke.cli import smoke_app

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


def should_exit_nonzero(findings: list[Finding], gate: GateConfig | None) -> bool:
    """Determine whether the CLI should exit non-zero based on findings and gate config.

    When gate is None, uses legacy behavior: exits non-zero on any FAIL finding.
    When gate is set, applies the gate mode policy to decide the exit signal.
    The gate trigger threshold is ``status in {FAIL, WARN}`` for all named modes.

    There is no ``case _`` in the match — a missing branch would be a bug, not a
    runtime fallback. Python will raise ``ValueError`` on an unhandled StrEnum value.
    """
    if gate is None:
        return any(f.status == RuleStatus.FAIL for f in findings)

    triggered = {RuleStatus.FAIL, RuleStatus.WARN}
    match gate.mode:
        case GateMode.ADVISORY:
            return False
        case GateMode.STRICT_REQUIRED:
            return any(
                f.severity == RuleSeverity.REQUIRED and f.status in triggered
                for f in findings
            )
        case GateMode.HACS_PUBLISH:
            # TODO(hacs-tags): refine once rules carry tags=("hacs",)
            return any(
                f.severity in {RuleSeverity.REQUIRED, RuleSeverity.RECOMMENDED}
                and f.status in triggered
                for f in findings
            )
        case GateMode.UPGRADE_RADAR:
            return any(
                f.rule_id.startswith("version.") and f.status in triggered
                for f in findings
            )


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
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-P",
            help=(
                "Apply a built-in quality profile: cloud-service, local-device, "
                "hub, helper, read-only-sensor, core-submission-candidate. "
                "Wins over `profile:` in hasscheck.yaml."
            ),
        ),
    ] = None,
    baseline: Annotated[
        Path | None,
        typer.Option(
            "--baseline",
            "-b",
            help=(
                "Path to a baseline file. Findings matching the baseline are "
                "labeled [accepted] and excluded from the gate. New findings "
                "trigger the gate; resolved findings show as [fixed]. "
                "Generate one with `hasscheck baseline create`."
            ),
        ),
    ] = None,
) -> None:
    """Check a custom integration repository and print actionable findings.

    Reads hasscheck.yaml at the repo root if present, applying per-rule
    applicability overrides. Use --no-config to ignore.

    Examples:
      hasscheck check --path .
      hasscheck check --path . --format json
      hasscheck check --path . --format md
      hasscheck check --path . --no-config
      hasscheck check --path . --profile cloud-service
    """
    if not path.exists():
        console.print(f"[red]Error:[/] Path '{path}' does not exist.")
        console.print(
            "[yellow]Suggestion:[/] Pass an existing repository path with --path."
        )
        raise typer.Exit(code=1)

    # Hoist discover_config to resolve effective_profile before run_check.
    # D5: CLI --profile wins over config profile:.
    try:
        cfg = discover_config(path.resolve()) if not no_config else None
    except ConfigError as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    effective_profile = profile or (cfg.profile if cfg else None)

    try:
        report = run_check(
            path,
            config=cfg,
            no_config=no_config,
            profile_name=effective_profile,
        )
    except (ConfigError, ValueError) as exc:
        typer.echo(f"hasscheck: error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Baseline partition (no-op when --baseline omitted).
    bl_partition: FindingPartition | None = None
    if baseline is not None:
        try:
            baseline_file = load_baseline(baseline)
        except BaselineError as exc:
            typer.echo(f"hasscheck: error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        bl_partition = partition_findings(report.findings, baseline_file)

    if format == OutputFormat.JSON:
        typer.echo(report_to_json(report), nl=False)  # D3 — JSON unchanged
    elif format == OutputFormat.MD:
        typer.echo(report_to_md(report), nl=False)  # D4 — MD unchanged
    else:
        print_terminal_report(report, console, partition=bl_partition)

    # Gate decision: gate on new findings only when a baseline is active.
    gate_findings = bl_partition.new if bl_partition is not None else report.findings
    _gate = cfg.gate if cfg else None
    if should_exit_nonzero(gate_findings, _gate):
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

    Generated files are LOCAL PREVIEW ONLY — they are self-reported and
    cannot be independently verified by consumers. At v1.0, hub-verified
    badge URLs (generated server-side from an OIDC-authenticated report)
    should be used in README embeds instead of committed local JSON files.

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
def inventory(
    ha_config: Path = typer.Argument(
        ...,
        help=(
            "Path to a Home Assistant configuration directory "
            "(the one containing custom_components/)."
        ),
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.TERMINAL,
        "--format",
        help="Output format: terminal (default) or json.",
        case_sensitive=False,
    ),
    ha_version: str | None = typer.Option(
        None,
        "--ha-version",
        help=(
            "Home Assistant core version to evaluate compatibility against "
            "(e.g. 2026.5.0). Forwarded to every per-integration check."
        ),
    ),
    no_config: bool = typer.Option(
        False,
        "--no-config",
        help="Ignore hasscheck.yaml even if present in any integration.",
    ),
) -> None:
    """Scan all custom integrations under a Home Assistant config dir.

    Walks <ha_config>/custom_components/, runs the full ruleset on every
    integration that has a manifest.json, and emits a consolidated report.

    Exit codes:
      0 — every integration passed (no FAIL findings).
      1 — at least one integration has a FAIL finding or failed to scan.
      2 — argument error (missing dir, etc.) [Typer default].
    """
    if not ha_config.exists():
        typer.echo(
            f"hasscheck: error: ha_config path does not exist: {ha_config}",
            err=True,
        )
        raise typer.Exit(code=2)
    if not ha_config.is_dir():
        typer.echo(
            f"hasscheck: error: ha_config must be a directory: {ha_config}",
            err=True,
        )
        raise typer.Exit(code=2)
    if not (ha_config / "custom_components").is_dir():
        typer.echo(
            f"hasscheck: warning: no custom_components/ directory found at {ha_config}",
            err=True,
        )
        raise typer.Exit(code=0)

    if format is OutputFormat.MD:
        typer.echo(
            "hasscheck: error: --format md is not supported for inventory.",
            err=True,
        )
        raise typer.Exit(code=2)

    result = run_inventory(
        ha_config,
        ha_version=ha_version,
        no_config=no_config,
    )

    if format is OutputFormat.JSON:
        typer.echo(json.dumps(result.to_json_dict(), indent=2))
    else:
        _print_inventory_terminal(result)

    raise typer.Exit(code=result.exit_code)


def _print_inventory_terminal(result: InventoryResult) -> None:
    """Render a one-row-per-integration table to the shared `console`.

    Reuses the module-level rich.Console (already instantiated at module scope).
    No new dependency — rich.table.Table is in the same package as Console.
    """
    from rich.table import Table

    table = Table(title=f"HassCheck Inventory — {result.ha_config}")
    table.add_column("Domain", style="bold")
    table.add_column("Version")
    table.add_column("FAIL", justify="right", style="red")
    table.add_column("WARN", justify="right", style="yellow")
    table.add_column("Status")

    for entry in result.entries:
        if not entry.ok:
            table.add_row(
                entry.domain, "—", "—", "—", f"[red]ERROR[/red] {entry.error}"
            )
            continue
        report = entry.report
        fails = sum(1 for f in report.findings if f.status is RuleStatus.FAIL)
        warns = sum(1 for f in report.findings if f.status is RuleStatus.WARN)
        status = (
            "[red]FAIL[/red]"
            if fails
            else "[yellow]WARN[/yellow]"
            if warns
            else "[green]PASS[/green]"
        )
        version = report.project.integration_version or "—"
        table.add_row(entry.domain, version, str(fails), str(warns), status)

    console.print(table)
    s = result.summary
    console.print(
        f"\n{s.total} integration(s) scanned: "
        f"[green]{s.passed} pass[/green], "
        f"[yellow]{s.warned} warn[/yellow], "
        f"[red]{s.failed} fail[/red]"
    )


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
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate and preview without making any network request.",
    ),
    ha_version: str | None = typer.Option(
        None,
        "--ha-version",
        help=(
            "Home Assistant core version this report was tested against "
            "(e.g. 2026.5.0). No format validation. Propagated to the published report."
        ),
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
      hasscheck publish --path . --dry-run
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

    if dry_run:
        endpoint, endpoint_source = resolve_endpoint_with_source(to, config=cfg)
        _, token_status = detect_oidc_token(oidc_token)

        if withdraw or withdraw_all:
            resolved_slug = slug or detect_repo_slug(path.resolve())
            if resolved_slug is None:
                typer.echo(
                    "hasscheck: error: could not detect repo slug; pass --slug owner/repo.",
                    err=True,
                )
                raise typer.Exit(code=1)
            target_desc = (
                f"report {report_id}"
                if report_id
                else f"all reports for {resolved_slug}"
            )
            typer.echo(f"would withdraw {target_desc} from: {endpoint}")
            typer.echo(f"  - endpoint resolved from: {endpoint_source}")
            typer.echo(f"  - oidc token: {token_status}")
            typer.echo("  - dry-run: no network request made")
            return

        try:
            report = run_check(path, config=cfg, no_config=no_config)
        except ConfigError as exc:
            typer.echo(f"hasscheck: error: {exc}", err=True)
            raise typer.Exit(code=1) from exc

        detected_slug = (
            slug or detect_repo_slug(path.resolve()) or "unknown (pass --slug)"
        )
        actionable = sum(
            1
            for f in report.findings
            if f.status not in (RuleStatus.PASS, RuleStatus.NOT_APPLICABLE)
        )
        typer.echo(f"would publish report to: {endpoint}")
        typer.echo(f"  - repo slug: {detected_slug}")
        typer.echo(f"  - schema_version: {report.schema_version}")
        typer.echo(f"  - ruleset: {report.ruleset.id}")
        typer.echo(f"  - {len(report.findings)} rules evaluated, {actionable} findings")
        typer.echo(f"  - oidc token: {token_status}")
        typer.echo(f"  - endpoint resolved from: {endpoint_source}")
        typer.echo("  - dry-run: no network request made")
        return

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
            ha_version=ha_version,
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


@app.command("diff")
def diff_cmd(
    base_json: Path = typer.Argument(..., help="Base branch report JSON"),
    head_json: Path = typer.Argument(..., help="PR HEAD report JSON"),
    format: str = typer.Option(
        "md", "--format", "-f", help="Output format: md or json"
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout"
    ),
) -> None:
    """Compare two HassCheck JSON reports and show new / fixed findings.

    BASE_JSON is the report from the base branch; HEAD_JSON is the report from
    the PR HEAD. Exits 0 when no new findings are introduced, 1 when new
    findings exist, and 2 on read/parse error.

    Examples:
      hasscheck diff base.json head.json
      hasscheck diff base.json head.json --format json
      hasscheck diff base.json head.json --output delta.md
    """
    try:
        base_report = _load_report(base_json)
    except FileNotFoundError as exc:
        typer.echo(f"hasscheck diff: file not found: {base_json}", err=True)
        raise typer.Exit(code=2) from exc
    except ValueError as exc:
        typer.echo(f"hasscheck diff: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    try:
        head_report = _load_report(head_json)
    except FileNotFoundError as exc:
        typer.echo(f"hasscheck diff: file not found: {head_json}", err=True)
        raise typer.Exit(code=2) from exc
    except ValueError as exc:
        typer.echo(f"hasscheck diff: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    delta = compute_delta(base_report, head_report)

    if format == "json":
        payload = {
            "new": [f.model_dump(mode="json") for f in delta.new],
            "fixed": [f.model_dump(mode="json") for f in delta.fixed],
            "unchanged": [f.model_dump(mode="json") for f in delta.unchanged],
        }
        rendered = json.dumps(payload, indent=2)
    else:
        rendered = delta_to_md(delta)

    if output is not None:
        output.write_text(rendered, encoding="utf-8")
    else:
        typer.echo(rendered, nl=False)

    if delta.new:
        raise typer.Exit(code=1)


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
app.add_typer(baseline_app, name="baseline")
app.add_typer(smoke_app, name="smoke")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
