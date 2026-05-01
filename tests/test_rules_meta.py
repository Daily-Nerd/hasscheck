"""Meta-tests that lock the v0.2 overridable audit policy in code.

These tests fail at import time (TypeError from frozen dataclass) if any
rule definition omits the `overridable` field, and fail at assertion time
if the set of locked rules drifts from the canonical audit.

If a future PR sets overridable inconsistently with the audit, this test
fails — by design.
"""
from __future__ import annotations

from hasscheck.rules.registry import RULES, RULES_BY_ID

# Canonical audit (from sdd/config-file-support/mixed-status-rule-audit):
# 18 rules total, 10 locked overridable=False, 8 overridable=True.
EXPECTED_LOCKED_RULE_IDS = {
    "hacs.custom_components.exists",
    "hacs.file.parseable",  # mixed-status: WARN missing, FAIL invalid JSON
    "manifest.exists",
    "manifest.domain.exists",
    "manifest.name.exists",
    "manifest.version.exists",
    "manifest.documentation.exists",
    "manifest.issue_tracker.exists",
    "manifest.codeowners.exists",
    "config_flow.manifest_flag_consistent",
}

EXPECTED_OVERRIDABLE_RULE_IDS = {
    "config_flow.file.exists",
    "diagnostics.file.exists",
    "repairs.file.exists",
    "brand.icon.exists",
    "docs.readme.exists",
    "repo.license.exists",
    "tests.folder.exists",
    "ci.github_actions.exists",
}


def test_total_rule_count_is_eighteen() -> None:
    assert len(RULES) == 18, f"expected 18 rules, got {len(RULES)}"


def test_every_rule_declares_overridable_bool() -> None:
    for rule in RULES:
        assert hasattr(rule, "overridable"), f"{rule.id} is missing the overridable field"
        assert isinstance(rule.overridable, bool), (
            f"{rule.id}.overridable must be bool, got {type(rule.overridable).__name__}"
        )


def test_locked_rules_match_audit() -> None:
    actual_locked = {rule.id for rule in RULES if rule.overridable is False}
    assert actual_locked == EXPECTED_LOCKED_RULE_IDS, (
        f"locked rule_ids drifted from audit. "
        f"unexpected lock: {actual_locked - EXPECTED_LOCKED_RULE_IDS}, "
        f"missing lock: {EXPECTED_LOCKED_RULE_IDS - actual_locked}"
    )


def test_overridable_rules_match_audit() -> None:
    actual_overridable = {rule.id for rule in RULES if rule.overridable is True}
    assert actual_overridable == EXPECTED_OVERRIDABLE_RULE_IDS, (
        f"overridable rule_ids drifted from audit. "
        f"unexpected: {actual_overridable - EXPECTED_OVERRIDABLE_RULE_IDS}, "
        f"missing: {EXPECTED_OVERRIDABLE_RULE_IDS - actual_overridable}"
    )


def test_required_rules_are_all_locked() -> None:
    """REQUIRED severity rules must always be overridable=False."""
    from hasscheck.models import RuleSeverity

    for rule in RULES:
        if rule.severity is RuleSeverity.REQUIRED:
            assert rule.overridable is False, (
                f"REQUIRED rule {rule.id} must be overridable=False"
            )


def test_locked_set_and_overridable_set_partition_all_rules() -> None:
    """Sanity check: every rule lands in exactly one of the two sets."""
    all_ids = {rule.id for rule in RULES}
    assert all_ids == EXPECTED_LOCKED_RULE_IDS | EXPECTED_OVERRIDABLE_RULE_IDS
    assert not (EXPECTED_LOCKED_RULE_IDS & EXPECTED_OVERRIDABLE_RULE_IDS)
