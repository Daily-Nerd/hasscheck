"""Tests for hasscheck.provenance — detect_provenance() detection logic.

TDD order: all tests written RED before provenance.py exists.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hasscheck.provenance import detect_provenance

# ---------- 2.1 GitHub Actions: full context ----------


def test_github_actions_full_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """GITHUB_ACTIONS=true + all GITHUB_* vars → source="github_actions", all fields set, verified_by None."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_SHA", "abc123def456")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
    monkeypatch.setenv("GITHUB_RUN_ID", "9876543210")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_ACTOR", "octocat")

    result = detect_provenance()

    assert result.source == "github_actions"
    assert result.repository == "owner/repo"
    assert result.commit_sha == "abc123def456"
    assert result.ref == "refs/heads/main"
    assert result.workflow == "CI"
    assert result.run_id == "9876543210"
    assert result.run_attempt == 1
    assert result.actor == "octocat"
    assert result.published_at is not None
    assert result.verified_by is None


# ---------- 2.2 Local context: no env vars ----------


def test_local_context_no_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """No GITHUB_ACTIONS → source="local", env fields None, published_at not None."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("GITHUB_REF", raising=False)
    monkeypatch.delenv("GITHUB_WORKFLOW", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ATTEMPT", raising=False)
    monkeypatch.delenv("GITHUB_ACTOR", raising=False)

    result = detect_provenance()

    assert result.source == "local"
    assert result.repository is None
    assert result.commit_sha is None
    assert result.ref is None
    assert result.workflow is None
    assert result.run_id is None
    assert result.run_attempt is None
    assert result.actor is None
    assert result.published_at is not None


# ---------- 2.3 run_attempt coercion: string "2" → int 2 ----------


def test_run_attempt_coercion_to_int(monkeypatch: pytest.MonkeyPatch) -> None:
    """GITHUB_RUN_ATTEMPT="2" → run_attempt == 2 (int)."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")

    result = detect_provenance()

    assert result.run_attempt == 2
    assert isinstance(result.run_attempt, int)


# ---------- 2.4 run_attempt coercion: bad string → None, no exception ----------


def test_run_attempt_bad_string_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """GITHUB_RUN_ATTEMPT="bad" → run_attempt is None, no exception raised."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "bad")

    result = detect_provenance()

    assert result.run_attempt is None


# ---------- 2.5 Partial GitHub Actions context ----------


def test_github_actions_partial_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """GITHUB_ACTIONS=true but some vars missing → best-effort, missing = None, no exception."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("GITHUB_REF", raising=False)
    monkeypatch.delenv("GITHUB_WORKFLOW", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ATTEMPT", raising=False)
    monkeypatch.delenv("GITHUB_ACTOR", raising=False)

    result = detect_provenance()

    assert result.source == "github_actions"
    assert result.repository == "owner/repo"
    assert result.commit_sha is None
    assert result.ref is None
    assert result.workflow is None
    assert result.run_id is None
    assert result.run_attempt is None
    assert result.actor is None


# ---------- 2.6 Injectable now parameter ----------


def test_now_param_injectable(monkeypatch: pytest.MonkeyPatch) -> None:
    """inject explicit now → published_at matches injected datetime."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    fixed_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
    result = detect_provenance(now=fixed_dt)

    assert result.published_at == fixed_dt.isoformat()


def test_now_param_injectable_github_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """inject now in GitHub Actions context → published_at matches injected datetime."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")

    fixed_dt = datetime(2025, 6, 20, 8, 30, 0, tzinfo=UTC)
    result = detect_provenance(now=fixed_dt)

    assert result.published_at == fixed_dt.isoformat()


# ---------- 2.7 verified_by always None ----------


def test_verified_by_is_none_in_github_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """verified_by is None in GitHub Actions context."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    result = detect_provenance()

    assert result.verified_by is None


def test_verified_by_is_none_in_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """verified_by is None in local context."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    result = detect_provenance()

    assert result.verified_by is None
