"""YAML-backed advisory loader for HassCheck deprecation advisories."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from hasscheck.advisories.model import Advisory

# Exposed as a module-level variable so tests can patch it.
_DATA_DIR: Path = Path(__file__).parent / "data"


def _load_all() -> dict[str, Advisory]:
    """Load all advisory YAML files from _DATA_DIR.

    Returns a dict keyed by advisory id.
    Raises RuntimeError (wrapping FileNotFoundError or ValidationError) on
    any loading or validation failure — fail-loud at import time.
    """
    data_dir = _DATA_DIR

    if not data_dir.is_dir():
        raise RuntimeError(
            f"Advisory data directory not found: {data_dir}. "
            "This indicates a packaging problem — the YAML advisory files "
            "were not included in the installed package."
        )

    advisories: dict[str, Advisory] = {}

    for yaml_path in sorted(data_dir.glob("*.yaml")):
        try:
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise RuntimeError(
                f"Failed to read advisory file {yaml_path.name}: {exc}"
            ) from exc

        try:
            advisory = Advisory.model_validate(raw)
        except ValidationError as exc:
            raise RuntimeError(
                f"Advisory file {yaml_path.name} failed validation: {exc}"
            ) from exc

        advisories[advisory.id] = advisory

    return advisories


# Eager module-level load — matches RULES pattern.
# Fails loud at import time on packaging issues.
ADVISORIES: dict[str, Advisory] = _load_all()


def get_advisory(advisory_id: str) -> Advisory | None:
    """Return the Advisory for the given id, or None if not found."""
    return ADVISORIES.get(advisory_id)
