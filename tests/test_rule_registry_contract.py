"""Registry-level contract tests for RuleDefinition metadata — #147."""

from __future__ import annotations

from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Task 2.1 — replacement_rule cross-reference contract
# ---------------------------------------------------------------------------

ANCHOR_ID = sorted(RULES_BY_ID.keys())[0]
EXPECTED_HASH = 0  # placeholder — replaced in Task 2.3 GREEN phase


def test_replacement_rule_must_reference_existing_id() -> None:
    """Every non-None replacement_rule must point to an existing rule in RULES_BY_ID.

    Passes vacuously when no rule has replacement_rule set (expected baseline
    in this PR — no existing rule is deprecated yet).
    """
    dangling: list[tuple[str, str]] = []
    for rule_id, rule in RULES_BY_ID.items():
        if (
            rule.replacement_rule is not None
            and rule.replacement_rule not in RULES_BY_ID
        ):
            dangling.append((rule_id, rule.replacement_rule))
    assert not dangling, f"replacement_rule references non-existent rule(s): {dangling}"


# ---------------------------------------------------------------------------
# Task 2.2 → 2.3 — hash-stability snapshot
# ---------------------------------------------------------------------------


def test_existing_rule_hashes_stable() -> None:
    """Hash of the alphabetically-first registered rule must stay stable post-PR.

    The snapshot is captured once (Task 2.3 GREEN), hard-coded as EXPECTED_HASH,
    and serves as a canary against future field reorderings or accidental
    dataclass mutations that would silently break any consumer that interns
    RuleDefinition in a set or dict.

    If you intentionally change a field that affects the hash, update EXPECTED_HASH
    and document why in your commit message.
    """
    rule = RULES_BY_ID[ANCHOR_ID]
    assert hash(rule) == EXPECTED_HASH, (
        f"Hash of {ANCHOR_ID!r} changed from {EXPECTED_HASH} to {hash(rule)}. "
        f"This breaks any consumer that interns RuleDefinition. "
        f"If intentional, update EXPECTED_HASH and document why in the commit."
    )
