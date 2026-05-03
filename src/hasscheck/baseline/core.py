"""Baseline data layer: models, hashing, partition, YAML I/O.

Pure, no Typer, no Rich. Imported by both the CLI subapp and `cli.check`.
The hash policy is documented in ADR 0016 — message normalization is the
only field-stability lever; rule_id and path must match exactly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from hasscheck.models import Finding

from hasscheck.models import RuleStatus

# Public statuses that are eligible to enter the baseline (D6).
_BASELINE_ELIGIBLE = frozenset({RuleStatus.FAIL, RuleStatus.WARN})


class BaselineError(Exception):
    """Raised when a baseline file is missing, corrupt, or refers to unknown data."""


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BaselineEntry(BaseModel):
    """A single accepted finding stored in the baseline file."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    path: str | None = None
    finding_hash: str = Field(min_length=8, max_length=8)
    accepted_at: date
    reason: str = ""


class BaselineFile(BaseModel):
    """The full contents of a hasscheck-baseline.yaml file."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    hasscheck_version: str
    ruleset: str
    accepted_findings: list[BaselineEntry] = Field(default_factory=list)


@dataclass(frozen=True)
class FindingPartition:
    """Result of comparing live findings against a baseline.

    - new:      live FAIL/WARN findings that DO NOT match any baseline entry
    - accepted: live FAIL/WARN findings that DO match a baseline entry
    - fixed:    baseline entries with NO matching live finding (debt resolved)
    """

    new: list[Finding]
    accepted: list[Finding]
    fixed: list[BaselineEntry]


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def compute_finding_hash(finding: Finding) -> str:
    """Stable 8-hex-char hash of the identity-bearing fields of a Finding.

    Hash inputs: rule_id, path (or empty string), normalized message.
    Excluded (intentionally): status, severity, rule_version, source.checked_at.
    Re-running with the same code on the same repo MUST yield the same hash.

    Message normalization is whitespace-collapse + lowercase to absorb trivial
    rewording without invalidating the entire baseline. ADR 0016 documents the
    expectation that message changes in rule code MAY require `baseline update`.
    """
    normalized = " ".join((finding.message or "").lower().split())
    raw = f"{finding.rule_id}|{finding.path or ''}|{normalized}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Partition
# ---------------------------------------------------------------------------


def partition_findings(
    findings: list[Finding],
    baseline: BaselineFile,
) -> FindingPartition:
    """Split live findings into (new, accepted, fixed) against a baseline.

    Eligibility: only RuleStatus.FAIL and RuleStatus.WARN are considered for
    matching against baseline entries (D6). All other statuses (PASS,
    NOT_APPLICABLE, MANUAL_REVIEW) are NOT placed into any of the three
    buckets — they are not regressions, not accepted debt, and not "fixed".
    """
    by_key: dict[tuple[str, str, str], BaselineEntry] = {
        (e.rule_id, e.path or "", e.finding_hash): e for e in baseline.accepted_findings
    }
    matched_keys: set[tuple[str, str, str]] = set()

    new: list[Finding] = []
    accepted: list[Finding] = []

    for f in findings:
        if f.status not in _BASELINE_ELIGIBLE:
            continue
        key = (f.rule_id, f.path or "", compute_finding_hash(f))
        if key in by_key:
            accepted.append(f)
            matched_keys.add(key)
        else:
            new.append(f)

    fixed = [entry for key, entry in by_key.items() if key not in matched_keys]

    return FindingPartition(new=new, accepted=accepted, fixed=fixed)


# ---------------------------------------------------------------------------
# YAML I/O
# ---------------------------------------------------------------------------


def load_baseline(path: Path) -> BaselineFile:
    """Load and validate a baseline YAML file.

    Raises BaselineError on missing file, YAML parse error, non-mapping top
    level, or schema validation failure. Never returns None — callers either
    have a baseline or they don't pass --baseline at all.
    """
    if not path.is_file():
        raise BaselineError(f"baseline file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BaselineError(f"YAML parse error in {path.name}: {exc}") from exc
    if raw is None:
        raise BaselineError(f"{path.name} is empty; expected a baseline mapping")
    if not isinstance(raw, dict):
        raise BaselineError(
            f"{path.name} must be a YAML mapping; got {type(raw).__name__}"
        )
    try:
        return BaselineFile(**raw)
    except ValidationError as exc:
        raise BaselineError(f"invalid {path.name}: {exc}") from exc


def write_baseline(baseline: BaselineFile, path: Path) -> None:
    """Write a baseline file with deterministic key ordering.

    Top-level keys are emitted in a fixed order to keep diffs minimal across
    runs. Entries inside accepted_findings are sorted by (rule_id, path or "",
    finding_hash) — also deterministic.
    """
    sorted_entries = sorted(
        baseline.accepted_findings,
        key=lambda e: (e.rule_id, e.path or "", e.finding_hash),
    )
    payload = {
        "generated_at": baseline.generated_at.isoformat(),
        "hasscheck_version": baseline.hasscheck_version,
        "ruleset": baseline.ruleset,
        "accepted_findings": [
            {
                "rule_id": e.rule_id,
                "path": e.path,
                "finding_hash": e.finding_hash,
                "accepted_at": e.accepted_at.isoformat(),
                "reason": e.reason,
            }
            for e in sorted_entries
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Builder helpers used by the CLI subapp
# ---------------------------------------------------------------------------


def baseline_from_findings(
    findings: list[Finding],
    *,
    hasscheck_version: str,
    ruleset: str,
    now: datetime,
    today: date,
) -> BaselineFile:
    """Build a fresh BaselineFile from a current findings list.

    Only FAIL/WARN findings are included (D6). Reason is empty by default;
    users edit the file (or use `baseline update` after editing) to attach
    rationale. accepted_at is set to `today` for every entry.
    """
    entries = [
        BaselineEntry(
            rule_id=f.rule_id,
            path=f.path,
            finding_hash=compute_finding_hash(f),
            accepted_at=today,
            reason="",
        )
        for f in findings
        if f.status in _BASELINE_ELIGIBLE
    ]
    return BaselineFile(
        generated_at=now,
        hasscheck_version=hasscheck_version,
        ruleset=ruleset,
        accepted_findings=entries,
    )


def merge_baseline(
    existing: BaselineFile,
    findings: list[Finding],
    *,
    hasscheck_version: str,
    ruleset: str,
    now: datetime,
    today: date,
) -> BaselineFile:
    """Merge live findings into an existing baseline (D1).

    Preservation rule: when an existing entry's (rule_id, path, finding_hash)
    matches a live FAIL/WARN finding, KEEP the existing reason and accepted_at.
    Stale entries (no matching live finding) are dropped. New live FAIL/WARN
    findings (no matching existing entry) are added with empty reason and
    today's accepted_at.

    Header fields (generated_at, hasscheck_version, ruleset) are refreshed.
    """
    by_key: dict[tuple[str, str, str], BaselineEntry] = {
        (e.rule_id, e.path or "", e.finding_hash): e for e in existing.accepted_findings
    }
    merged: list[BaselineEntry] = []

    for f in findings:
        if f.status not in _BASELINE_ELIGIBLE:
            continue
        key = (f.rule_id, f.path or "", compute_finding_hash(f))
        if key in by_key:
            merged.append(by_key[key])  # preserve existing reason + accepted_at
        else:
            merged.append(
                BaselineEntry(
                    rule_id=f.rule_id,
                    path=f.path,
                    finding_hash=key[2],
                    accepted_at=today,
                    reason="",
                )
            )
    # Stale entries (in baseline but not in live findings) are simply not
    # appended — they are dropped, which is the documented merge behavior.

    return BaselineFile(
        generated_at=now,
        hasscheck_version=hasscheck_version,
        ruleset=ruleset,
        accepted_findings=merged,
    )


def drop_from_baseline(
    existing: BaselineFile,
    *,
    rule_id: str,
    path: str | None,
    now: datetime,
) -> tuple[BaselineFile, int]:
    """Remove entries matching `rule_id` (D2). Returns (new_baseline, count_removed).

    If `path` is None: removes ALL entries with that rule_id.
    If `path` is given: removes only the (rule_id, path) entry/entries.

    Raises BaselineError if no entries match (so the user notices typos).
    """

    def _matches(entry: BaselineEntry) -> bool:
        if entry.rule_id != rule_id:
            return False
        if path is None:
            return True
        return (entry.path or "") == path

    kept = [e for e in existing.accepted_findings if not _matches(e)]
    removed = len(existing.accepted_findings) - len(kept)
    if removed == 0:
        scope = f"rule_id={rule_id!r}" + (f" path={path!r}" if path is not None else "")
        raise BaselineError(f"no baseline entries matched {scope}")
    return (
        BaselineFile(
            generated_at=now,
            hasscheck_version=existing.hasscheck_version,
            ruleset=existing.ruleset,
            accepted_findings=kept,
        ),
        removed,
    )
