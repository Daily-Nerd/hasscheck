"""Tests for hasscheck.profiles — ProfileDefinition dataclass and built-in profiles."""

from __future__ import annotations

import pytest

from hasscheck.models import RuleSeverity
from hasscheck.profiles import (
    CLOUD_SERVICE,
    CORE_SUBMISSION_CANDIDATE,
    HELPER,
    LOCAL_DEVICE,
    PROFILES,
    ProfileDefinition,
)

EXPECTED_PROFILE_IDS = {
    "cloud-service",
    "local-device",
    "hub",
    "helper",
    "read-only-sensor",
    "core-submission-candidate",
}


# ---------- Phase 1.1: registry size + keying + frozen ----------


def test_profiles_registry_contains_exactly_six_built_ins() -> None:
    assert set(PROFILES) == EXPECTED_PROFILE_IDS


def test_each_profile_keyed_by_its_own_id() -> None:
    for name, profile in PROFILES.items():
        assert profile.id == name


def test_profile_dataclass_is_frozen() -> None:
    """Mutating any field raises FrozenInstanceError."""
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        CLOUD_SERVICE.id = "x"  # type: ignore[misc]


# ---------- Phase 1.3: invariant tests (rule IDs exist + overridable) ----------


@pytest.mark.parametrize("profile", list(PROFILES.values()), ids=lambda p: p.id)
def test_profile_severity_override_rule_ids_exist_in_registry(
    profile: ProfileDefinition,
) -> None:
    from hasscheck.rules.registry import RULES_BY_ID

    for rule_id in profile.severity_overrides:
        assert rule_id in RULES_BY_ID, (
            f"Profile {profile.id!r} references unknown rule_id {rule_id!r} "
            f"in severity_overrides"
        )


@pytest.mark.parametrize("profile", list(PROFILES.values()), ids=lambda p: p.id)
def test_profile_disabled_rule_ids_exist_in_registry(
    profile: ProfileDefinition,
) -> None:
    from hasscheck.rules.registry import RULES_BY_ID

    for rule_id in profile.disabled_rules:
        assert rule_id in RULES_BY_ID, (
            f"Profile {profile.id!r} references unknown rule_id {rule_id!r} "
            f"in disabled_rules"
        )


@pytest.mark.parametrize("profile", list(PROFILES.values()), ids=lambda p: p.id)
def test_profile_severity_overrides_target_overridable_rules(
    profile: ProfileDefinition,
) -> None:
    from hasscheck.rules.registry import RULES_BY_ID

    for rule_id in profile.severity_overrides:
        rule = RULES_BY_ID[rule_id]
        assert rule.overridable, (
            f"Profile {profile.id!r} boosts non-overridable rule {rule_id!r}"
        )


@pytest.mark.parametrize("profile", list(PROFILES.values()), ids=lambda p: p.id)
def test_profile_disabled_rules_target_overridable_rules(
    profile: ProfileDefinition,
) -> None:
    from hasscheck.rules.registry import RULES_BY_ID

    for rule_id in profile.disabled_rules:
        rule = RULES_BY_ID[rule_id]
        assert rule.overridable, (
            f"Profile {profile.id!r} disables non-overridable rule {rule_id!r}"
        )


# ---------- Phase 2.1: core-submission-candidate parity test ----------


def test_core_submission_candidate_covers_every_overridable_recommended_rule() -> None:
    """Parity guard: _CORE_SUBMISSION_RULE_IDS must exactly match the registry.

    Adding a new overridable RECOMMENDED rule MUST be a deliberate decision
    about core-submission-candidate scope (fails the test, forcing the author
    to update _CORE_SUBMISSION_RULE_IDS in profiles.py).
    """
    from hasscheck.rules.registry import RULES_BY_ID

    expected = frozenset(
        rid
        for rid, rule in RULES_BY_ID.items()
        if rule.overridable and rule.severity is RuleSeverity.RECOMMENDED
    )
    actual = frozenset(CORE_SUBMISSION_CANDIDATE.severity_overrides)
    assert actual == expected, (
        f"CORE_SUBMISSION_CANDIDATE.severity_overrides does not match "
        f"the current set of overridable RECOMMENDED rules.\n"
        f"Missing from profile: {expected - actual}\n"
        f"Extra in profile: {actual - expected}"
    )


# ---------- Cloud-service profile structure ----------


def test_cloud_service_profile_has_three_severity_overrides() -> None:
    assert len(CLOUD_SERVICE.severity_overrides) == 3
    for _rule_id, sev in CLOUD_SERVICE.severity_overrides.items():
        assert sev == RuleSeverity.REQUIRED


def test_cloud_service_profile_has_empty_disabled_rules() -> None:
    assert CLOUD_SERVICE.disabled_rules == frozenset()


def test_local_device_profile_disables_privacy_rule() -> None:
    assert "docs.privacy.exists" in LOCAL_DEVICE.disabled_rules


def test_helper_profile_disables_device_info_and_diagnostics() -> None:
    assert LOCAL_DEVICE.disabled_rules == frozenset({"docs.privacy.exists"})
    assert HELPER.disabled_rules == frozenset(
        {"entity.device_info.set", "diagnostics.file.exists"}
    )
