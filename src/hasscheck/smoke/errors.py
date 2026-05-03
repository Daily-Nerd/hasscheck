"""Smoke harness exception hierarchy."""

from __future__ import annotations


class SmokeError(Exception):
    """Base class for all smoke harness errors."""


class SmokeTimeoutError(SmokeError):
    """Raised when a subprocess invocation exceeds its timeout budget."""


class SmokeRunnerMissingError(SmokeError):
    """Raised when a required binary (e.g. uv) is absent from PATH."""
