"""Shared fixtures for the smoke test suite."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _make_integration(tmp_path: Path) -> Path:
    """Create a minimal integration structure for smoke tests.

    Returns the repo root (containing custom_components/foo/).
    """
    integration = tmp_path / "custom_components" / "foo"
    integration.mkdir(parents=True)
    (integration / "__init__.py").write_text("", encoding="utf-8")
    manifest = {
        "domain": "foo",
        "name": "Foo",
        "documentation": "https://example.com",
        "issue_tracker": "https://example.com/issues",
        "codeowners": ["@foo"],
        "version": "0.1.0",
        "requirements": [],
    }
    (integration / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def integration_repo(tmp_path: Path) -> Path:
    """Fixture: a minimal integration repository under tmp_path."""
    return _make_integration(tmp_path)


@pytest.fixture()
def fake_run_success():
    """Fixture: a subprocess.run fake that always returns (rc=0, stdout='', stderr='')."""

    def _fake(*args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    return _fake
