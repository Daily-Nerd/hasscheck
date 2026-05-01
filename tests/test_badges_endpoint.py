"""Golden-file tests for to_shields_endpoint()."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hasscheck.badges.endpoint import to_shields_endpoint
from hasscheck.badges.status import BadgeStatus

GOLDEN_DIR = Path(__file__).parent / "badges_golden" / "endpoint"

CASES = [
    (
        "hacs_structure__passing",
        BadgeStatus(
            category_id="hacs_structure",
            label_left="HACS Structure",
            label_right="Passing",
            color="brightgreen",
        ),
    ),
    (
        "hacs_structure__partial",
        BadgeStatus(
            category_id="hacs_structure",
            label_left="HACS Structure",
            label_right="Partial",
            color="yellow",
        ),
    ),
    (
        "hacs_structure__issues",
        BadgeStatus(
            category_id="hacs_structure",
            label_left="HACS Structure",
            label_right="Issues",
            color="red",
        ),
    ),
]


@pytest.mark.parametrize("name,status", CASES)
def test_endpoint_matches_golden(name: str, status: BadgeStatus) -> None:
    golden_path = GOLDEN_DIR / f"{name}.json"
    actual = json.dumps(to_shields_endpoint(status), sort_keys=True, indent=2) + "\n"

    if os.environ.get("UPDATE_GOLDENS") == "1":
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(actual, encoding="utf-8")
        return

    assert golden_path.exists(), (
        f"Golden file {golden_path} not found. "
        "Run with UPDATE_GOLDENS=1 to generate it."
    )
    expected = golden_path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"Output for {name!r} does not match golden.\n"
        f"Expected:\n{expected}\nActual:\n{actual}"
    )
