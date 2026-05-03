from __future__ import annotations

import json

import pytest

from hasscheck.checker import run_check
from hasscheck.config import HassCheckConfig, RuleOverride
from hasscheck.models import Finding, RuleStatus


def test_missing_custom_components_and_manifest_are_reported(tmp_path) -> None:
    report = run_check(tmp_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["hacs.custom_components.exists"].status is RuleStatus.FAIL
    assert findings["manifest.exists"].status is RuleStatus.FAIL
    assert findings["manifest.domain.exists"].status is RuleStatus.NOT_APPLICABLE


def test_manifest_domain_passes_for_custom_integration(tmp_path) -> None:
    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "demo",
                "name": "Demo",
                "documentation": "https://example.com",
                "issue_tracker": "https://example.com/issues",
                "codeowners": ["@demo"],
                "version": "0.1.0",
            }
        ),
        encoding="utf-8",
    )

    report = run_check(tmp_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["hacs.custom_components.exists"].status is RuleStatus.PASS
    assert findings["manifest.exists"].status is RuleStatus.PASS
    assert findings["manifest.domain.exists"].status is RuleStatus.PASS


# ---------- Phase 4: config kwarg + discovery ----------


def test_run_check_config_and_no_config_conflict(tmp_path) -> None:
    with pytest.raises(ValueError, match="no_config"):
        run_check(tmp_path, config=HassCheckConfig(), no_config=True)


def test_run_check_no_config_flag_skips_yaml(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — a real override target
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    report = run_check(tmp_path, no_config=True)
    assert report.summary.overrides_applied.count == 0


def test_run_check_discovers_yaml_at_root(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — confirms the override is actually applied
    (tmp_path / "hasscheck.yaml").write_text(
        "rules:\n"
        "  tests.folder.exists:\n"
        "    status: not_applicable\n"
        "    reason: no tests needed\n"
    )
    report = run_check(tmp_path)
    assert report.summary.overrides_applied.count == 1
    assert "tests.folder.exists" in report.summary.overrides_applied.rule_ids


def test_run_check_applies_overrides_from_config_kwarg(tmp_path) -> None:
    # tests.folder.exists is WARN in empty dir — confirms source="config" is set
    config = HassCheckConfig(
        rules={
            "tests.folder.exists": RuleOverride(status="not_applicable", reason="test")
        }
    )
    report = run_check(tmp_path, config=config)
    findings = {f.rule_id: f for f in report.findings}
    assert findings["tests.folder.exists"].status is RuleStatus.NOT_APPLICABLE
    assert findings["tests.folder.exists"].applicability.source == "config"
    assert report.summary.overrides_applied.count == 1


def test_run_check_no_yaml_overrides_applied_is_empty(tmp_path) -> None:
    report = run_check(tmp_path)
    assert report.summary.overrides_applied.count == 0
    assert report.summary.overrides_applied.rule_ids == []


def test_run_check_schema_version_is_0_5_0(tmp_path) -> None:
    report = run_check(tmp_path)
    assert report.schema_version == "0.5.0"


# ---------- v0.8: Ruleset ID bump ----------


def test_default_ruleset_id_is_hasscheck_ha_2026_5() -> None:
    from hasscheck.models import DEFAULT_RULESET_ID

    assert DEFAULT_RULESET_ID == "hasscheck-ha-2026.5"


# ---------- v0.13: Provenance block (#130) ----------


def test_run_check_report_provenance_key_present(tmp_path) -> None:
    """Round-trip: run_check → to_json_dict → parse → 'provenance' key present."""
    import json

    report = run_check(tmp_path)
    raw = report.to_json_dict()
    reparsed = json.loads(json.dumps(raw))

    assert "provenance" in reparsed
    assert reparsed["schema_version"] == "0.5.0"


def test_run_check_report_provenance_is_not_none(tmp_path) -> None:
    """run_check() populates provenance on the returned report."""
    report = run_check(tmp_path)
    assert report.provenance is not None


# ---------- Phase 3 — Checker SSoT + ProjectContext wiring ----------


def test_checker_calls_read_manifest_version_only_once(monkeypatch, tmp_path) -> None:
    """Spy on target.read_manifest_version; assert called <= 1 per run_check."""
    import hasscheck.target as target_module

    call_count = 0
    original = target_module.read_manifest_version

    def spy(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(target_module, "read_manifest_version", spy)

    import json

    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": "demo", "name": "Demo", "version": "1.0.0"})
    )

    run_check(tmp_path)
    assert call_count <= 1, (
        f"read_manifest_version called {call_count} times (expected <= 1)"
    )


def test_checker_populates_version_identity_into_context(tmp_path) -> None:
    """Run check on a tmp integration path; findings must include 'version' category."""
    import json

    integration = tmp_path / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(
        json.dumps({"domain": "demo", "name": "Demo", "version": "1.0.0"})
    )

    report = run_check(tmp_path)
    version_findings = [f for f in report.findings if f.category == "version"]
    assert len(version_findings) > 0, (
        "Expected at least one finding with category='version' after context wiring"
    )


def test_category_label_version_identity_present() -> None:
    """CATEGORY_LABELS['version'] must equal 'Version Identity'."""
    from hasscheck.checker import CATEGORY_LABELS

    assert CATEGORY_LABELS["version"] == "Version Identity"


# ---------- Phase 3: ApplicabilitySource "profile" + apply_profile_overrides ----------


def test_applicability_source_accepts_profile() -> None:
    """ApplicabilitySource must include 'profile' as a valid literal value."""
    from hasscheck.models import Applicability, ApplicabilityStatus

    a = Applicability(
        status=ApplicabilityStatus.NOT_APPLICABLE,
        reason="Disabled by profile 'test'.",
        source="profile",
    )
    assert a.source == "profile"


def _make_finding_for_checker(
    rule_id: str = "docs.readme.exists",
    severity: str = "recommended",
    status: str = "warn",
) -> Finding:
    """Build a minimal Finding for apply_profile_overrides tests."""
    from hasscheck.models import (
        Applicability,
        ApplicabilityStatus,
        RuleSeverity,
        RuleSource,
        RuleStatus,
    )

    return Finding(
        rule_id=rule_id,
        rule_version="1.0.0",
        category="test",
        status=RuleStatus(status),
        severity=RuleSeverity(severity),
        title=f"{rule_id} title",
        message=f"{rule_id} message",
        applicability=Applicability(
            status=ApplicabilityStatus.APPLICABLE,
            reason="test reason",
        ),
        source=RuleSource(url="https://example.com"),
    )


def test_apply_profile_overrides_none_returns_identical_list() -> None:
    """apply_profile_overrides(findings, None, rules) returns a new list with same elements."""
    from hasscheck.checker import apply_profile_overrides

    findings = [_make_finding_for_checker()]
    result = apply_profile_overrides(findings, None, [])
    assert result == findings
    assert result is not findings  # new list object


def test_apply_profile_overrides_boosts_overridable_severity() -> None:
    """Profile severity_override boosts a RECOMMENDED finding to REQUIRED."""
    from hasscheck.checker import apply_profile_overrides
    from hasscheck.models import RuleSeverity
    from hasscheck.profiles import READ_ONLY_SENSOR
    from hasscheck.rules.registry import RULES

    finding = _make_finding_for_checker(
        rule_id="docs.readme.exists",
        severity="recommended",
        status="warn",
    )
    result = apply_profile_overrides([finding], READ_ONLY_SENSOR, RULES)
    assert len(result) == 1
    assert result[0].severity == RuleSeverity.REQUIRED


def test_apply_profile_overrides_disables_overridable_rule() -> None:
    """Profile disabled_rules marks finding NOT_APPLICABLE with source='profile'."""
    from hasscheck.checker import apply_profile_overrides
    from hasscheck.models import RuleStatus
    from hasscheck.profiles import LOCAL_DEVICE
    from hasscheck.rules.registry import RULES

    finding = _make_finding_for_checker(
        rule_id="docs.privacy.exists",
        severity="recommended",
        status="warn",
    )
    result = apply_profile_overrides([finding], LOCAL_DEVICE, RULES)
    assert len(result) == 1
    assert result[0].status == RuleStatus.NOT_APPLICABLE
    assert result[0].applicability.source == "profile"


def test_apply_profile_overrides_skips_non_overridable_severity_override() -> None:
    """A profile severity_override on a non-overridable rule is silently skipped."""

    from hasscheck.checker import apply_profile_overrides
    from hasscheck.models import RuleSeverity
    from hasscheck.profiles import ProfileDefinition

    # manifest.exists is non-overridable (overridable=False)
    synthetic_profile = ProfileDefinition(
        id="test-non-overridable-sev",
        title="Test",
        description="Test profile that boosts a locked rule.",
        severity_overrides={"manifest.exists": RuleSeverity.REQUIRED},
        disabled_rules=frozenset(),
    )
    # manifest.exists is REQUIRED + non-overridable; severity must stay unchanged
    from hasscheck.models import (
        Applicability,
        ApplicabilityStatus,
        Finding,
        RuleSource,
        RuleStatus,
    )

    finding = Finding(
        rule_id="manifest.exists",
        rule_version="1.0.0",
        category="hacs_structure",
        status=RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title="manifest exists",
        message="no manifest",
        applicability=Applicability(status=ApplicabilityStatus.APPLICABLE, reason="t"),
        source=RuleSource(url="https://example.com"),
    )
    from hasscheck.rules.registry import RULES

    result = apply_profile_overrides([finding], synthetic_profile, RULES)
    assert result[0].severity == RuleSeverity.REQUIRED  # unchanged
    # No source change either
    assert result[0].applicability.source != "profile"


def test_apply_profile_overrides_skips_non_overridable_disable() -> None:
    """A profile disabled_rules on a non-overridable rule is silently skipped."""
    from hasscheck.checker import apply_profile_overrides
    from hasscheck.models import (
        Applicability,
        ApplicabilityStatus,
        Finding,
        RuleSeverity,
        RuleSource,
        RuleStatus,
    )
    from hasscheck.profiles import ProfileDefinition

    synthetic_profile = ProfileDefinition(
        id="test-non-overridable-disable",
        title="Test",
        description="Test profile that disables a locked rule.",
        severity_overrides={},
        disabled_rules=frozenset({"manifest.exists"}),
    )
    finding = Finding(
        rule_id="manifest.exists",
        rule_version="1.0.0",
        category="hacs_structure",
        status=RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title="manifest exists",
        message="no manifest",
        applicability=Applicability(status=ApplicabilityStatus.APPLICABLE, reason="t"),
        source=RuleSource(url="https://example.com"),
    )
    from hasscheck.rules.registry import RULES

    result = apply_profile_overrides([finding], synthetic_profile, RULES)
    assert result[0].status == RuleStatus.FAIL  # unchanged
    assert result[0].applicability.source != "profile"


def test_apply_profile_overrides_does_not_mutate_original_findings() -> None:
    """apply_profile_overrides never mutates the input finding objects."""
    from hasscheck.checker import apply_profile_overrides
    from hasscheck.profiles import READ_ONLY_SENSOR
    from hasscheck.rules.registry import RULES

    original = _make_finding_for_checker(
        rule_id="docs.readme.exists",
        severity="recommended",
        status="warn",
    )
    original_severity = original.severity
    original_status = original.status

    apply_profile_overrides([original], READ_ONLY_SENSOR, RULES)

    assert original.severity == original_severity
    assert original.status == original_status


# ---------- Phase 4: run_check profile integration ----------


def test_run_check_unknown_profile_name_raises_value_error(tmp_path) -> None:
    """run_check with an unknown profile name raises ValueError with 'Unknown profile'."""
    with pytest.raises(ValueError, match="Unknown profile"):
        run_check(tmp_path, profile_name="bogus-profile-doesnt-exist")


def test_run_check_no_profile_identical_to_baseline(tmp_path) -> None:
    """run_check with no profile produces same findings as without profile kwarg."""
    report_no_profile = run_check(tmp_path, no_config=True)
    report_explicit_none = run_check(tmp_path, no_config=True, profile_name=None)

    # severity values should be identical
    baseline = {f.rule_id: f.severity for f in report_no_profile.findings}
    with_none = {f.rule_id: f.severity for f in report_explicit_none.findings}
    assert baseline == with_none


def test_run_check_profile_boosts_severity_in_report(tmp_path) -> None:
    """cloud-service profile boosts config_flow.reauth_step.exists to REQUIRED."""
    from hasscheck.models import RuleSeverity

    report = run_check(tmp_path, no_config=True, profile_name="cloud-service")
    findings_by_id = {f.rule_id: f for f in report.findings}

    assert (
        findings_by_id["config_flow.reauth_step.exists"].severity
        == RuleSeverity.REQUIRED
    )


def test_run_check_profile_name_resolves_from_config(tmp_path) -> None:
    """When profile set in config, it is applied during run_check."""
    from hasscheck.config import HassCheckConfig
    from hasscheck.models import RuleSeverity

    config = HassCheckConfig(
        schema_version="0.7.0",
        profile="read-only-sensor",
    )
    report = run_check(tmp_path, config=config)
    findings_by_id = {f.rule_id: f for f in report.findings}
    assert findings_by_id["docs.readme.exists"].severity == RuleSeverity.REQUIRED


def test_run_check_cli_profile_name_overrides_config_profile(tmp_path) -> None:
    """CLI profile_name wins over config.profile."""
    from hasscheck.config import HassCheckConfig
    from hasscheck.models import RuleSeverity

    config = HassCheckConfig(
        schema_version="0.7.0",
        profile="helper",
    )
    # cloud-service boosts diagnostics.redaction.used; helper does not
    report = run_check(tmp_path, config=config, profile_name="cloud-service")
    findings_by_id = {f.rule_id: f for f in report.findings}
    assert (
        findings_by_id["diagnostics.redaction.used"].severity == RuleSeverity.REQUIRED
    )


def test_run_check_read_only_sensor_disables_reauth_step(tmp_path) -> None:
    """A4: read-only-sensor profile marks config_flow.reauth_step.exists as not_applicable."""
    from hasscheck.models import RuleStatus

    report = run_check(tmp_path, no_config=True, profile_name="read-only-sensor")
    findings_by_id = {f.rule_id: f for f in report.findings}
    assert (
        findings_by_id["config_flow.reauth_step.exists"].status
        == RuleStatus.NOT_APPLICABLE
    )
    assert (
        findings_by_id["config_flow.reauth_step.exists"].applicability.source
        == "profile"
    )


def test_run_check_user_rule_override_wins_over_profile_boost(tmp_path) -> None:
    """Per-rule config override supersedes profile severity boost."""
    from hasscheck.config import HassCheckConfig, RuleOverride
    from hasscheck.models import RuleStatus

    config = HassCheckConfig(
        schema_version="0.7.0",
        rules={
            "config_flow.reauth_step.exists": RuleOverride(
                status="not_applicable",
                reason="read-only integration, no reauth needed",
            )
        },
    )
    # cloud-service boosts config_flow.reauth_step.exists to REQUIRED,
    # but user override marks it not_applicable → user wins
    report = run_check(tmp_path, config=config, profile_name="cloud-service")
    findings_by_id = {f.rule_id: f for f in report.findings}
    assert (
        findings_by_id["config_flow.reauth_step.exists"].status
        == RuleStatus.NOT_APPLICABLE
    )
