"""Built-in quality profiles (#146 / ADR-0015).

Profiles are curated severity baselines for specific Home Assistant integration
shapes (cloud-service, local-device, hub, helper, read-only-sensor,
core-submission-candidate). Each profile may:

  - Boost RECOMMENDED rules to REQUIRED (severity_overrides).
  - Mark rules as not_applicable for the integration shape (disabled_rules).

Profiles are PURE RECOMMENDATIONS. Per-rule user RuleOverride entries in
hasscheck.yaml take precedence (D4 in the proposal). Profiles cannot mutate
non-overridable rules — those entries are silently skipped at apply time (D6).

Profile definitions are standalone maps; RuleDefinition.profiles field is NOT
populated here (ADR 0015 D7).

Rule IDs in this module MUST exist in hasscheck.rules.registry.RULES_BY_ID
AND have overridable=True. Both invariants are enforced by tests in
tests/test_profiles.py (NOT at import time, to avoid circular imports
between rules.registry and profiles).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hasscheck.models import RuleSeverity


@dataclass(frozen=True)
class ProfileDefinition:
    """A named quality profile that adjusts rule severity and applicability.

    Fields:
        id: Unique profile identifier (kebab-case).
        title: Short human-readable title.
        description: Longer description of the integration shape this covers.
        severity_overrides: Mapping of rule_id → new RuleSeverity.
            Only rules with overridable=True are affected at apply time.
        disabled_rules: Rule IDs whose findings are forced to NOT_APPLICABLE.
            Only rules with overridable=True are affected at apply time.
    """

    id: str
    title: str
    description: str
    severity_overrides: dict[str, RuleSeverity] = field(default_factory=dict)
    disabled_rules: frozenset[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Built-in profile definitions (ADR-0015 — frozen at v1)
# ---------------------------------------------------------------------------

CLOUD_SERVICE = ProfileDefinition(
    id="cloud-service",
    title="Cloud-backed integration",
    description=(
        "Cloud-backed integration: reauth, diagnostics redaction, and privacy "
        "documentation are critical for credentialed external services."
    ),
    severity_overrides={
        "config_flow.reauth_step.exists": RuleSeverity.REQUIRED,
        "diagnostics.redaction.used": RuleSeverity.REQUIRED,
        "docs.privacy.exists": RuleSeverity.REQUIRED,
    },
    disabled_rules=frozenset(),
)

LOCAL_DEVICE = ProfileDefinition(
    id="local-device",
    title="LAN-only device integration",
    description=(
        "LAN-only device integration: stable device identity and unique IDs "
        "are critical; privacy-policy documentation rarely applies."
    ),
    severity_overrides={
        "config_flow.unique_id.set": RuleSeverity.REQUIRED,
        "entity.device_info.set": RuleSeverity.REQUIRED,
        "entity.unique_id.set": RuleSeverity.REQUIRED,
    },
    disabled_rules=frozenset({"docs.privacy.exists"}),
)

HUB = ProfileDefinition(
    id="hub",
    title="Hub / coordinator integration",
    description=(
        "Hub or coordinator managing child entities: device registry "
        "and full setup/unload lifecycle support are critical."
    ),
    severity_overrides={
        "entity.device_info.set": RuleSeverity.REQUIRED,
        "init.async_setup_entry.defined": RuleSeverity.REQUIRED,
        "tests.unload.detected": RuleSeverity.REQUIRED,
    },
    disabled_rules=frozenset(),
)

HELPER = ProfileDefinition(
    id="helper",
    title="Helper-style integration",
    description=(
        "Helper-style integration (template, derivative, computed): "
        "config flow and tests matter most; device/diagnostics rarely apply."
    ),
    severity_overrides={
        "config_flow.file.exists": RuleSeverity.REQUIRED,
        "tests.config_flow.detected": RuleSeverity.REQUIRED,
    },
    disabled_rules=frozenset(
        {
            "entity.device_info.set",
            "diagnostics.file.exists",
        }
    ),
)

READ_ONLY_SENSOR = ProfileDefinition(
    id="read-only-sensor",
    title="Read-only sensor integration",
    description=(
        "Read-only sensor integration: tests + README presence matter; "
        "reauth and repair flows typically do not apply."
    ),
    severity_overrides={
        "tests.folder.exists": RuleSeverity.REQUIRED,
        "docs.readme.exists": RuleSeverity.REQUIRED,
    },
    disabled_rules=frozenset(
        {
            "config_flow.reauth_step.exists",
            "repairs.file.exists",
        }
    ),
)

# Hardcoded enumeration of every overridable RECOMMENDED rule ID at v0.15.x.
# This is INTENTIONALLY a literal list (not derived from RULES at import time)
# so that adding a new RECOMMENDED rule does NOT silently change
# `core-submission-candidate` semantics. A test in tests/test_profiles.py
# enforces parity — when a new overridable RECOMMENDED rule lands, this
# list MUST be updated in the same PR (the test fails otherwise).
# Parity test enforces sync when new RECOMMENDED rules land.
_CORE_SUBMISSION_RULE_IDS: frozenset[str] = frozenset(
    {
        "brand.icon.exists",
        "ci.github_actions.exists",
        "config_flow.connection_test",
        "config_flow.file.exists",
        "config_flow.reauth_step.exists",
        "config_flow.reconfigure_step.exists",
        "config_flow.unique_id.set",
        "config_flow.user_step.exists",
        "diagnostics.file.exists",
        "diagnostics.redaction.used",
        "docs.configuration.exists",
        "docs.examples.exists",
        "docs.hacs_instructions.exists",
        "docs.installation.exists",
        "docs.limitations.exists",
        "docs.privacy.exists",
        "docs.readme.exists",
        "docs.removal.exists",
        "docs.supported_devices.exists",
        "docs.troubleshooting.exists",
        "entity.device_info.set",
        "entity.has_entity_name.set",
        "entity.unique_id.set",
        "init.async_setup_entry.defined",
        "init.runtime_data.used",
        "maintenance.changelog.exists",
        "maintenance.recent_commit.detected",
        "maintenance.recent_release.detected",
        "manifest.integration_type.exists",
        "manifest.integration_type.valid",
        "manifest.iot_class.exists",
        "manifest.iot_class.valid",
        "manifest.requirements.entries_well_formed",
        "manifest.requirements.no_git_or_url_specs",
        "repairs.file.exists",
        "repo.license.exists",
        "tests.config_flow.detected",
        "tests.folder.exists",
        "tests.setup_entry.detected",
        "tests.unload.detected",
        "version.identity.present",
        "version.manifest.resolvable",
        "version.matches.release_tag",
    }
)

CORE_SUBMISSION_CANDIDATE = ProfileDefinition(
    id="core-submission-candidate",
    title="Targeting Home Assistant core submission",
    description=(
        "Targeting Home Assistant core submission: every overridable "
        "RECOMMENDED rule is boosted to REQUIRED. Use this profile only when "
        "preparing an integration for upstream contribution."
    ),
    severity_overrides={
        rule_id: RuleSeverity.REQUIRED for rule_id in _CORE_SUBMISSION_RULE_IDS
    },
    disabled_rules=frozenset(),
)

PROFILES: dict[str, ProfileDefinition] = {
    p.id: p
    for p in (
        CLOUD_SERVICE,
        LOCAL_DEVICE,
        HUB,
        HELPER,
        READ_ONLY_SENSOR,
        CORE_SUBMISSION_CANDIDATE,
    )
}


def get_profile(name: str) -> ProfileDefinition | None:
    """Return a built-in profile by name, or None if not found."""
    return PROFILES.get(name)
