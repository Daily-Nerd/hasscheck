"""Provenance detection for hasscheck reports.

Reads GitHub Actions environment variables (or falls back to "local") and
returns a populated :class:`~hasscheck.models.Provenance` instance.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from hasscheck.models import Provenance


def detect_provenance(now: datetime | None = None) -> Provenance:
    """Detect the execution context and return a :class:`Provenance` instance.

    Args:
        now: Optional datetime to use as ``published_at``. Defaults to
             ``datetime.now(timezone.utc)``. Inject a fixed value in tests for
             deterministic assertions.

    Returns:
        A :class:`Provenance` populated from environment variables.
        ``verified_by`` is always ``None`` — only the hosted hub sets that field
        after OIDC validation.
    """
    _now = now or datetime.now(UTC)
    published_at = _now.isoformat()

    if os.environ.get("GITHUB_ACTIONS") != "true":
        return Provenance(source="local", published_at=published_at)

    run_attempt: int | None = None
    raw = os.environ.get("GITHUB_RUN_ATTEMPT")
    if raw is not None:
        try:
            run_attempt = int(raw)
        except ValueError:
            pass

    return Provenance(
        source="github_actions",
        repository=os.environ.get("GITHUB_REPOSITORY"),
        commit_sha=os.environ.get("GITHUB_SHA"),
        ref=os.environ.get("GITHUB_REF"),
        workflow=os.environ.get("GITHUB_WORKFLOW"),
        run_id=os.environ.get("GITHUB_RUN_ID"),
        run_attempt=run_attempt,
        actor=os.environ.get("GITHUB_ACTOR"),
        published_at=published_at,
        verified_by=None,
    )
