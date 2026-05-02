"""Meta-tests that lock the v0.2 overridable audit policy in code.

These tests fail at import time (TypeError from frozen dataclass) if any
rule definition omits the `overridable` field, and fail at assertion time
if the set of locked rules drifts from the canonical audit.

If a future PR sets overridable inconsistently with the audit, this test
fails — by design.
"""

from __future__ import annotations

from hasscheck.rules.registry import RULES

# Canonical audit (from sdd/config-file-support/mixed-status-rule-audit):
# 42 rules total (v0.10 issue #107 adds 5 modern HA pattern rules):
#   - init.async_setup_entry.defined (overridable=True, RECOMMENDED)
#   - init.runtime_data.used (overridable=True, RECOMMENDED)
#   - entity.unique_id.set (overridable=True, RECOMMENDED)
#   - entity.has_entity_name.set (overridable=True, RECOMMENDED)
#   - entity.device_info.set (overridable=True, RECOMMENDED)
# 12 locked overridable=False, 30 overridable=True.
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
    "manifest.domain.matches_directory",  # v0.8 PR1 — non-overridable REQUIRED
    "config_flow.manifest_flag_consistent",
    "manifest.requirements.is_list",  # v0.10 #100 — correctness check, non-overridable
}

EXPECTED_OVERRIDABLE_RULE_IDS = {
    "config_flow.file.exists",
    "config_flow.user_step.exists",  # v0.8 PR3 — AST inspection (RECOMMENDED, overridable=True)
    "diagnostics.file.exists",
    "diagnostics.redaction.used",  # v0.8 PR4 — AST redaction detection (RECOMMENDED, overridable=True)
    "repairs.file.exists",
    "brand.icon.exists",
    "docs.readme.exists",
    "repo.license.exists",
    "tests.folder.exists",
    "ci.github_actions.exists",
    # v0.8 PR2 — manifest metadata validation (RECOMMENDED, overridable=True)
    "manifest.iot_class.exists",
    "manifest.iot_class.valid",
    "manifest.integration_type.exists",
    "manifest.integration_type.valid",
    # v0.9 issue #55 — README content rules (RECOMMENDED, overridable=True)
    "docs.installation.exists",
    "docs.configuration.exists",
    "docs.troubleshooting.exists",
    "docs.removal.exists",
    "docs.privacy.exists",
    # v0.10 issue #100 — manifest.requirements validation (RECOMMENDED, overridable=True)
    "manifest.requirements.entries_well_formed",
    "manifest.requirements.no_git_or_url_specs",
    # v0.10 issue #101 — advanced config_flow rules (RECOMMENDED, overridable=True)
    "config_flow.reauth_step.exists",
    "config_flow.reconfigure_step.exists",
    "config_flow.unique_id.set",
    "config_flow.connection_test",
    # v0.10 issue #107 — modern HA pattern checks (RECOMMENDED, overridable=True)
    "init.async_setup_entry.defined",
    "init.runtime_data.used",
    "entity.unique_id.set",
    "entity.has_entity_name.set",
    "entity.device_info.set",
}


def test_total_rule_count_is_forty_two() -> None:
    assert len(RULES) == 42, f"expected 42 rules, got {len(RULES)}"


def test_every_rule_declares_overridable_bool() -> None:
    for rule in RULES:
        assert hasattr(rule, "overridable"), (
            f"{rule.id} is missing the overridable field"
        )
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


def test_no_duplicate_rule_ids() -> None:
    from hasscheck.rules.registry import RULES

    ids = [rule.id for rule in RULES]
    assert len(ids) == len(set(ids)), (
        f"Duplicate rule IDs: {[id for id in ids if ids.count(id) > 1]}"
    )
