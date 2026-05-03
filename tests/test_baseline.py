"""Tests for hasscheck.baseline — strict TDD, slice by slice."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from hasscheck.baseline import (
    BaselineEntry,
    BaselineError,
    BaselineFile,
    baseline_from_findings,
    compute_finding_hash,
    drop_from_baseline,
    load_baseline,
    merge_baseline,
    partition_findings,
    write_baseline,
)
from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
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


def _make_baseline_file(entries: list[BaselineEntry] | None = None) -> BaselineFile:
    return BaselineFile(
        generated_at=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        hasscheck_version="0.14.0",
        ruleset="hasscheck-ha-2026.5",
        accepted_findings=entries or [],
    )


_NOW = datetime(2026, 5, 2, 12, 0, 0, tzinfo=UTC)
_TODAY = date(2026, 5, 2)


# ---------------------------------------------------------------------------
# Slice 1: hash + models
# ---------------------------------------------------------------------------


def test_compute_finding_hash_is_deterministic() -> None:
    f1 = _make_finding(rule_id="m.d.e", message="domain missing", path="manifest.json")
    f2 = _make_finding(rule_id="m.d.e", message="domain missing", path="manifest.json")
    assert compute_finding_hash(f1) == compute_finding_hash(f2)


def test_compute_finding_hash_is_8_hex_chars() -> None:
    h = compute_finding_hash(_make_finding())
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_finding_hash_normalizes_whitespace() -> None:
    f1 = _make_finding(message="foo  bar  baz")
    f2 = _make_finding(message="foo bar baz")
    assert compute_finding_hash(f1) == compute_finding_hash(f2)


def test_compute_finding_hash_normalizes_case() -> None:
    f1 = _make_finding(message="DOMAIN Missing")
    f2 = _make_finding(message="domain missing")
    assert compute_finding_hash(f1) == compute_finding_hash(f2)


def test_compute_finding_hash_changes_on_rule_id_change() -> None:
    f1 = _make_finding(rule_id="a.b.c", message="same")
    f2 = _make_finding(rule_id="x.y.z", message="same")
    assert compute_finding_hash(f1) != compute_finding_hash(f2)


def test_compute_finding_hash_changes_on_path_change() -> None:
    f1 = _make_finding(path="file_a.py")
    f2 = _make_finding(path="file_b.py")
    assert compute_finding_hash(f1) != compute_finding_hash(f2)


def test_compute_finding_hash_ignores_status_and_severity() -> None:
    f_fail = _make_finding(status=RuleStatus.FAIL)
    f_warn = _make_finding(status=RuleStatus.WARN)
    assert compute_finding_hash(f_fail) == compute_finding_hash(f_warn)


def test_compute_finding_hash_none_path_uses_empty_segment() -> None:
    f_none = _make_finding(path=None)
    f_empty = _make_finding(path="")
    # path=None and path="" should produce the same hash (both use empty string)
    assert compute_finding_hash(f_none) == compute_finding_hash(f_empty)


def test_baseline_entry_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BaselineEntry.model_validate(
            {
                "rule_id": "x.y",
                "finding_hash": "abcd1234",
                "accepted_at": "2026-05-01",
                "extra_field": "oops",
            }
        )


def test_baseline_entry_requires_8_char_hash() -> None:
    with pytest.raises(ValidationError):
        BaselineEntry.model_validate(
            {
                "rule_id": "x.y",
                "finding_hash": "short",  # < 8 chars
                "accepted_at": "2026-05-01",
            }
        )


def test_baseline_file_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BaselineFile.model_validate(
            {
                "generated_at": "2026-05-01T00:00:00",
                "hasscheck_version": "0.14.0",
                "ruleset": "test",
                "accepted_findings": [],
                "unknown_key": True,
            }
        )


def test_baseline_file_empty_accepted_findings_is_valid() -> None:
    bf = _make_baseline_file()
    assert bf.accepted_findings == []


# ---------------------------------------------------------------------------
# Slice 2: partition_findings
# ---------------------------------------------------------------------------


def test_partition_marks_unmatched_finding_as_new() -> None:
    f = _make_finding(status=RuleStatus.WARN)
    bl = _make_baseline_file()
    partition = partition_findings([f], bl)
    assert f in partition.new
    assert f not in partition.accepted
    assert partition.fixed == []


def test_partition_marks_matched_finding_as_accepted() -> None:
    f = _make_finding(status=RuleStatus.FAIL)
    h = compute_finding_hash(f)
    entry = BaselineEntry(
        rule_id=f.rule_id,
        path=f.path,
        finding_hash=h,
        accepted_at=_TODAY,
    )
    bl = _make_baseline_file([entry])
    partition = partition_findings([f], bl)
    assert f in partition.accepted
    assert f not in partition.new


def test_partition_marks_unmatched_baseline_entry_as_fixed() -> None:
    entry = BaselineEntry(
        rule_id="old.rule",
        path=None,
        finding_hash="abcd1234",
        accepted_at=_TODAY,
    )
    bl = _make_baseline_file([entry])
    partition = partition_findings([], bl)
    assert entry in partition.fixed
    assert partition.new == []
    assert partition.accepted == []


def test_partition_only_evaluates_fail_and_warn() -> None:
    f_pass = _make_finding(status=RuleStatus.PASS)
    f_na = _make_finding(rule_id="na.rule", status=RuleStatus.NOT_APPLICABLE)
    bl = _make_baseline_file()
    partition = partition_findings([f_pass, f_na], bl)
    # Neither PASS nor NOT_APPLICABLE should appear in any bucket
    assert f_pass not in partition.new
    assert f_pass not in partition.accepted
    assert f_na not in partition.new
    assert f_na not in partition.accepted
    assert partition.fixed == []


def test_partition_message_rewording_treated_as_new() -> None:
    f_orig = _make_finding(message="original message")
    h = compute_finding_hash(f_orig)
    entry = BaselineEntry(
        rule_id=f_orig.rule_id,
        path=f_orig.path,
        finding_hash=h,
        accepted_at=_TODAY,
    )
    bl = _make_baseline_file([entry])
    f_reworded = _make_finding(message="different message entirely")
    partition = partition_findings([f_reworded], bl)
    assert f_reworded in partition.new
    assert entry in partition.fixed


def test_partition_path_difference_treated_as_new() -> None:
    f_a = _make_finding(path="a.py")
    h = compute_finding_hash(f_a)
    entry = BaselineEntry(
        rule_id=f_a.rule_id,
        path="a.py",
        finding_hash=h,
        accepted_at=_TODAY,
    )
    bl = _make_baseline_file([entry])
    f_b = _make_finding(path="b.py")
    partition = partition_findings([f_b], bl)
    assert f_b in partition.new
    assert entry in partition.fixed


def test_partition_empty_baseline_all_findings_new() -> None:
    findings = [_make_finding(rule_id="r.1"), _make_finding(rule_id="r.2")]
    bl = _make_baseline_file()
    partition = partition_findings(findings, bl)
    assert len(partition.new) == 2
    assert all(f in partition.new for f in findings)
    assert partition.accepted == []
    assert partition.fixed == []


def test_partition_empty_findings_all_baseline_fixed() -> None:
    entries = [
        BaselineEntry(rule_id="r.1", finding_hash="aaaabbbb", accepted_at=_TODAY),
        BaselineEntry(rule_id="r.2", finding_hash="ccccdddd", accepted_at=_TODAY),
    ]
    bl = _make_baseline_file(entries)
    partition = partition_findings([], bl)
    assert len(partition.fixed) == 2
    fixed_rule_ids = {e.rule_id for e in partition.fixed}
    assert fixed_rule_ids == {"r.1", "r.2"}
    assert partition.new == []
    assert partition.accepted == []


# ---------------------------------------------------------------------------
# Slice 3: YAML I/O
# ---------------------------------------------------------------------------


def test_load_baseline_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(BaselineError, match="not found"):
        load_baseline(tmp_path / "nonexistent.yaml")


def test_load_baseline_invalid_yaml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "baseline.yaml"
    bad.write_text("{key: [invalid: yaml: :\n", encoding="utf-8")
    with pytest.raises(BaselineError, match="YAML"):
        load_baseline(bad)


def test_load_baseline_non_mapping_raises(tmp_path: Path) -> None:
    bad = tmp_path / "baseline.yaml"
    bad.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(BaselineError, match="mapping"):
        load_baseline(bad)


def test_load_baseline_extra_fields_raises(tmp_path: Path) -> None:
    bad = tmp_path / "baseline.yaml"
    bad.write_text(
        "generated_at: '2026-05-01T00:00:00'\n"
        "hasscheck_version: '0.14.0'\n"
        "ruleset: 'test'\n"
        "accepted_findings: []\n"
        "unexpected_key: true\n",
        encoding="utf-8",
    )
    with pytest.raises(BaselineError):
        load_baseline(bad)


def test_write_baseline_creates_parent_dir(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / "nested" / "baseline.yaml"
    bl = _make_baseline_file()
    write_baseline(bl, target)
    assert target.exists()


def test_write_baseline_round_trip_preserves_entries(tmp_path: Path) -> None:
    entry = BaselineEntry(
        rule_id="m.d.e",
        path="manifest.json",
        finding_hash="abcd1234",
        accepted_at=date(2026, 5, 1),
        reason="known issue",
    )
    bl = _make_baseline_file([entry])
    target = tmp_path / "baseline.yaml"
    write_baseline(bl, target)
    loaded = load_baseline(target)
    assert len(loaded.accepted_findings) == 1
    assert loaded.accepted_findings[0].rule_id == "m.d.e"
    assert loaded.accepted_findings[0].reason == "known issue"
    assert loaded.accepted_findings[0].finding_hash == "abcd1234"


def test_write_baseline_sorts_entries_deterministically(tmp_path: Path) -> None:
    entries = [
        BaselineEntry(
            rule_id="z.rule", path=None, finding_hash="zzzz9999", accepted_at=_TODAY
        ),
        BaselineEntry(
            rule_id="a.rule", path=None, finding_hash="aaaa1111", accepted_at=_TODAY
        ),
        BaselineEntry(
            rule_id="m.rule", path=None, finding_hash="mmmm5555", accepted_at=_TODAY
        ),
    ]
    bl = _make_baseline_file(entries)
    target = tmp_path / "baseline.yaml"
    write_baseline(bl, target)
    loaded = load_baseline(target)
    rule_ids = [e.rule_id for e in loaded.accepted_findings]
    assert rule_ids == sorted(rule_ids)


# ---------------------------------------------------------------------------
# Slice 4: Builder helpers
# ---------------------------------------------------------------------------


def test_baseline_from_findings_filters_to_fail_and_warn() -> None:
    findings = [
        _make_finding(rule_id="f.rule", status=RuleStatus.FAIL),
        _make_finding(rule_id="w.rule", status=RuleStatus.WARN),
        _make_finding(rule_id="p.rule", status=RuleStatus.PASS),
        _make_finding(rule_id="na.rule", status=RuleStatus.NOT_APPLICABLE),
    ]
    bl = baseline_from_findings(
        findings,
        hasscheck_version="0.14.0",
        ruleset="test-ruleset",
        now=_NOW,
        today=_TODAY,
    )
    rule_ids = {e.rule_id for e in bl.accepted_findings}
    assert "f.rule" in rule_ids
    assert "w.rule" in rule_ids
    assert "p.rule" not in rule_ids
    assert "na.rule" not in rule_ids


def test_baseline_from_findings_sets_today_and_empty_reason() -> None:
    findings = [_make_finding(rule_id="x.y", status=RuleStatus.FAIL)]
    bl = baseline_from_findings(
        findings,
        hasscheck_version="0.14.0",
        ruleset="test-ruleset",
        now=_NOW,
        today=_TODAY,
    )
    assert len(bl.accepted_findings) == 1
    entry = bl.accepted_findings[0]
    assert entry.accepted_at == _TODAY
    assert entry.reason == ""


def test_merge_baseline_preserves_reason_for_matched_hash() -> None:
    f = _make_finding(rule_id="x.y", status=RuleStatus.FAIL)
    h = compute_finding_hash(f)
    old_entry = BaselineEntry(
        rule_id=f.rule_id,
        path=f.path,
        finding_hash=h,
        accepted_at=date(2026, 1, 1),
        reason="known debt",
    )
    existing = _make_baseline_file([old_entry])
    merged = merge_baseline(
        existing,
        [f],
        hasscheck_version="0.14.0",
        ruleset="test-ruleset",
        now=_NOW,
        today=_TODAY,
    )
    assert len(merged.accepted_findings) == 1
    assert merged.accepted_findings[0].reason == "known debt"


def test_merge_baseline_preserves_accepted_at_for_matched_hash() -> None:
    f = _make_finding(rule_id="x.y", status=RuleStatus.FAIL)
    h = compute_finding_hash(f)
    original_date = date(2026, 1, 1)
    old_entry = BaselineEntry(
        rule_id=f.rule_id,
        path=f.path,
        finding_hash=h,
        accepted_at=original_date,
        reason="",
    )
    existing = _make_baseline_file([old_entry])
    merged = merge_baseline(
        existing,
        [f],
        hasscheck_version="0.14.0",
        ruleset="test-ruleset",
        now=_NOW,
        today=_TODAY,
    )
    assert merged.accepted_findings[0].accepted_at == original_date


def test_merge_baseline_drops_stale_entries() -> None:
    stale_entry = BaselineEntry(
        rule_id="stale.rule",
        path=None,
        finding_hash="stale123",
        accepted_at=_TODAY,
        reason="was valid",
    )
    existing = _make_baseline_file([stale_entry])
    # Pass empty findings — everything is stale
    merged = merge_baseline(
        existing,
        [],
        hasscheck_version="0.14.0",
        ruleset="test-ruleset",
        now=_NOW,
        today=_TODAY,
    )
    assert merged.accepted_findings == []


def test_merge_baseline_adds_new_findings_with_empty_reason() -> None:
    existing = _make_baseline_file()
    f = _make_finding(rule_id="new.rule", status=RuleStatus.WARN)
    merged = merge_baseline(
        existing,
        [f],
        hasscheck_version="0.14.0",
        ruleset="test-ruleset",
        now=_NOW,
        today=_TODAY,
    )
    assert len(merged.accepted_findings) == 1
    assert merged.accepted_findings[0].reason == ""
    assert merged.accepted_findings[0].accepted_at == _TODAY


def test_drop_from_baseline_removes_all_for_rule_id() -> None:
    entries = [
        BaselineEntry(
            rule_id="W001", path="a.py", finding_hash="aaaa1111", accepted_at=_TODAY
        ),
        BaselineEntry(
            rule_id="W001", path="b.py", finding_hash="bbbb2222", accepted_at=_TODAY
        ),
        BaselineEntry(
            rule_id="W002", path=None, finding_hash="cccc3333", accepted_at=_TODAY
        ),
    ]
    existing = _make_baseline_file(entries)
    new_bl, removed = drop_from_baseline(existing, rule_id="W001", path=None, now=_NOW)
    assert removed == 2
    assert all(e.rule_id != "W001" for e in new_bl.accepted_findings)
    assert len(new_bl.accepted_findings) == 1


def test_drop_from_baseline_path_narrows_to_single_entry() -> None:
    entries = [
        BaselineEntry(
            rule_id="W001", path="a.py", finding_hash="aaaa1111", accepted_at=_TODAY
        ),
        BaselineEntry(
            rule_id="W001", path="b.py", finding_hash="bbbb2222", accepted_at=_TODAY
        ),
    ]
    existing = _make_baseline_file(entries)
    new_bl, removed = drop_from_baseline(
        existing, rule_id="W001", path="a.py", now=_NOW
    )
    assert removed == 1
    remaining_paths = [e.path for e in new_bl.accepted_findings]
    assert "a.py" not in remaining_paths
    assert "b.py" in remaining_paths


def test_drop_from_baseline_no_match_raises() -> None:
    entries = [
        BaselineEntry(
            rule_id="W001", path=None, finding_hash="aaaa1111", accepted_at=_TODAY
        ),
    ]
    existing = _make_baseline_file(entries)
    with pytest.raises(BaselineError, match="no baseline entries matched"):
        drop_from_baseline(existing, rule_id="W999", path=None, now=_NOW)
