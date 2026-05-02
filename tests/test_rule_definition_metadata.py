"""Tests for new optional metadata fields on RuleDefinition — #147."""

from __future__ import annotations

import pytest

from hasscheck.models import RuleSeverity
from hasscheck.rules.base import RuleDefinition


def _make_minimal_rule(**kwargs) -> RuleDefinition:
    """Return a RuleDefinition with only the 9 original required fields."""

    def _noop(ctx):  # pragma: no cover
        raise NotImplementedError

    defaults = dict(
        id="test.rule",
        version="1.0.0",
        category="test",
        severity=RuleSeverity.REQUIRED,
        title="Test rule",
        why="Because we test.",
        source_url="https://example.com",
        check=_noop,
        overridable=False,
    )
    defaults.update(kwargs)
    return RuleDefinition(**defaults)


class TestRuleDefinitionAcceptsAllNewFields:
    """Scenario 1 — construct with all 13 new fields at non-default values."""

    def test_rule_definition_accepts_all_new_fields(self) -> None:
        def _noop(ctx):  # pragma: no cover
            raise NotImplementedError

        rule = RuleDefinition(
            id="test.full.fields",
            version="2.0.0",
            category="meta",
            severity=RuleSeverity.REQUIRED,
            title="Full fields rule",
            why="To test all new metadata fields.",
            source_url="https://example.com/full",
            check=_noop,
            overridable=True,
            # --- 13 new optional fields ---
            tags=("ha-2026", "cloud"),
            profiles=("default", "strict"),
            min_ha_version="2024.1",
            max_ha_version="2025.12",
            introduced_by="dev@example.com",
            introduced_at_version="1.5.0",
            advisory_id="GHSA-xxxx-yyyy-zzzz",
            related_quality_scale_rule="some-quality-rule",
            confidence="medium",
            false_positive_notes="May trigger on edge case X.",
            replacement_rule="new.better.rule",
            deprecated=True,
            deprecated_in_version="2.0.0",
        )

        assert rule.tags == ("ha-2026", "cloud")
        assert rule.profiles == ("default", "strict")
        assert rule.min_ha_version == "2024.1"
        assert rule.max_ha_version == "2025.12"
        assert rule.introduced_by == "dev@example.com"
        assert rule.introduced_at_version == "1.5.0"
        assert rule.advisory_id == "GHSA-xxxx-yyyy-zzzz"
        assert rule.related_quality_scale_rule == "some-quality-rule"
        assert rule.confidence == "medium"
        assert rule.false_positive_notes == "May trigger on edge case X."
        assert rule.replacement_rule == "new.better.rule"
        assert rule.deprecated is True
        assert rule.deprecated_in_version == "2.0.0"


class TestRuleDefinitionDefaultsForNewFields:
    """Scenario 2 — construct with only the 9 existing required fields; assert all 13 new fields equal their defaults."""

    def test_rule_definition_defaults_for_new_fields(self) -> None:
        rule = _make_minimal_rule()

        assert rule.tags == ()
        assert rule.profiles == ()
        assert rule.min_ha_version is None
        assert rule.max_ha_version is None
        assert rule.introduced_by is None
        assert rule.introduced_at_version is None
        assert rule.advisory_id is None
        assert rule.related_quality_scale_rule is None
        assert rule.confidence == "high"
        assert rule.false_positive_notes is None
        assert rule.replacement_rule is None
        assert rule.deprecated is False
        assert rule.deprecated_in_version is None


class TestRuleDefinitionCollectionFieldsRejectList:
    """Scenario 3 — tags=list raises TypeError (eager D2 validation in __post_init__)."""

    def test_rule_definition_collection_fields_reject_list(self) -> None:
        with pytest.raises(TypeError):
            _make_minimal_rule(tags=["x"])  # type: ignore[arg-type]


class TestRuleDefinitionConfidenceRejectsInvalidLiteral:
    """Scenario 4 — confidence='extreme' raises ValueError in __post_init__."""

    def test_rule_definition_confidence_rejects_invalid_literal(self) -> None:
        with pytest.raises(ValueError):
            _make_minimal_rule(confidence="extreme")  # type: ignore[arg-type]
