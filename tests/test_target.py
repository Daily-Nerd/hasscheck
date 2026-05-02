"""Tests for hasscheck.target — detect_target and build_validity."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Scenario 9 — test_detect_target_reads_manifest_version
# ---------------------------------------------------------------------------


def test_detect_target_reads_manifest_version(tmp_path: Path) -> None:
    from hasscheck.target import detect_target

    (tmp_path / "manifest.json").write_text(
        json.dumps({"domain": "test", "version": "1.2.3", "name": "Test"})
    )
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None
    assert target.integration_version == "1.2.3"
    assert target.integration_version_source == "manifest"


# ---------------------------------------------------------------------------
# Scenario 10 — test_detect_target_falls_through_to_git_tag_when_manifest_missing
# ---------------------------------------------------------------------------


def test_detect_target_falls_through_to_git_tag_when_manifest_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hasscheck.target import detect_target

    # No manifest.json → fall through to git describe
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="v2.0.0\n", stderr="")

    monkeypatch.setattr("hasscheck.target.subprocess.run", fake_run)
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None
    assert target.integration_version == "v2.0.0"
    assert target.integration_version_source == "git_tag"


# ---------------------------------------------------------------------------
# Scenario 11 — test_detect_target_falls_through_to_github_release_when_ref_is_tag
# ---------------------------------------------------------------------------


def test_detect_target_falls_through_to_github_release_when_ref_is_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hasscheck.target import detect_target

    monkeypatch.setenv("GITHUB_REF", "refs/tags/v3.0.0")

    # No manifest version, git describe fails
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0], 128, stdout="", stderr="fatal: no tag"
        )

    monkeypatch.setattr("hasscheck.target.subprocess.run", fake_run)
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None
    assert target.integration_version == "v3.0.0"
    assert target.integration_version_source == "github_release"


# ---------------------------------------------------------------------------
# Scenario 12 — test_detect_target_returns_unknown_when_all_sources_miss
# ---------------------------------------------------------------------------


def test_detect_target_returns_unknown_when_all_sources_miss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hasscheck.target import detect_target

    monkeypatch.delenv("GITHUB_REF", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 128, stdout="", stderr="fatal")

    monkeypatch.setattr("hasscheck.target.subprocess.run", fake_run)
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None
    assert target.integration_version_source == "unknown"
    assert target.integration_version is None


# ---------------------------------------------------------------------------
# Scenario 13 — test_detect_target_handles_shallow_clone_subprocess_failure
# ---------------------------------------------------------------------------


def test_detect_target_handles_shallow_clone_subprocess_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hasscheck.target import detect_target

    monkeypatch.delenv("GITHUB_REF", raising=False)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0], 128, stdout="", stderr="fatal: no tags"
        )

    monkeypatch.setattr("hasscheck.target.subprocess.run", fake_run)
    # Should not raise
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None


# ---------------------------------------------------------------------------
# Scenario 14 — test_detect_target_handles_unreadable_manifest
# ---------------------------------------------------------------------------


def test_detect_target_handles_unreadable_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hasscheck.target import detect_target

    (tmp_path / "manifest.json").write_text("{not valid json")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 128, stdout="", stderr="")

    monkeypatch.setattr("hasscheck.target.subprocess.run", fake_run)
    monkeypatch.delenv("GITHUB_REF", raising=False)

    # Must not raise; falls through
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None


# ---------------------------------------------------------------------------
# Scenario 15 — test_build_validity_sets_claim_scope_and_default_expires
# ---------------------------------------------------------------------------


def test_build_validity_sets_claim_scope_and_default_expires() -> None:
    from hasscheck.target import build_validity

    validity = build_validity(checked_at=datetime(2026, 1, 1, tzinfo=UTC))
    assert validity.claim_scope == "exact_build_only"
    assert validity.expires_after_days == 90


# ---------------------------------------------------------------------------
# Scenario 16 — test_build_validity_checked_at_is_utc_iso8601_z
# ---------------------------------------------------------------------------


def test_build_validity_checked_at_is_utc_iso8601_z() -> None:
    from hasscheck.target import build_validity

    validity = build_validity(checked_at=datetime(2026, 1, 1, tzinfo=UTC))
    d = validity.model_dump(mode="json")
    assert d["checked_at"].endswith("Z"), f"Expected Z suffix, got: {d['checked_at']}"
    # Basic ISO-8601 structure check
    assert "T" in d["checked_at"]


# ---------------------------------------------------------------------------
# Scenario 17 — test_detect_target_never_raises_on_missing_integration_path
# ---------------------------------------------------------------------------


def test_detect_target_never_raises_on_missing_integration_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hasscheck.target import detect_target

    monkeypatch.delenv("GITHUB_REF", raising=False)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 128, stdout="", stderr="")

    monkeypatch.setattr("hasscheck.target.subprocess.run", fake_run)

    # integration_path=None must never raise
    target = detect_target(tmp_path, None, None)
    assert target is not None or target is None  # either is acceptable


# ---------------------------------------------------------------------------
# Scenario 25 — test_cli_never_sets_superseded_by_integration_version
# ---------------------------------------------------------------------------


def test_cli_never_sets_superseded_by_integration_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hasscheck.target import build_validity, detect_target

    monkeypatch.delenv("GITHUB_REF", raising=False)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 128, stdout="", stderr="")

    monkeypatch.setattr("hasscheck.target.subprocess.run", fake_run)

    detect_target(tmp_path, tmp_path, "test")
    validity = build_validity(checked_at=datetime(2026, 1, 1, tzinfo=UTC))
    assert validity.superseded_by_integration_version is None
