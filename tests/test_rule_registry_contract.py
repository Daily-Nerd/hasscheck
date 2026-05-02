"""Registry-level contract tests for RuleDefinition metadata — #147."""

from __future__ import annotations

import dataclasses

from hasscheck.rules.base import RuleDefinition
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Task 2.1 — replacement_rule cross-reference contract
# ---------------------------------------------------------------------------

ANCHOR_ID = sorted(RULES_BY_ID.keys())[0]

# Locked field ordering: any reorder/add/remove of fields in this sequence
# changes the hash structure and breaks consumers that intern RuleDefinition.
# `check` is excluded from hash/compare (field(hash=False, compare=False)).
EXPECTED_HASHED_FIELD_NAMES: tuple[str, ...] = (
    "id",
    "version",
    "category",
    "severity",
    "title",
    "why",
    "source_url",
    # "check" — excluded from hash (callable, non-deterministic across processes)
    "overridable",
    "tags",
    "profiles",
    "min_ha_version",
    "max_ha_version",
    "introduced_by",
    "introduced_at_version",
    "advisory_id",
    "related_quality_scale_rule",
    "confidence",
    "false_positive_notes",
    "replacement_rule",
    "deprecated",
    "deprecated_in_version",
)


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
# Task 2.2 → 2.3 — hash-stability anchor
# ---------------------------------------------------------------------------


def test_existing_rule_hashes_stable() -> None:
    """Hash structure of RuleDefinition must remain stable post-PR.

    Python's PYTHONHASHSEED randomises per-process hash values for strings and
    other objects, making cross-process integer pinning unreliable without
    constraining PYTHONHASHSEED in CI (an invasive change). Instead, we pin the
    STRUCTURAL invariant: the exact sequence of fields that participate in the
    hash computation (all fields where hash != False, in declaration order).

    Any reordering, addition, or removal of hashed fields changes the hash
    structure and would silently break consumers that intern RuleDefinition in
    a set or dict-key position. This test catches that class of regression.

    If you intentionally change which fields participate in hashing, update
    EXPECTED_HASHED_FIELD_NAMES and document why in the commit message.
    """
    actual_hashed = tuple(
        f.name
        for f in dataclasses.fields(RuleDefinition)
        if f.hash is not False  # None means "inherit from compare" = True
    )
    assert actual_hashed == EXPECTED_HASHED_FIELD_NAMES, (
        f"Hash-participating fields changed.\n"
        f"Expected: {EXPECTED_HASHED_FIELD_NAMES}\n"
        f"Actual:   {actual_hashed}\n"
        "This breaks any consumer that interns RuleDefinition. "
        "Update EXPECTED_HASHED_FIELD_NAMES and document why in the commit."
    )

    # Secondary check: the anchor rule is hashable and hashes consistently
    # within the same process (verifies __post_init__ doesn't corrupt the object).
    anchor_rule = RULES_BY_ID[ANCHOR_ID]
    assert hash(anchor_rule) == hash(anchor_rule), (
        f"hash({ANCHOR_ID!r}) is not idempotent — frozen dataclass invariant violated."
    )
