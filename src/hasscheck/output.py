from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from hasscheck.models import HassCheckReport, RuleStatus

STATUS_ICON = {
    RuleStatus.PASS: "✅ PASS",
    RuleStatus.WARN: "⚠️ WARN",
    RuleStatus.FAIL: "❌ FAIL",
    RuleStatus.NOT_APPLICABLE: "➖ N/A",
    RuleStatus.MANUAL_REVIEW: "🔎 MANUAL",
}


def report_to_json(report: HassCheckReport) -> str:
    return json.dumps(report.to_json_dict(), indent=2) + "\n"


def print_terminal_report(report: HassCheckReport, console: Console | None = None) -> None:
    console = console or Console()
    console.print("[bold]HassCheck Summary[/bold]")
    console.print()
    for category in report.summary.categories:
        console.print(f"{category.label}: {category.points_awarded} / {category.points_possible}")
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

    table = Table(title="Findings")
    table.add_column("Status", no_wrap=True)
    table.add_column("Rule")
    table.add_column("Message")
    for finding in report.findings:
        table.add_row(STATUS_ICON[finding.status], finding.rule_id, finding.message)
    console.print(table)
