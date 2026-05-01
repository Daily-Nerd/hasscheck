"""Integration tests against the bad_integration fixture.

Design: D3 — whitelist-asserts only on the 7 v0.8 rule IDs that the fixture
was designed to exercise. Other rules are NOT asserted here — keeps the test
stable as more rules land in PR2/PR3/PR4.

Extend this file when adding fixture coverage for new rules (PR2–PR4 tasks).
"""

from __future__ import annotations

from pathlib import Path

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus

FIXTURE_PATH = Path(__file__).parent.parent / "examples" / "bad_integration"


def _findings_by_id():
    return {f.rule_id: f for f in run_check(FIXTURE_PATH).findings}


# ---------------------------------------------------------------------------
# PR1: manifest.domain.matches_directory must FAIL on the bad_integration fixture
# ---------------------------------------------------------------------------


def test_domain_mismatch_rule_fails_on_bad_integration_fixture() -> None:
    """Fixture declares domain 'wrong_domain' but directory is 'demo_bad' — must FAIL."""
    findings = _findings_by_id()
    assert findings["manifest.domain.matches_directory"].status is RuleStatus.FAIL
