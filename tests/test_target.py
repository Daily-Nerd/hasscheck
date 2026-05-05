"""Tests for hasscheck.target — detect_target and build_validity."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from hasscheck.target import _compute_requirements_hash

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

    # integration_path=None must never raise; helpers fall through to "unknown"
    target = detect_target(tmp_path, None, None)
    assert target is not None
    assert target.integration_domain is None
    assert target.integration_version is None
    assert target.integration_version_source == "unknown"


# ---------------------------------------------------------------------------
# Scenario 25 — test_cli_never_sets_superseded_by_integration_version
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Phase 4.1 RED — _latest_version_tag helper tests
# ---------------------------------------------------------------------------


def test_latest_version_tag_returns_none_when_no_git(tmp_path: Path) -> None:
    """No .git directory → must return None (not a git repo)."""
    from hasscheck.target import _latest_version_tag

    assert _latest_version_tag(tmp_path) is None


def test_latest_version_tag_returns_none_on_missing_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git binary not found → must return None gracefully."""
    from hasscheck.target import _latest_version_tag

    (tmp_path / ".git").mkdir()

    def raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("hasscheck.target.subprocess.run", raise_file_not_found)
    assert _latest_version_tag(tmp_path) is None


def test_latest_version_tag_returns_none_when_no_tags(tmp_path: Path) -> None:
    """git init but no commits/tags → must return None."""
    import subprocess as sp

    from hasscheck.target import _latest_version_tag

    sp.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    # No commits, no tags — git describe will fail
    assert _latest_version_tag(tmp_path) is None


def test_latest_version_tag_returns_tag_string() -> None:
    """Real git repo path with tags → must return a non-None string."""
    # Use the current repo which has real tags
    import subprocess as sp

    from hasscheck.target import _latest_version_tag

    repo_root = Path(__file__).parent.parent
    result = sp.run(
        ["git", "tag", "--list"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        pytest.skip("No tags in current repo — skipping integration test")

    tag = _latest_version_tag(repo_root)
    assert tag is not None
    assert isinstance(tag, str)
    assert len(tag) > 0


def test_latest_version_tag_handles_subprocess_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """subprocess.SubprocessError → must return None (no crash)."""
    import subprocess as sp

    from hasscheck.target import _latest_version_tag

    (tmp_path / ".git").mkdir()

    def raise_subprocess_error(*args, **kwargs):
        raise sp.SubprocessError("some error")

    monkeypatch.setattr("hasscheck.target.subprocess.run", raise_subprocess_error)
    assert _latest_version_tag(tmp_path) is None


# ---------------------------------------------------------------------------
# Phase 2.1 RED — public rename tests
# ---------------------------------------------------------------------------


def test_read_manifest_version_is_public(tmp_path: Path) -> None:
    """read_manifest_version must be importable as a public name from target."""
    from hasscheck.target import read_manifest_version  # noqa: F401

    assert callable(read_manifest_version)


def test_read_manifest_version_absent_private() -> None:
    """_read_manifest_version MUST NOT be importable by modules outside target.py."""
    import hasscheck.target as target_module

    # After the rename there should be no public symbol named _read_manifest_version
    assert not hasattr(target_module, "_read_manifest_version"), (
        "_read_manifest_version should not be exported from hasscheck.target"
    )


# ---------------------------------------------------------------------------
# Phase 2.3 RED — ReportTarget hash transport tests
# ---------------------------------------------------------------------------


def test_report_target_carries_hashes_internally(tmp_path: Path) -> None:
    """detect_target must pass manifest_hash and requirements_hash to ReportTarget."""
    import json

    from hasscheck.target import detect_target

    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "test",
                "version": "1.0.0",
                "name": "Test",
                "requirements": ["requests==2.0.0"],
            }
        )
    )
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None
    assert target.manifest_hash is not None, "manifest_hash should be set"
    assert target.requirements_hash is not None, "requirements_hash should be set"


def test_report_target_excludes_hashes_from_json(tmp_path: Path) -> None:
    """manifest_hash and requirements_hash must NOT appear in JSON output."""
    import json as json_mod

    from hasscheck.target import detect_target

    (tmp_path / "manifest.json").write_text(
        json_mod.dumps({"domain": "test", "version": "1.0.0", "name": "Test"})
    )
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None
    dumped = target.model_dump()
    assert "manifest_hash" not in dumped, "manifest_hash must be excluded from JSON"
    assert "requirements_hash" not in dumped, (
        "requirements_hash must be excluded from JSON"
    )


def test_report_target_json_excludes_hash_fields(tmp_path: Path) -> None:
    """model_dump_json() must not contain manifest_hash or requirements_hash."""
    import json as json_mod

    from hasscheck.target import detect_target

    (tmp_path / "manifest.json").write_text(
        json_mod.dumps(
            {
                "domain": "test",
                "version": "1.0.0",
                "name": "Test",
                "requirements": ["aiohttp==3.9.0"],
            }
        )
    )
    target = detect_target(tmp_path, tmp_path, "test")
    assert target is not None
    # Confirm the internal fields are set (transport works)
    assert target.manifest_hash is not None
    assert target.requirements_hash is not None
    # Confirm they do NOT appear in the JSON output (schema 0.5.0 stability)
    raw_json = json_mod.loads(target.model_dump_json())
    assert "manifest_hash" not in raw_json, (
        "manifest_hash must not appear in model_dump_json()"
    )
    assert "requirements_hash" not in raw_json, (
        "requirements_hash must not appear in model_dump_json()"
    )


# ---------------------------------------------------------------------------
# Scenario 25 (original)
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


# Phase 4.2 RED — #159 requirements_hash normalization


def test_requirements_hash_normalizes_whitespace() -> None:
    """Extra whitespace around specifiers must not change the hash."""
    h1 = _compute_requirements_hash(["aiohttp >= 3.0"])
    h2 = _compute_requirements_hash(["aiohttp>=3.0"])
    assert h1 == h2


def test_requirements_hash_normalizes_name_case() -> None:
    """Package name case must not change the hash."""
    h1 = _compute_requirements_hash(["Aiohttp>=3.0"])
    h2 = _compute_requirements_hash(["aiohttp>=3.0"])
    assert h1 == h2


def test_requirements_hash_normalizes_name_separator() -> None:
    """Hyphen/underscore in package name must not change the hash."""
    h1 = _compute_requirements_hash(["aiohttp_client>=1.0"])
    h2 = _compute_requirements_hash(["aiohttp-client>=1.0"])
    assert h1 == h2


def test_requirements_hash_is_order_independent() -> None:
    """Input order must not change the hash."""
    h1 = _compute_requirements_hash(["a>=1", "b>=2"])
    h2 = _compute_requirements_hash(["b>=2", "a>=1"])
    assert h1 == h2


def test_requirements_hash_handles_invalid_pep508() -> None:
    """A non-PEP-508 string must not raise; result must be a valid hex string."""
    result = _compute_requirements_hash(["not-valid-requirement@!#$"])
    assert result is not None
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 hex


def test_requirements_hash_returns_none_for_empty_list() -> None:
    """Empty list must return None."""
    assert _compute_requirements_hash([]) is None


def test_requirements_hash_returns_none_for_none_input() -> None:
    """None input must return None."""
    assert _compute_requirements_hash(None) is None


def test_requirements_hash_handles_mixed_valid_and_invalid() -> None:
    """A list with both valid and invalid entries must return a hash without raising."""
    result = _compute_requirements_hash(
        ["requests>=2.0", "git+https://example.com/pkg.git"]
    )
    assert result is not None
    assert isinstance(result, str)
    assert len(result) == 64


# ---------------------------------------------------------------------------
# Issue #181 — ha_version threading through detect_target
# ---------------------------------------------------------------------------


def test_detect_target_passes_ha_version(tmp_path: Path) -> None:
    """detect_target passes ha_version=... to ReportTarget.ha_version (S4)."""
    import json as json_mod

    from hasscheck.target import detect_target

    (tmp_path / "manifest.json").write_text(
        json_mod.dumps({"domain": "test", "version": "1.0.0", "name": "Test"})
    )
    result = detect_target(tmp_path, tmp_path, "test", ha_version="2026.5.0")
    assert result is not None
    assert result.ha_version == "2026.5.0"


def test_detect_target_omitted_ha_version_is_none(tmp_path: Path) -> None:
    """Omitting ha_version leaves ReportTarget.ha_version as None (backward compat)."""
    import json as json_mod

    from hasscheck.target import detect_target

    (tmp_path / "manifest.json").write_text(
        json_mod.dumps({"domain": "test", "version": "1.0.0", "name": "Test"})
    )
    result = detect_target(tmp_path, tmp_path, "test")
    assert result is not None
    assert result.ha_version is None
