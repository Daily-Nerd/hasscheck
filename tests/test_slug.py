import json
import subprocess
from pathlib import Path

import pytest

from hasscheck.slug import _parse_github_url, detect_repo_slug


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo", "owner/repo"),
        ("https://github.com/owner/repo/", "owner/repo"),
        ("http://github.com/owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo", "owner/repo"),
        ("ssh://git@github.com/owner/repo.git", "owner/repo"),
        ("ssh://git@github.com:22/owner/repo.git", "owner/repo"),
        ("https://github.com/Daily-Nerd/hasscheck.git", "Daily-Nerd/hasscheck"),
        ("https://github.com/owner/repo.with.dots", "owner/repo.with.dots"),
        ("https://github.com/owner/repo-with-dashes", "owner/repo-with-dashes"),
        (
            "https://github.com/owner/repo_with_underscores",
            "owner/repo_with_underscores",
        ),
    ],
)
def test_parse_github_url_accepts_common_forms(url, expected):
    assert _parse_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/owner/repo.git",
        "https://bitbucket.org/owner/repo.git",
        "https://example.com/owner/repo",
        "not a url",
        "",
        "https://github.com/owner",
        "https://github.com/",
    ],
)
def test_parse_github_url_rejects_non_github_or_malformed(url):
    assert _parse_github_url(url) is None


def _init_git_remote(root: Path, url: str) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", url],
        check=True,
    )


def test_detect_repo_slug_from_git_remote_https(tmp_path):
    _init_git_remote(tmp_path, "https://github.com/Daily-Nerd/hasscheck.git")
    assert detect_repo_slug(tmp_path) == "Daily-Nerd/hasscheck"


def test_detect_repo_slug_from_git_remote_ssh(tmp_path):
    _init_git_remote(tmp_path, "git@github.com:Daily-Nerd/hasscheck.git")
    assert detect_repo_slug(tmp_path) == "Daily-Nerd/hasscheck"


def test_detect_repo_slug_returns_none_when_no_git(tmp_path):
    assert detect_repo_slug(tmp_path) is None


def test_detect_repo_slug_returns_none_when_remote_missing(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert detect_repo_slug(tmp_path) is None


def test_detect_repo_slug_returns_none_for_non_github_remote(tmp_path):
    _init_git_remote(tmp_path, "https://gitlab.com/owner/repo.git")
    assert detect_repo_slug(tmp_path) is None


def test_detect_repo_slug_falls_back_to_manifest_issue_tracker(tmp_path):
    integration = tmp_path / "custom_components" / "my_integration"
    integration.mkdir(parents=True)
    manifest = integration / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "domain": "my_integration",
                "name": "My Integration",
                "issue_tracker": "https://github.com/Daily-Nerd/hasscheck/issues",
            }
        )
    )
    assert detect_repo_slug(tmp_path, integration) == "Daily-Nerd/hasscheck"


def test_detect_repo_slug_prefers_git_remote_over_manifest(tmp_path):
    integration = tmp_path / "custom_components" / "my_integration"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "my_integration",
                "issue_tracker": "https://github.com/owner-from-manifest/repo/issues",
            }
        )
    )
    _init_git_remote(tmp_path, "https://github.com/owner-from-git/repo.git")
    assert detect_repo_slug(tmp_path, integration) == "owner-from-git/repo"


def test_detect_repo_slug_handles_malformed_manifest(tmp_path):
    integration = tmp_path / "custom_components" / "my_integration"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text("not valid json {")
    assert detect_repo_slug(tmp_path, integration) is None


def test_detect_repo_slug_handles_manifest_without_issue_tracker(tmp_path):
    integration = tmp_path / "custom_components" / "my_integration"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(json.dumps({"domain": "x"}))
    assert detect_repo_slug(tmp_path, integration) is None


def test_detect_repo_slug_handles_non_github_issue_tracker(tmp_path):
    integration = tmp_path / "custom_components" / "my_integration"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"issue_tracker": "https://example.com/tickets"})
    )
    assert detect_repo_slug(tmp_path, integration) is None
