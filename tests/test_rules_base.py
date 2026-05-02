"""Tests for hasscheck.rules.base — ProjectContext version identity fields.

TDD cycle:
  - RED: written first, before production code exists
  - GREEN: confirmed after implementation

Spec: issue #142 — version identity fields on ProjectContext.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_project_context_accepts_version_identity_fields() -> None:
    """Constructing ProjectContext with all 4 new kwargs must succeed."""
    from hasscheck.rules.base import ProjectContext

    ctx = ProjectContext(
        root=Path("/tmp/integration"),
        integration_path=Path("/tmp/integration/custom_components/demo"),
        domain="demo",
        integration_version="1.2.3",
        integration_version_source="manifest",
        integration_release_tag="v1.2.3",
        commit_sha="abc123def456",
    )

    assert ctx.integration_version == "1.2.3"
    assert ctx.integration_version_source == "manifest"
    assert ctx.integration_release_tag == "v1.2.3"
    assert ctx.commit_sha == "abc123def456"


def test_project_context_version_fields_default_to_none() -> None:
    """All 4 new fields must default when not provided."""
    from hasscheck.rules.base import ProjectContext

    ctx = ProjectContext(
        root=Path("/tmp/integration"),
        integration_path=None,
        domain=None,
    )

    assert ctx.integration_version is None
    assert ctx.integration_version_source == "unknown"
    assert ctx.integration_release_tag is None
    assert ctx.commit_sha is None


def test_project_context_version_fields_are_immutable() -> None:
    """FrozenInstanceError must be raised on write attempt."""
    from dataclasses import FrozenInstanceError

    from hasscheck.rules.base import ProjectContext

    ctx = ProjectContext(
        root=Path("/tmp/integration"),
        integration_path=None,
        domain=None,
    )

    with pytest.raises(FrozenInstanceError):
        ctx.integration_version = "1.2.3"  # type: ignore[misc]
