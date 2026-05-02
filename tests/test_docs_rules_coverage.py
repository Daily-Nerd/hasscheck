"""Meta-test: every registered rule has a docs/rules/<rule_id>.md page."""

from __future__ import annotations

from pathlib import Path

import pytest

from hasscheck.rules.registry import RULES_BY_ID

DOCS_DIR = Path(__file__).parent.parent / "docs" / "rules"


@pytest.mark.parametrize("rule_id", sorted(RULES_BY_ID.keys()))
def test_rule_has_docs_page(rule_id: str) -> None:
    """Each registered rule must have a corresponding docs page."""
    page = DOCS_DIR / f"{rule_id}.md"
    assert page.is_file(), f"Missing docs page: docs/rules/{rule_id}.md"


def test_all_pages_correspond_to_registered_rules() -> None:
    """Reverse check: no orphan pages for rules that no longer exist."""
    pages = {p.stem for p in DOCS_DIR.glob("*.md") if p.stem != "README"}
    registered = set(RULES_BY_ID.keys())
    orphans = pages - registered
    assert not orphans, f"Orphan docs pages (rule no longer registered): {orphans}"
