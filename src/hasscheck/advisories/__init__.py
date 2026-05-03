"""Advisory model and loader for HassCheck deprecation advisories."""

from __future__ import annotations

from hasscheck.advisories.loader import ADVISORIES, get_advisory
from hasscheck.advisories.model import Advisory

__all__ = ["Advisory", "ADVISORIES", "get_advisory"]
