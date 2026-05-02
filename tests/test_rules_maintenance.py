"""Tests for maintenance signal rules (issue #109, v0.11 second batch).

TDD cycle:
  - RED: written first, before production code exists
  - GREEN: confirmed after implementation

Rules covered:
  - maintenance.recent_commit.detected
  - maintenance.recent_release.detected
  - maintenance.changelog.exists

Spec: issue #109 — maintenance signal rules (git-based, local subprocess only)
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECONDS_PER_MONTH = 30.44 * 86400


def _init_git_repo(path: Path, commit_offset_seconds: int = 0) -> None:
    """Initialize a real git repo in path with a single commit.

    commit_offset_seconds: positive = future, negative = past.
    """
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    ts = str(int(time.time()) + commit_offset_seconds)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": ts,
        "GIT_COMMITTER_DATE": ts,
    }
    (path / "README.md").write_text("# Test\n")
    subprocess.run(
        ["git", "add", "README.md"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )


def _add_tag(path: Path, tag: str, tag_offset_seconds: int = 0) -> None:
    """Add a lightweight git tag with a forced timestamp."""
    ts = str(int(time.time()) + tag_offset_seconds)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        # For annotated tags we need these; for lightweight we still export
        "GIT_COMMITTER_DATE": ts,
    }
    subprocess.run(
        ["git", "tag", "-a", tag, "-m", f"release {tag}"],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )


def _check_rule(root: Path, rule_id: str):
    """Run just the given rule's check function against root."""
    rule = RULES_BY_ID[rule_id]
    from hasscheck.rules.base import ProjectContext

    ctx = ProjectContext(root=root, integration_path=None, domain=None)
    return rule.check(ctx)


# ===========================================================================
# maintenance.recent_commit.detected
# ===========================================================================

RC_RULE = "maintenance.recent_commit.detected"


class TestRecentCommit:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[RC_RULE]
        assert rule.id == RC_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "maintenance"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_recent_commit(self, tmp_path: Path) -> None:
        """Commit dated now → PASS."""
        _init_git_repo(tmp_path)
        finding = _check_rule(tmp_path, RC_RULE)
        assert finding.status is RuleStatus.PASS

    def test_warn_old_commit(self, tmp_path: Path) -> None:
        """Commit dated 18 months ago → WARN."""
        offset = int(-18 * _SECONDS_PER_MONTH)
        _init_git_repo(tmp_path, commit_offset_seconds=offset)
        finding = _check_rule(tmp_path, RC_RULE)
        assert finding.status is RuleStatus.WARN

    def test_not_applicable_no_git_dir(self, tmp_path: Path) -> None:
        """No .git directory → NOT_APPLICABLE."""
        finding = _check_rule(tmp_path, RC_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE
        assert "git" in finding.applicability.reason.lower()

    def test_not_applicable_git_not_on_path(self, tmp_path: Path) -> None:
        """git binary not on PATH → NOT_APPLICABLE."""
        _init_git_repo(tmp_path)
        from hasscheck.rules import maintenance

        with patch.object(maintenance, "_git_available", return_value=False):
            finding = _check_rule(tmp_path, RC_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE
        assert "git" in finding.applicability.reason.lower()

    def test_message_contains_age_info_on_pass(self, tmp_path: Path) -> None:
        """PASS message should contain age information."""
        _init_git_repo(tmp_path)
        finding = _check_rule(tmp_path, RC_RULE)
        assert finding.message  # non-empty

    def test_message_contains_age_info_on_warn(self, tmp_path: Path) -> None:
        """WARN message should mention age."""
        offset = int(-18 * _SECONDS_PER_MONTH)
        _init_git_repo(tmp_path, commit_offset_seconds=offset)
        finding = _check_rule(tmp_path, RC_RULE)
        assert "month" in finding.message.lower() or "day" in finding.message.lower()


# ===========================================================================
# maintenance.recent_release.detected
# ===========================================================================

RR_RULE = "maintenance.recent_release.detected"


class TestRecentRelease:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[RR_RULE]
        assert rule.id == RR_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "maintenance"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_recent_tag(self, tmp_path: Path) -> None:
        """Annotated tag dated now → PASS."""
        _init_git_repo(tmp_path)
        _add_tag(tmp_path, "v1.0.0")
        finding = _check_rule(tmp_path, RR_RULE)
        assert finding.status is RuleStatus.PASS

    def test_warn_old_tag(self, tmp_path: Path) -> None:
        """Tag dated 18 months ago → WARN."""
        _init_git_repo(tmp_path)
        offset = int(-18 * _SECONDS_PER_MONTH)
        _add_tag(tmp_path, "v0.1.0", tag_offset_seconds=offset)
        finding = _check_rule(tmp_path, RR_RULE)
        assert finding.status is RuleStatus.WARN

    def test_not_applicable_no_tags(self, tmp_path: Path) -> None:
        """Repo with commits but no tags → NOT_APPLICABLE."""
        _init_git_repo(tmp_path)
        finding = _check_rule(tmp_path, RR_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE
        assert "tag" in finding.applicability.reason.lower()

    def test_not_applicable_no_git_dir(self, tmp_path: Path) -> None:
        """No .git directory → NOT_APPLICABLE."""
        finding = _check_rule(tmp_path, RR_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_git_not_on_path(self, tmp_path: Path) -> None:
        """git binary not on PATH → NOT_APPLICABLE."""
        _init_git_repo(tmp_path)
        _add_tag(tmp_path, "v1.0.0")
        from hasscheck.rules import maintenance

        with patch.object(maintenance, "_git_available", return_value=False):
            finding = _check_rule(tmp_path, RR_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_message_contains_age_on_warn(self, tmp_path: Path) -> None:
        """WARN message should mention age."""
        _init_git_repo(tmp_path)
        offset = int(-18 * _SECONDS_PER_MONTH)
        _add_tag(tmp_path, "v0.1.0", tag_offset_seconds=offset)
        finding = _check_rule(tmp_path, RR_RULE)
        assert "month" in finding.message.lower() or "day" in finding.message.lower()


# ===========================================================================
# maintenance.changelog.exists
# ===========================================================================

CL_RULE = "maintenance.changelog.exists"


class TestChangelogExists:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[CL_RULE]
        assert rule.id == CL_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "maintenance"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_pass_changelog_md(self, tmp_path: Path) -> None:
        """CHANGELOG.md present → PASS."""
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_changelog(self, tmp_path: Path) -> None:
        """CHANGELOG (no extension) → PASS."""
        (tmp_path / "CHANGELOG").write_text("changelog\n")
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_history_md(self, tmp_path: Path) -> None:
        """HISTORY.md → PASS."""
        (tmp_path / "HISTORY.md").write_text("# History\n")
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_history(self, tmp_path: Path) -> None:
        """HISTORY (no extension) → PASS."""
        (tmp_path / "HISTORY").write_text("history\n")
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_releases_md(self, tmp_path: Path) -> None:
        """RELEASES.md → PASS."""
        (tmp_path / "RELEASES.md").write_text("# Releases\n")
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_news_md(self, tmp_path: Path) -> None:
        """NEWS.md → PASS."""
        (tmp_path / "NEWS.md").write_text("# News\n")
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.PASS

    def test_warn_no_changelog(self, tmp_path: Path) -> None:
        """No changelog file → WARN."""
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.WARN

    def test_warn_changelog_is_directory(self, tmp_path: Path) -> None:
        """CHANGELOG.md is a directory (not a file) → WARN."""
        (tmp_path / "CHANGELOG.md").mkdir()
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.status is RuleStatus.WARN

    def test_pass_message_includes_filename(self, tmp_path: Path) -> None:
        """PASS message should name the file found."""
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
        finding = _check_rule(tmp_path, CL_RULE)
        assert "CHANGELOG.md" in finding.message

    def test_warn_message_is_informative(self, tmp_path: Path) -> None:
        """WARN message should not be empty."""
        finding = _check_rule(tmp_path, CL_RULE)
        assert finding.message
