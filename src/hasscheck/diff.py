"""Diff layer for hasscheck reports.

Pure module — no Typer, no Rich, no I/O.
Provides: ReportDelta (ADR-D1), compute_delta (ADR-D2), delta_to_md (ADR-D3),
and the private _load_report helper (used by cli.py for the `diff` command).

Design decisions documented in docs/decisions/0019-diff-pr-comments.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hasscheck.baseline import compute_finding_hash  # ADR-D2: no extraction
from hasscheck.models import Finding, HassCheckReport

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReportDelta:
    """Immutable result of diffing two HassCheckReports.

    Identity is computed via ``compute_finding_hash`` (ADR 0016 / ADR-D2).
    Status-only changes (FAIL → WARN, same rule_id/path/message) appear in
    ``unchanged`` because the hash policy intentionally excludes the status
    field — see spec v1 limitation note.
    """

    new: tuple[Finding, ...]
    fixed: tuple[Finding, ...]
    unchanged: tuple[Finding, ...]


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _findings_by_hash(report: HassCheckReport) -> dict[str, Finding]:
    """Build a hash → Finding mapping for all findings in *report*.

    When two findings share the same hash (duplicate entries in a report),
    the last one wins — acceptable for v1 where duplicates are unexpected.
    """
    return {compute_finding_hash(f): f for f in report.findings}


def compute_delta(base: HassCheckReport, head: HassCheckReport) -> ReportDelta:
    """Compute the diff between *base* and *head* reports.

    - ``new``:       findings whose hash is in head but NOT in base (regressions)
    - ``fixed``:     findings whose hash is in base but NOT in head (resolved)
    - ``unchanged``: findings whose hash appears in BOTH (same identity)

    The result contains ``Finding`` objects, not raw hashes.
    """
    base_hashes = _findings_by_hash(base)
    head_hashes = _findings_by_hash(head)

    new = tuple(f for h, f in head_hashes.items() if h not in base_hashes)
    fixed = tuple(f for h, f in base_hashes.items() if h not in head_hashes)
    unchanged = tuple(f for h, f in head_hashes.items() if h in base_hashes)

    return ReportDelta(new=new, fixed=fixed, unchanged=unchanged)


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

_EMOJI = {
    "fail": "❌",
    "warn": "⚠️",
    "pass": "✅",
}
_MARKER = "<!-- hasscheck-pr-comment -->"


def _finding_line(f: Finding) -> str:
    """Render a single Finding as a Markdown list item.

    Format: ``- {emoji} `{rule_id}` — `{path or "(repo)"}` ``
    """
    emoji = _EMOJI.get(str(f.status).lower(), "🔍")
    location = f"`{f.path}`" if f.path else "`(repo)`"
    return f"- {emoji} `{f.rule_id}` — {location}"


def delta_to_md(delta: ReportDelta) -> str:
    """Render *delta* as a Markdown PR comment body.

    Always starts with the sticky marker ``<!-- hasscheck-pr-comment -->``
    so that the action can detect and update it in future iterations (ADR-D3).

    When all three tuples are empty, outputs a brief "No changes detected"
    message instead of empty section headers.
    """
    lines: list[str] = [_MARKER, "", "## HassCheck — PR delta", ""]

    if not delta.new and not delta.fixed and not delta.unchanged:
        lines.append("No changes detected.")
        lines.append("")
        lines.append("---")
        lines.append("_Run `hasscheck check` locally for the full report._")
        return "\n".join(lines)

    n_new = len(delta.new)
    n_fixed = len(delta.fixed)
    n_unchanged = len(delta.unchanged)

    lines.append(
        f"**Summary**: {n_new} new · {n_fixed} fixed · {n_unchanged} unchanged"
    )
    lines.append("")

    if delta.new:
        lines.append(f"### New findings ({n_new})")
        lines.append("")
        for f in delta.new:
            lines.append(_finding_line(f))
        lines.append("")

    if delta.fixed:
        lines.append(f"### Fixed findings ({n_fixed})")
        lines.append("")
        for f in delta.fixed:
            lines.append(_finding_line(f))
        lines.append("")

    if delta.unchanged:
        lines.append("<details>")
        lines.append(f"<summary>Unchanged: {n_unchanged} findings</summary>")
        lines.append("")
        for f in delta.unchanged:
            lines.append(_finding_line(f))
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append("_Run `hasscheck check` locally for the full report._")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# I/O helper (used only by cli.py — not exported from hasscheck/__init__.py)
# ---------------------------------------------------------------------------


def _load_report(path: Path) -> HassCheckReport:
    """Load and validate a HassCheckReport from *path*.

    Raises ``FileNotFoundError`` when the file does not exist.
    Raises ``ValueError`` (wrapping ``json.JSONDecodeError`` or
    ``pydantic.ValidationError``) on parse or schema errors.
    Callers in cli.py catch these and map them to exit code 2.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error in {path.name}: {exc}") from exc

    try:
        return HassCheckReport.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError
        raise ValueError(f"invalid report in {path.name}: {exc}") from exc
