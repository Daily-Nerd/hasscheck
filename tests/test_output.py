from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    CategorySignal,
    Finding,
    FixSuggestion,
    HassCheckReport,
    ProjectInfo,
    ReportSummary,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.output import print_terminal_report, report_to_md


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


@pytest.mark.parametrize(
    "status",
    [
        RuleStatus.WARN,
        RuleStatus.FAIL,
        RuleStatus.NOT_APPLICABLE,
        RuleStatus.MANUAL_REVIEW,
    ],
)
def test_fix_section_shown_for_all_non_pass_statuses(status: RuleStatus) -> None:
    fix = FixSuggestion(summary="Fix this.", command="hasscheck scaffold x")
    report = make_report([make_finding(status, fix=fix)])
    output = capture_output(report)
    assert "Fix suggestions" in output
    assert "Fix this." in output


def test_fix_section_shows_all_qualifying_findings() -> None:
    fix1 = FixSuggestion(
        summary="Add diagnostics.py", command="hasscheck scaffold diagnostics"
    )
    fix2 = FixSuggestion(summary="Add repairs.py", command="hasscheck scaffold repairs")
    report = make_report(
        [
            make_finding(RuleStatus.WARN, fix=fix1, rule_id="diagnostics.file.exists"),
            make_finding(RuleStatus.WARN, fix=fix2, rule_id="repairs.file.exists"),
        ]
    )
    output = capture_output(report)
    assert "diagnostics.file.exists" in output
    assert "repairs.file.exists" in output
    assert "hasscheck scaffold diagnostics" in output
    assert "hasscheck scaffold repairs" in output


def make_finding_with_source(
    status: RuleStatus,
    fix: FixSuggestion | None = None,
    rule_id: str = "test.rule",
    applicability_source: str = "default",
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
            status=ApplicabilityStatus.APPLICABLE,
            reason="applicable",
            source=applicability_source,
        ),
        source=RuleSource(url="https://example.com"),
        fix=fix,
    )


def make_md_report(
    findings: list[Finding],
    categories: list[CategorySignal] | None = None,
) -> HassCheckReport:
    return HassCheckReport(
        project=ProjectInfo(path="/some/path", domain="my_integration"),
        summary=ReportSummary(categories=categories or []),
        findings=findings,
    )


def test_report_to_md_basic_structure() -> None:
    report = make_md_report([make_finding(RuleStatus.PASS)])
    output = report_to_md(report)

    assert "## HassCheck Signals" in output
    assert "| Category | Score | Points |" in output
    assert "| Status | Rule | Message |" in output
    assert "Security Review: Not performed." in output


def test_report_to_md_category_score_all_points() -> None:
    categories = [
        CategorySignal(
            id="cat1", label="Structure", points_awarded=10, points_possible=10
        )
    ]
    report = make_md_report([], categories=categories)
    output = report_to_md(report)

    assert "✅" in output
    assert "10 / 10" in output


def test_report_to_md_category_score_partial_points() -> None:
    categories = [
        CategorySignal(
            id="cat1", label="Structure", points_awarded=5, points_possible=10
        )
    ]
    report = make_md_report([], categories=categories)
    output = report_to_md(report)

    assert "⚠️" in output
    assert "5 / 10" in output


def test_report_to_md_category_score_zero_points() -> None:
    categories = [
        CategorySignal(
            id="cat1", label="Structure", points_awarded=0, points_possible=10
        )
    ]
    report = make_md_report([], categories=categories)
    output = report_to_md(report)

    assert "❌" in output
    assert "0 / 10" in output


def test_report_to_md_fix_suggestions_shown_for_non_pass_with_fix() -> None:
    fix = FixSuggestion(summary="Do the thing.", command="hasscheck scaffold thing")
    report = make_md_report(
        [make_finding(RuleStatus.WARN, fix=fix, rule_id="some.rule")]
    )
    output = report_to_md(report)

    assert "### Fix Suggestions" in output
    assert "some.rule" in output
    assert "Do the thing." in output
    assert "`hasscheck scaffold thing`" in output


def test_report_to_md_fix_suggestions_omitted_when_all_fixes_none() -> None:
    report = make_md_report(
        [
            make_finding(RuleStatus.WARN, fix=None, rule_id="warn.rule"),
            make_finding(RuleStatus.FAIL, fix=None, rule_id="fail.rule"),
        ]
    )
    output = report_to_md(report)

    assert "### Fix Suggestions" not in output


def test_report_to_md_fix_suggestions_omitted_for_pass_findings() -> None:
    fix = FixSuggestion(summary="Should not appear.", command="hasscheck scaffold pass")
    report = make_md_report(
        [make_finding(RuleStatus.PASS, fix=fix, rule_id="pass.rule")]
    )
    output = report_to_md(report)

    assert "### Fix Suggestions" not in output
    assert "Should not appear." not in output


def test_report_to_md_config_applicability_marker() -> None:
    finding = make_finding_with_source(
        RuleStatus.PASS, rule_id="config.rule", applicability_source="config"
    )
    report = make_md_report([finding])
    output = report_to_md(report)

    assert "config.rule *(config)*" in output


def test_report_to_md_no_config_marker_for_default_source() -> None:
    finding = make_finding_with_source(
        RuleStatus.PASS, rule_id="default.rule", applicability_source="default"
    )
    report = make_md_report([finding])
    output = report_to_md(report)

    assert "*(config)*" not in output


# ---------- Phase 141: Compat policy footer scenarios (RED) ----------

from hasscheck.models import ReportTarget  # noqa: E402

_EXPECTED_FOOTER_FRAGMENT = "compatibility-claim-policy.md"


def _make_report_with_target(ha_version: str | None) -> HassCheckReport:
    return HassCheckReport(
        project=ProjectInfo(path="."),
        summary=ReportSummary(),
        findings=[],
        target=ReportTarget(ha_version=ha_version),
    )


# Scenario 20 — text report emits footer when ha_version populated
def test_text_report_emits_compat_policy_footer_when_ha_version_populated() -> None:
    report = _make_report_with_target(ha_version="2026.5.1")
    output = capture_output(report)
    assert _EXPECTED_FOOTER_FRAGMENT in output, (
        f"Expected footer fragment '{_EXPECTED_FOOTER_FRAGMENT}' not found in terminal output"
    )


# Scenario 21 — text report omits footer when target is None
def test_text_report_omits_footer_when_target_is_none() -> None:
    report = HassCheckReport(
        project=ProjectInfo(path="."),
        summary=ReportSummary(),
        findings=[],
        target=None,
    )
    output = capture_output(report)
    assert _EXPECTED_FOOTER_FRAGMENT not in output


# Scenario 22 — text report omits footer when ha_version is None
def test_text_report_omits_footer_when_ha_version_is_none() -> None:
    report = _make_report_with_target(ha_version=None)
    output = capture_output(report)
    assert _EXPECTED_FOOTER_FRAGMENT not in output


# Scenario 23 — markdown report emits footer when ha_version populated
def test_markdown_report_emits_compat_policy_footer_when_ha_version_populated() -> None:
    report = _make_report_with_target(ha_version="2026.5.1")
    output = report_to_md(report)
    assert _EXPECTED_FOOTER_FRAGMENT in output, (
        f"Expected footer fragment '{_EXPECTED_FOOTER_FRAGMENT}' not found in markdown output"
    )


# Scenario 24 — JSON report unchanged by footer logic
def test_json_report_unchanged_by_footer_logic() -> None:
    from hasscheck.output import report_to_json

    for ha_version in (None, "2026.5.1"):
        report = _make_report_with_target(ha_version=ha_version)
        json_bytes = report_to_json(report)
        assert _EXPECTED_FOOTER_FRAGMENT not in json_bytes, (
            f"Footer fragment should not appear in JSON output (ha_version={ha_version!r})"
        )
