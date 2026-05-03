"""Tests for hasscheck.diff — strict TDD, Groups 1–3."""

from __future__ import annotations

import dataclasses

import pytest

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    HassCheckReport,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    rule_id: str = "x.y",
    message: str = "msg",
    path: str | None = None,
    status: RuleStatus = RuleStatus.FAIL,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version="1.0",
        category="test",
        status=status,
        severity=RuleSeverity.REQUIRED,
        title="Test Finding",
        message=message,
        applicability=Applicability(
            status=ApplicabilityStatus.APPLICABLE,
            reason="applicable",
            source="default",
        ),
        source=RuleSource(url="https://example.com"),
        path=path,
    )


def _make_report(findings: list[Finding]) -> HassCheckReport:
    return HassCheckReport.model_validate(
        {
            "schema_version": "0.5.0",
            "project": {"path": "/repo"},
            "summary": {
                "overall": "informational_only",
                "security_review": "not_performed",
                "official_ha_tier": "not_assigned",
                "hacs_acceptance": "not_guaranteed",
            },
            "findings": [f.model_dump(mode="json") for f in findings],
        }
    )


# ---------------------------------------------------------------------------
# Group 1 — ReportDelta dataclass
# ---------------------------------------------------------------------------


def test_report_delta_is_importable() -> None:
    from hasscheck.diff import ReportDelta  # noqa: F401 (import check)


def test_report_delta_is_frozen_dataclass() -> None:
    from hasscheck.diff import ReportDelta

    assert dataclasses.is_dataclass(ReportDelta)
    assert ReportDelta.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_report_delta_has_correct_fields() -> None:
    from hasscheck.diff import ReportDelta

    fields = {f.name: f for f in dataclasses.fields(ReportDelta)}
    assert set(fields) == {"new", "fixed", "unchanged"}
    for field_name in ("new", "fixed", "unchanged"):
        assert fields[field_name].type == "tuple[Finding, ...]"


def test_report_delta_instantiates() -> None:
    from hasscheck.diff import ReportDelta

    f = _make_finding()
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    assert delta.new == (f,)
    assert delta.fixed == ()
    assert delta.unchanged == ()


def test_report_delta_is_immutable() -> None:
    from hasscheck.diff import ReportDelta

    delta = ReportDelta(new=(), fixed=(), unchanged=())
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        delta.new = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Group 2 — compute_delta
# ---------------------------------------------------------------------------


def test_compute_delta_importable() -> None:
    from hasscheck.diff import compute_delta  # noqa: F401


def test_s1_identical_reports_all_unchanged() -> None:
    """S1 — identical reports produce empty new/fixed, all in unchanged."""
    from hasscheck.diff import compute_delta

    f1 = _make_finding(rule_id="a.b", message="msg1", path="p.py")
    f2 = _make_finding(rule_id="c.d", message="msg2", path=None)
    report = _make_report([f1, f2])
    delta = compute_delta(report, report)

    assert delta.new == ()
    assert delta.fixed == ()
    assert len(delta.unchanged) == 2


def test_s2_new_finding_in_head() -> None:
    """S2 — head has one additional finding; it appears in new."""
    from hasscheck.diff import compute_delta

    existing = _make_finding(rule_id="a.b", message="msg")
    added = _make_finding(rule_id="c.d", message="added")
    base = _make_report([existing])
    head = _make_report([existing, added])
    delta = compute_delta(base, head)

    assert len(delta.new) == 1
    assert delta.new[0].rule_id == "c.d"
    assert delta.fixed == ()
    assert len(delta.unchanged) == 1


def test_s3_finding_removed_in_head() -> None:
    """S3 — base has a finding not present in head; it appears in fixed."""
    from hasscheck.diff import compute_delta

    existing = _make_finding(rule_id="a.b", message="msg")
    removed = _make_finding(rule_id="c.d", message="removed")
    base = _make_report([existing, removed])
    head = _make_report([existing])
    delta = compute_delta(base, head)

    assert delta.new == ()
    assert len(delta.fixed) == 1
    assert delta.fixed[0].rule_id == "c.d"
    assert len(delta.unchanged) == 1


def test_s4_status_only_change_is_unchanged() -> None:
    """S4 — same rule_id/path/message but status FAIL→WARN counts as unchanged."""
    from hasscheck.diff import compute_delta

    base_f = _make_finding(
        rule_id="a.b", message="msg", path="p.py", status=RuleStatus.FAIL
    )
    head_f = _make_finding(
        rule_id="a.b", message="msg", path="p.py", status=RuleStatus.WARN
    )
    base = _make_report([base_f])
    head = _make_report([head_f])
    delta = compute_delta(base, head)

    assert delta.new == ()
    assert delta.fixed == ()
    assert len(delta.unchanged) == 1


def test_compute_delta_mixed_scenario() -> None:
    """Mixed: one new, one fixed, one unchanged."""
    from hasscheck.diff import compute_delta

    common = _make_finding(rule_id="common", message="shared")
    old_only = _make_finding(rule_id="old", message="was there")
    new_only = _make_finding(rule_id="new", message="appeared")
    base = _make_report([common, old_only])
    head = _make_report([common, new_only])
    delta = compute_delta(base, head)

    assert len(delta.new) == 1
    assert delta.new[0].rule_id == "new"
    assert len(delta.fixed) == 1
    assert delta.fixed[0].rule_id == "old"
    assert len(delta.unchanged) == 1
    assert delta.unchanged[0].rule_id == "common"


def test_compute_delta_empty_reports() -> None:
    """Both reports empty → all tuples empty."""
    from hasscheck.diff import compute_delta

    base = _make_report([])
    head = _make_report([])
    delta = compute_delta(base, head)

    assert delta.new == ()
    assert delta.fixed == ()
    assert delta.unchanged == ()


# ---------------------------------------------------------------------------
# Group 3 — delta_to_md
# ---------------------------------------------------------------------------


def test_delta_to_md_importable() -> None:
    from hasscheck.diff import delta_to_md  # noqa: F401


def test_s9_empty_delta_contains_no_changes() -> None:
    """S9 — all-empty delta → contains 'No changes detected'."""
    from hasscheck.diff import ReportDelta, delta_to_md

    delta = ReportDelta(new=(), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "No changes detected" in md


def test_s10_nonempty_delta_starts_with_marker() -> None:
    """S10 — non-empty delta starts with the sticky marker."""
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b")
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert md.startswith("<!-- hasscheck-pr-comment -->")


def test_delta_to_md_new_section_present_when_nonempty() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b")
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "### New findings (1)" in md


def test_delta_to_md_new_section_absent_when_empty() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    delta = ReportDelta(new=(), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "### New findings" not in md


def test_delta_to_md_fixed_section_present_when_nonempty() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b")
    delta = ReportDelta(new=(), fixed=(f,), unchanged=())
    md = delta_to_md(delta)
    assert "### Fixed findings (1)" in md


def test_delta_to_md_fixed_section_absent_when_empty() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b")
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "### Fixed findings" not in md


def test_delta_to_md_unchanged_details_block_present() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b")
    delta = ReportDelta(new=(), fixed=(), unchanged=(f,))
    md = delta_to_md(delta)
    assert "<details>" in md
    assert "Unchanged" in md
    assert "1" in md


def test_delta_to_md_unchanged_absent_when_empty() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b")
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "<details>" not in md


def test_delta_to_md_heading_present() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b")
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "## HassCheck" in md


def test_delta_to_md_finding_line_contains_rule_id() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="manifest.exists", path="custom_components/demo")
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "manifest.exists" in md


def test_delta_to_md_finding_line_contains_path() -> None:
    from hasscheck.diff import ReportDelta, delta_to_md

    f = _make_finding(rule_id="a.b", path="some/path.py")
    delta = ReportDelta(new=(f,), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert "some/path.py" in md


def test_delta_to_md_empty_delta_starts_with_marker() -> None:
    """Even the empty-delta case should carry the marker for sticky detection."""
    from hasscheck.diff import ReportDelta, delta_to_md

    delta = ReportDelta(new=(), fixed=(), unchanged=())
    md = delta_to_md(delta)
    assert md.startswith("<!-- hasscheck-pr-comment -->")
