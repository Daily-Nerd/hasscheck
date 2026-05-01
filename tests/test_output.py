from __future__ import annotations

from io import StringIO

from rich.console import Console

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    FixSuggestion,
    HassCheckReport,
    ProjectInfo,
    ReportSummary,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.output import print_terminal_report


def make_finding(
    status: RuleStatus,
    fix: FixSuggestion | None = None,
    rule_id: str = "test.rule",
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category="test",
        status=status,
        severity=RuleSeverity.RECOMMENDED,
        title="Test Rule",
        message="Test message",
        applicability=Applicability(
            status=ApplicabilityStatus.APPLICABLE, reason="applicable"
        ),
        source=RuleSource(url="https://example.com"),
        fix=fix,
    )


def make_report(findings: list[Finding]) -> HassCheckReport:
    return HassCheckReport(
        project=ProjectInfo(path="."),
        summary=ReportSummary(),
        findings=findings,
    )


def capture_output(report: HassCheckReport) -> str:
    sio = StringIO()
    console = Console(file=sio, no_color=True, highlight=False)
    print_terminal_report(report, console)
    return sio.getvalue()


def test_fix_section_shown_for_warn_finding_with_fix() -> None:
    fix = FixSuggestion(
        summary="Add diagnostics.py with redaction for sensitive values.",
        command="hasscheck scaffold diagnostics",
    )
    report = make_report(
        [make_finding(RuleStatus.WARN, fix=fix, rule_id="diagnostics.file.exists")]
    )
    output = capture_output(report)

    assert "Fix suggestions" in output
    assert "diagnostics.file.exists" in output
    assert "Add diagnostics.py with redaction for sensitive values." in output
    assert "Run: hasscheck scaffold diagnostics" in output


def test_fix_section_shown_for_fail_finding_with_fix() -> None:
    fix = FixSuggestion(
        summary="Create the missing file.",
        command="hasscheck scaffold missing",
    )
    report = make_report([make_finding(RuleStatus.FAIL, fix=fix, rule_id="some.rule")])
    output = capture_output(report)

    assert "Fix suggestions" in output
    assert "some.rule" in output
    assert "Create the missing file." in output
    assert "Run: hasscheck scaffold missing" in output


def test_fix_section_shows_summary_only_when_no_command() -> None:
    fix = FixSuggestion(
        summary="Review your configuration manually.",
        command=None,
    )
    report = make_report(
        [make_finding(RuleStatus.WARN, fix=fix, rule_id="config.rule")]
    )
    output = capture_output(report)

    assert "Fix suggestions" in output
    assert "Review your configuration manually." in output
    assert "Run:" not in output


def test_fix_section_shows_docs_url_when_present() -> None:
    fix = FixSuggestion(
        summary="See the docs for details.",
        docs_url="https://developers.home-assistant.io/docs/example",
    )
    report = make_report([make_finding(RuleStatus.FAIL, fix=fix, rule_id="docs.rule")])
    output = capture_output(report)

    assert "Fix suggestions" in output
    assert "Docs: https://developers.home-assistant.io/docs/example" in output


def test_fix_section_not_shown_for_pass_finding() -> None:
    fix = FixSuggestion(
        summary="This should not appear.",
        command="hasscheck scaffold pass",
    )
    report = make_report([make_finding(RuleStatus.PASS, fix=fix, rule_id="pass.rule")])
    output = capture_output(report)

    assert "Fix suggestions" not in output
    assert "This should not appear." not in output
    assert "Run: hasscheck scaffold pass" not in output


def test_fix_section_not_shown_when_no_findings_have_fix() -> None:
    report = make_report(
        [
            make_finding(RuleStatus.WARN, fix=None, rule_id="warn.rule"),
            make_finding(RuleStatus.FAIL, fix=None, rule_id="fail.rule"),
        ]
    )
    output = capture_output(report)

    assert "Fix suggestions" not in output


def test_fix_section_only_lists_non_pass_findings() -> None:
    pass_fix = FixSuggestion(
        summary="Pass fix — should not appear.", command="hasscheck scaffold pass"
    )
    warn_fix = FixSuggestion(
        summary="Warn fix — should appear.", command="hasscheck scaffold warn"
    )

    report = make_report(
        [
            make_finding(RuleStatus.PASS, fix=pass_fix, rule_id="pass.rule"),
            make_finding(RuleStatus.WARN, fix=warn_fix, rule_id="warn.rule"),
        ]
    )
    output = capture_output(report)

    assert "Fix suggestions" in output
    assert "warn.rule" in output
    assert "Warn fix — should appear." in output
    assert "Run: hasscheck scaffold warn" in output

    assert "Pass fix — should not appear." not in output
    assert "Run: hasscheck scaffold pass" not in output
