"""GitHub `owner/repo` slug detection from git remote or manifest fallback."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# Accepted forms:
#   https://github.com/owner/repo[.git]
#   http://github.com/owner/repo[.git]
#   git@github.com:owner/repo[.git]
#   ssh://git@github.com[:port]/owner/repo[.git]
_GITHUB_URL_RE = re.compile(
    r"""
    (?:https?://github\.com/|
       git@github\.com:|
       ssh://git@github\.com(?::\d+)?/)
    (?P<owner>[A-Za-z0-9._-]+)/
    (?P<repo>[A-Za-z0-9._-]+?)
    (?:\.git)?
    /?$
    """,
    re.VERBOSE,
)


def _parse_github_url(url: str) -> str | None:
    match = _GITHUB_URL_RE.search(url.strip())
    if match is None:
        return None
    return f"{match.group('owner')}/{match.group('repo')}"


def _from_git_remote(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return _parse_github_url(result.stdout)


def _from_manifest(integration_path: Path | None) -> str | None:
    if integration_path is None:
        return None
    manifest = integration_path / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    issue_tracker = data.get("issue_tracker") if isinstance(data, dict) else None
    if not isinstance(issue_tracker, str):
        return None
    parsed = _parse_github_url(
        issue_tracker.removesuffix("/issues").removesuffix("/issues/")
    )
    return parsed


def detect_repo_slug(root: Path, integration_path: Path | None = None) -> str | None:
    """Best-effort `owner/repo` detection.

    Tries `git remote get-url origin` first, then falls back to the manifest's
    `issue_tracker` URL when it points at github.com. Returns None if neither
    source yields a valid slug.

    Authoritative slug at publish time comes from the GitHub OIDC token's
    `repository` claim — this function exists for local CLI display and the
    `hasscheck publish` pre-flight only.
    """
    return _from_git_remote(root) or _from_manifest(integration_path)
