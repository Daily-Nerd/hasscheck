"""Target identity detection for hasscheck reports.

Reads integration manifest, git tags, and GitHub Actions environment variables
to detect the exact-build identity of the integration under check.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from hasscheck.models import ReportTarget, ReportValidity


def detect_target(
    root: Path,
    integration_path: Path | None,
    domain: str | None,
) -> ReportTarget | None:
    """Detect exact-build identity for the integration under check.

    Reads env vars (GITHUB_REF, GITHUB_SHA) internally. Never raises.
    Returns a ReportTarget with whichever fields detection could fill
    (others left as defaults).

    Detection priority for ``integration_version`` (first-match-wins):
        1. manifest.json["version"]             → source = "manifest"
        2. git describe --tags --exact-match HEAD → source = "git_tag"
        3. GITHUB_REF matches refs/tags/*        → source = "github_release"
        4. HACS metadata (deferred; always None this PR) → "hacs_metadata"
        5. None                                  → source = "unknown"

    Other fields populate independently:
        - commit_sha     ← os.environ["GITHUB_SHA"] (None outside CI)
        - python_version ← sys.version_info major.minor.patch (D11)
        - ha_version     ← None this PR (D12)
        - check_mode     ← "static"
        - integration_domain ← domain parameter
    """
    try:
        integration_version: str | None = None
        integration_version_source = "unknown"
        integration_release_tag: str | None = None
        manifest_hash: str | None = None
        requirements_hash: str | None = None

        # --- Step 1: manifest.json ---
        if integration_path is not None:
            version, manifest_hash, requirements_hash = read_manifest_version(
                integration_path
            )
            if version is not None:
                integration_version = version
                integration_version_source = "manifest"

        # --- Step 2: git describe (only if manifest didn't win) ---
        if integration_version is None:
            git_tag = _git_describe_tag(root)
            if git_tag is not None:
                integration_version = git_tag
                integration_version_source = "git_tag"

        # --- Step 3: GITHUB_REF env (only if still no winner) ---
        if integration_version is None:
            ref_tag = _github_release_tag()
            if ref_tag is not None:
                integration_version = ref_tag
                integration_version_source = "github_release"
                integration_release_tag = ref_tag

        # --- Step 4: HACS metadata stub (always None in this PR) ---
        if integration_version is None:
            _hacs_metadata_version()  # always returns None; reserved for future

        # --- Independent fields ---
        commit_sha = os.environ.get("GITHUB_SHA")
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        return ReportTarget(
            integration_domain=domain,
            integration_version=integration_version,
            integration_version_source=integration_version_source,  # type: ignore[arg-type]
            integration_release_tag=integration_release_tag,
            commit_sha=commit_sha,
            ha_version=None,  # D12: always None in this PR
            python_version=python_version,
            check_mode="static",
            manifest_hash=manifest_hash,
            requirements_hash=requirements_hash,
        )
    except Exception:  # noqa: BLE001
        # detect_target MUST NEVER raise
        return None


def build_validity(checked_at: datetime) -> ReportValidity:
    """Build a ReportValidity with frozen claim_scope and 90-day expiry.

    ``superseded_by_integration_version`` is ALWAYS None from CLI; the hub
    sets it after indexing (mirrors Provenance.verified_by).
    """
    return ReportValidity(
        claim_scope="exact_build_only",
        checked_at=checked_at,
        expires_after_days=90,
        superseded_by_integration_version=None,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def read_manifest_version(
    integration_path: Path,
) -> tuple[str | None, str | None, str | None]:
    """Read version, manifest_hash, and requirements_hash from manifest.json.

    Returns (version, manifest_hash, requirements_hash).
    Any IO or parse error → returns (None, None, None).
    """
    try:
        manifest_file = integration_path / "manifest.json"
        raw_bytes = manifest_file.read_bytes()
        manifest_hash = _compute_manifest_hash(raw_bytes)
        data = json.loads(raw_bytes)
        version = data.get("version") or None
        requirements = data.get("requirements")
        requirements_hash = _compute_requirements_hash(requirements)
        return version, manifest_hash, requirements_hash
    except Exception:  # noqa: BLE001
        return None, None, None


def _compute_manifest_hash(raw_bytes: bytes) -> str:
    """Return SHA-256 hex digest of the manifest raw bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()


def _compute_requirements_hash(requirements: list[str] | None) -> str | None:
    """Compute SHA-256 of LF-joined sorted normalized PEP 508 strings.

    Normalization:
    - Package name: lowercased, hyphens/underscores unified via canonicalize_name.
    - Whitespace around specifiers: stripped by Requirement.__str__.
    - Extras: normalized to lowercase, sorted (packaging behaviour).
    - Invalid PEP 508 entries: used as-is (raw string fallback).

    Empty list or None → returns None.
    """
    if not requirements:
        return None
    normalized: list[str] = []
    for req_str in requirements:
        try:
            req = Requirement(req_str)
            req.name = canonicalize_name(req.name)
            normalized.append(str(req))
        except InvalidRequirement:
            normalized.append(req_str)
    joined = "\n".join(sorted(normalized))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _git_describe_tag(root: Path) -> str | None:
    """Run git describe --tags --exact-match HEAD (D6 exact invocation).

    Returns the tag string on success, None on any failure.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "describe", "--tags", "--exact-match", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if result.returncode != 0:
            return None
        tag = result.stdout.strip()
        return tag if tag else None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _github_release_tag() -> str | None:
    """Extract release tag from GITHUB_REF env if it points to a tag.

    Returns "v3.0.0" for GITHUB_REF="refs/tags/v3.0.0", else None.
    """
    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/"):
        return ref[len("refs/tags/") :]
    return None


def _latest_version_tag(root: Path) -> str | None:
    """Return the most-recent git tag name reachable from HEAD, or None.

    Uses ``git describe --tags --abbrev=0`` (ADR-0003). Returns None on:
      - no .git directory
      - git binary missing
      - no tags
      - subprocess timeout / OSError / SubprocessError
    """
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "describe", "--tags", "--abbrev=0"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if result.returncode != 0:
            return None
        tag = result.stdout.strip()
        return tag if tag else None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _hacs_metadata_version() -> None:
    """HACS metadata version detection stub.

    Detection deferred; falls through to next source. See ADR 0013 §Consequences.
    Always returns None in this PR. Reserved as Literal value "hacs_metadata".
    """
    return None
