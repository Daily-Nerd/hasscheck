"""Maintenance signal rules — recent_commit, recent_release, changelog.

These rules check observable maintenance signals using local git history and
filesystem presence. No GitHub API calls are made; all git operations run via
subprocess against the local .git directory.

Issue #109 — v0.11 second batch.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import time
from pathlib import Path

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    FixSuggestion,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.rules.base import ProjectContext, RuleDefinition

CATEGORY = "maintenance"
_DOCS_URL = "https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases"
_SOURCE_CHECKED_AT = "2026-05-01"
_MAX_AGE_MONTHS = 12
_SECONDS_PER_MONTH = 30.44 * 86400  # average month in seconds
_MAX_AGE_SECONDS = _MAX_AGE_MONTHS * _SECONDS_PER_MONTH

_CHANGELOG_FILENAMES = (
    "CHANGELOG.md",
    "CHANGELOG",
    "HISTORY.md",
    "HISTORY",
    "RELEASES.md",
    "NEWS.md",
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _git_available() -> bool:
    return shutil.which("git") is not None


def _is_git_repo(root: Path) -> bool:
    """Return True if root is inside a git checkout (has .git dir or file)."""
    return (root / ".git").exists()


def _run_git(args: list[str], cwd: Path) -> tuple[str | None, str | None]:
    """Run a git command with a 5-second timeout.

    Returns (stdout, error_msg). On success error_msg is None.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
    except FileNotFoundError:
        return None, "git binary not found"
    except subprocess.TimeoutExpired:
        return None, "git command timed out"
    if result.returncode != 0:
        return None, result.stderr.strip() or f"git exit {result.returncode}"
    return result.stdout.strip(), None


def _head_commit_timestamp(root: Path) -> tuple[int | None, str | None]:
    """Return (unix_timestamp, error) for the HEAD commit."""
    out, err = _run_git(["log", "-1", "--format=%ct"], root)
    if err is not None:
        return None, err
    if not out:
        return None, "no commits"
    try:
        return int(out), None
    except ValueError:
        return None, f"unexpected git output: {out!r}"


def _latest_tag_timestamp(root: Path) -> tuple[int | None, str | None]:
    """Return (unix_timestamp, error) for the most recent tag.

    Returns (None, "no tags") when the repo has no tags at all.
    """
    out, err = _run_git(
        [
            "for-each-ref",
            "--sort=-creatordate",
            "--format=%(creatordate:unix)",
            "refs/tags",
            "--count=1",
        ],
        root,
    )
    if err is not None:
        return None, err
    if not out:
        return None, "no tags"
    try:
        return int(out), None
    except ValueError:
        return None, f"unexpected git output: {out!r}"


def _format_age(age_seconds: float) -> str:
    """Format age in seconds as a human-readable string."""
    months = age_seconds / _SECONDS_PER_MONTH
    if months >= 1:
        return f"{math.floor(months)} month{'s' if math.floor(months) != 1 else ''}"
    days = age_seconds / 86400
    return f"{math.floor(days)} day{'s' if math.floor(days) != 1 else ''}"


def _not_applicable_finding(
    rule_id: str,
    rule_version: str,
    title: str,
    reason: str,
    source: RuleSource,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version=rule_version,
        category=CATEGORY,
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.RECOMMENDED,
        title=title,
        message=reason,
        applicability=Applicability(
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reason=reason,
        ),
        source=source,
    )


# ---------------------------------------------------------------------------
# Rule: maintenance.recent_commit.detected
# ---------------------------------------------------------------------------

_COMMIT_RULE_ID = "maintenance.recent_commit.detected"
_COMMIT_TITLE = "Repository has a recent commit"
_COMMIT_SOURCE = RuleSource(url=_DOCS_URL, checked_at=_SOURCE_CHECKED_AT)


def recent_commit_check(context: ProjectContext) -> Finding:
    if not _is_git_repo(context.root):
        return _not_applicable_finding(
            _COMMIT_RULE_ID,
            "1.0.0",
            _COMMIT_TITLE,
            "repository is not a git checkout (no .git directory)",
            _COMMIT_SOURCE,
        )
    if not _git_available():
        return _not_applicable_finding(
            _COMMIT_RULE_ID,
            "1.0.0",
            _COMMIT_TITLE,
            "git binary not found on PATH",
            _COMMIT_SOURCE,
        )

    ts, err = _head_commit_timestamp(context.root)
    if err is not None:
        return _not_applicable_finding(
            _COMMIT_RULE_ID,
            "1.0.0",
            _COMMIT_TITLE,
            f"could not read git history: {err}",
            _COMMIT_SOURCE,
        )

    assert ts is not None
    age = time.time() - ts
    age_str = _format_age(age)
    is_recent = age < _MAX_AGE_SECONDS

    return Finding(
        rule_id=_COMMIT_RULE_ID,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if is_recent else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title=_COMMIT_TITLE,
        message=(
            f"Most recent commit is {age_str} old — within the {_MAX_AGE_MONTHS}-month threshold."
            if is_recent
            else f"Most recent commit is {age_str} old — exceeds the {_MAX_AGE_MONTHS}-month threshold."
        ),
        applicability=Applicability(
            reason="An active git history signals ongoing maintenance."
        ),
        source=_COMMIT_SOURCE,
        fix=None
        if is_recent
        else FixSuggestion(
            summary="Make a new commit to indicate active maintenance.",
        ),
    )


# ---------------------------------------------------------------------------
# Rule: maintenance.recent_release.detected
# ---------------------------------------------------------------------------

_RELEASE_RULE_ID = "maintenance.recent_release.detected"
_RELEASE_TITLE = "Repository has a recent release tag"
_RELEASE_SOURCE = RuleSource(url=_DOCS_URL, checked_at=_SOURCE_CHECKED_AT)


def recent_release_check(context: ProjectContext) -> Finding:
    if not _is_git_repo(context.root):
        return _not_applicable_finding(
            _RELEASE_RULE_ID,
            "1.0.0",
            _RELEASE_TITLE,
            "repository is not a git checkout (no .git directory)",
            _RELEASE_SOURCE,
        )
    if not _git_available():
        return _not_applicable_finding(
            _RELEASE_RULE_ID,
            "1.0.0",
            _RELEASE_TITLE,
            "git binary not found on PATH",
            _RELEASE_SOURCE,
        )

    ts, err = _latest_tag_timestamp(context.root)

    if err == "no tags":
        return _not_applicable_finding(
            _RELEASE_RULE_ID,
            "1.0.0",
            _RELEASE_TITLE,
            "no version tags found — repository may not have been released yet",
            _RELEASE_SOURCE,
        )

    if err is not None:
        return _not_applicable_finding(
            _RELEASE_RULE_ID,
            "1.0.0",
            _RELEASE_TITLE,
            f"could not read git tags: {err}",
            _RELEASE_SOURCE,
        )

    assert ts is not None
    age = time.time() - ts
    age_str = _format_age(age)
    is_recent = age < _MAX_AGE_SECONDS

    return Finding(
        rule_id=_RELEASE_RULE_ID,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if is_recent else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title=_RELEASE_TITLE,
        message=(
            f"Most recent release tag is {age_str} old — within the {_MAX_AGE_MONTHS}-month threshold."
            if is_recent
            else f"Most recent release tag is {age_str} old — exceeds the {_MAX_AGE_MONTHS}-month threshold."
        ),
        applicability=Applicability(
            reason="A recent release tag signals active versioning and distribution."
        ),
        source=_RELEASE_SOURCE,
        fix=None
        if is_recent
        else FixSuggestion(
            summary="Create a new release tag (e.g. git tag -a v1.x.x -m 'release').",
            docs_url=_DOCS_URL,
        ),
    )


# ---------------------------------------------------------------------------
# Rule: maintenance.changelog.exists
# ---------------------------------------------------------------------------

_CHANGELOG_RULE_ID = "maintenance.changelog.exists"
_CHANGELOG_TITLE = "Repository has a changelog file"
_CHANGELOG_SOURCE = RuleSource(url=_DOCS_URL, checked_at=_SOURCE_CHECKED_AT)


def changelog_exists_check(context: ProjectContext) -> Finding:
    existing = next(
        (
            context.root / name
            for name in _CHANGELOG_FILENAMES
            if (context.root / name).is_file()
        ),
        None,
    )
    exists = existing is not None

    return Finding(
        rule_id=_CHANGELOG_RULE_ID,
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title=_CHANGELOG_TITLE,
        message=(
            f"Repository contains {existing.name}."
            if exists
            else "Repository does not contain a recognized changelog file "
            f"({', '.join(_CHANGELOG_FILENAMES)})."
        ),
        applicability=Applicability(
            reason="A changelog helps users understand what changed between versions."
        ),
        source=_CHANGELOG_SOURCE,
        fix=None
        if exists
        else FixSuggestion(
            summary="Add a CHANGELOG.md at the repository root describing changes per version.",
        ),
        path=existing.name if exists else None,
    )


# ---------------------------------------------------------------------------
# Rule registry export
# ---------------------------------------------------------------------------

RULES = [
    RuleDefinition(
        id=_COMMIT_RULE_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_COMMIT_TITLE,
        why="An active commit history signals that the integration is actively maintained.",
        source_url=_DOCS_URL,
        check=recent_commit_check,
        overridable=True,
    ),
    RuleDefinition(
        id=_RELEASE_RULE_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_RELEASE_TITLE,
        why="Recent release tags indicate the integration ships versioned releases for users to install.",
        source_url=_DOCS_URL,
        check=recent_release_check,
        overridable=True,
    ),
    RuleDefinition(
        id=_CHANGELOG_RULE_ID,
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title=_CHANGELOG_TITLE,
        why="A changelog documents version history so users can understand what changed.",
        source_url=_DOCS_URL,
        check=changelog_exists_check,
        overridable=True,
    ),
]
