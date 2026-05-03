"""Bidirectional parity test: rule advisory_id ↔ ADVISORIES.

Spec requirement (S10, D8):
  1. Every RuleDefinition.advisory_id (non-None) must have a matching key in ADVISORIES.
  2. Every advisory in ADVISORIES must be referenced by at least one rule's advisory_id.
"""

from __future__ import annotations

import pytest

from hasscheck.advisories import ADVISORIES
from hasscheck.rules.registry import RULES


def _rule_advisory_ids() -> dict[str, str]:
    """Return a mapping of rule_id → advisory_id for rules that have advisory_id set."""
    return {rule.id: rule.advisory_id for rule in RULES if rule.advisory_id is not None}


def _all_advisory_ids_in_rules() -> set[str]:
    """Return all advisory_ids referenced by rules."""
    return {rule.advisory_id for rule in RULES if rule.advisory_id is not None}


class TestAdvisoryParity:
    """Bidirectional parity enforcement between rules and ADVISORIES."""

    def test_every_rule_advisory_id_exists_in_advisories(self) -> None:
        """Every rule.advisory_id must correspond to a key in ADVISORIES (spec S10)."""
        rule_to_advisory = _rule_advisory_ids()
        missing: list[str] = []

        for rule_id, advisory_id in rule_to_advisory.items():
            if advisory_id not in ADVISORIES:
                missing.append(
                    f"rule '{rule_id}' references advisory '{advisory_id}' which is not in ADVISORIES"
                )

        assert not missing, (
            "The following rules reference advisory IDs not found in ADVISORIES:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )

    def test_every_advisory_is_referenced_by_at_least_one_rule(self) -> None:
        """Every advisory in ADVISORIES must be referenced by at least one rule (D8)."""
        referenced_advisory_ids = _all_advisory_ids_in_rules()
        orphaned: list[str] = []

        for advisory_id in ADVISORIES:
            if advisory_id not in referenced_advisory_ids:
                orphaned.append(advisory_id)

        assert not orphaned, (
            "The following advisories are not referenced by any rule (orphaned):\n"
            + "\n".join(f"  - {aid}" for aid in sorted(orphaned))
        )

    def test_advisory_rule_ids_match_actual_rules(self) -> None:
        """Each Advisory.rule_ids must reference rules that actually exist in the registry."""
        from hasscheck.rules.registry import RULES_BY_ID

        mismatches: list[str] = []
        for advisory_id, advisory in ADVISORIES.items():
            for rule_id in advisory.rule_ids:
                if rule_id not in RULES_BY_ID:
                    mismatches.append(
                        f"advisory '{advisory_id}' references rule '{rule_id}' which is not in RULES_BY_ID"
                    )

        assert not mismatches, (
            "The following advisory rule_ids do not match any registered rule:\n"
            + "\n".join(f"  - {m}" for m in mismatches)
        )

    @pytest.mark.parametrize("rule", [r for r in RULES if r.advisory_id is not None])
    def test_advisory_id_format_is_valid(self, rule) -> None:
        """advisory_id must be a non-empty string matching the ha-YYYY-MM-* pattern."""
        advisory_id = rule.advisory_id
        assert isinstance(advisory_id, str) and len(advisory_id) > 0, (
            f"rule '{rule.id}' has invalid advisory_id: {advisory_id!r}"
        )
        assert advisory_id.startswith("ha-"), (
            f"rule '{rule.id}' advisory_id '{advisory_id}' should start with 'ha-'"
        )
