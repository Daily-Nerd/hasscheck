from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from hasscheck.models import Finding, HassCheckReport, RuleStatus

_COMPAT_POLICY_FOOTER = (
    "Compatibility claims policy: "
    "https://github.com/Daily-Nerd/hasscheck/blob/main/docs/compatibility-claim-policy.md"
    " — HassCheck reports are exact-build signals."
)

_NON_PASS_STATUSES = {
    RuleStatus.WARN,
    RuleStatus.FAIL,
    RuleStatus.NOT_APPLICABLE,
    RuleStatus.MANUAL_REVIEW,
}

STATUS_ICON = {
    RuleStatus.PASS: "✅ PASS",
    RuleStatus.WARN: "⚠️ WARN",
    RuleStatus.FAIL: "❌ FAIL",
    RuleStatus.NOT_APPLICABLE: "➖ N/A",
    RuleStatus.MANUAL_REVIEW: "🔎 MANUAL",
}


def report_to_json(report: HassCheckReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2) + "\n"


def print_terminal_report(
    report: HassCheckReport, console: Console | None = None
) -> None:
    console = console or Console()
    console.print("[bold]HassCheck Summary[/bold]")
    console.print()
    for category in report.summary.categories:
        console.print(
            f"{category.label}: {category.points_awarded} / {category.points_possible}"
        )
    console.print()
    console.print("Overall: Informational only")
    console.print("Security Review: Not performed")
    console.print("Official HA Tier: Not assigned")
    console.print("HACS Acceptance: Not guaranteed")
    console.print()

    if report.summary.overrides_applied.count > 0:
        n = report.summary.overrides_applied.count
        console.print(f"[cyan]{n} override(s) applied from hasscheck.yaml.[/cyan]")
        console.print()

    if report.summary.applicability_applied.count > 0:
        n = report.summary.applicability_applied.count
        console.print(
            f"[cyan]{n} applicability decision(s) applied from hasscheck.yaml.[/cyan]"
        )
        console.print()

    table = Table(title="Findings")
    table.add_column("Status", no_wrap=True)
    table.add_column("Rule")
    table.add_column("Message")
    for finding in report.findings:
        marker = " (config)" if finding.applicability.source == "config" else ""
        table.add_row(
            STATUS_ICON[finding.status], f"{finding.rule_id}{marker}", finding.message
        )
    console.print(table)

    _print_fix_suggestions(report.findings, console)

    if report.target and report.target.ha_version:
        console.print()
        console.print(_COMPAT_POLICY_FOOTER)


def report_to_md(report: HassCheckReport) -> str:
    lines: list[str] = []

    lines.append("## HassCheck Signals")
    lines.append("")
    lines.append(f"**Project:** {report.project.path}  ")
    lines.append(f"**Domain:** {report.project.domain or 'unknown'}  ")
    lines.append(f"**Tool:** hasscheck {report.tool.version}  ")
    lines.append(f"**Ruleset:** {report.ruleset.id}")
    lines.append("")

    lines.append("### Category Summary")
    lines.append("")
    lines.append("| Category | Score | Points |")
    lines.append("|---|---|---|")
    for category in report.summary.categories:
        if category.points_awarded == category.points_possible:
            icon = "✅"
        elif category.points_awarded > 0:
            icon = "⚠️"
        else:
            icon = "❌"
        lines.append(
            f"| {category.label} | {icon} | {category.points_awarded} / {category.points_possible} |"
        )
    lines.append("")

    lines.append("### Findings")
    lines.append("")
    lines.append("| Status | Rule | Message |")
    lines.append("|---|---|---|")
    for finding in report.findings:
        marker = " *(config)*" if finding.applicability.source == "config" else ""
        lines.append(
            f"| {STATUS_ICON[finding.status]} | {finding.rule_id}{marker} | {finding.message} |"
        )
    lines.append("")

    fixable = [
        f
        for f in report.findings
        if f.status in _NON_PASS_STATUSES and f.fix is not None
    ]
    if fixable:
        lines.append("### Fix Suggestions")
        lines.append("")
        for finding in fixable:
            fix = finding.fix
            if fix is None:
                continue
            lines.append(f"**{finding.rule_id}**  ")
            lines.append(f"{fix.summary}  ")
            if fix.command is not None:
                lines.append(f"Run: `{fix.command}`  ")
            if fix.docs_url is not None:
                lines.append(f"Docs: {fix.docs_url}  ")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "> Security Review: Not performed. Official HA Tier: Not assigned. HACS Acceptance: Not guaranteed."
    )

    if report.target and report.target.ha_version:
        lines.append("")
        lines.append(_COMPAT_POLICY_FOOTER)

    return "\n".join(lines) + "\n"


def _print_fix_suggestions(findings: list[Finding], console: Console) -> None:
    fixable = [
        f for f in findings if f.status in _NON_PASS_STATUSES and f.fix is not None
    ]
    if not fixable:
        return

    console.print()
    console.print("[bold]Fix suggestions[/bold]")
    for finding in fixable:
        fix = finding.fix
        if fix is None:
            continue
        console.print(f"  [bold]{finding.rule_id}[/bold]")
        console.print(f"    {fix.summary}")
        if fix.command is not None:
            console.print(f"    Run: {fix.command}")
        if fix.docs_url is not None:
            console.print(f"    Docs: {fix.docs_url}")
