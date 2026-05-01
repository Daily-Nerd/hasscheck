"""Integration tests against the bad_integration fixture.

Design: D3 — whitelist-asserts only on the rule IDs that the fixture was
designed to exercise. Other rules are NOT asserted here — keeps the test
stable as more rules land.

Extend this file when adding fixture coverage for new rules.
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


# ---------------------------------------------------------------------------
# PR2: iot_class.valid must FAIL (fixture has iot_class: "not_a_valid_class")
#       integration_type.exists must WARN (fixture has no integration_type)
# ---------------------------------------------------------------------------


def test_iot_class_valid_fails_on_bad_integration_fixture() -> None:
    """Fixture has iot_class='not_a_valid_class' — must FAIL."""
    findings = _findings_by_id()
    f = findings["manifest.iot_class.valid"]
    assert f.status is RuleStatus.FAIL
    assert "not_a_valid_class" in f.message


def test_integration_type_exists_warns_on_bad_integration_fixture() -> None:
    """Fixture has no integration_type field — must WARN."""
    findings = _findings_by_id()
    assert findings["manifest.integration_type.exists"].status is RuleStatus.WARN


# ---------------------------------------------------------------------------
# PR3: config_flow.user_step.exists must WARN (fixture has async_step_setup,
#       not async_step_user)
# ---------------------------------------------------------------------------


def test_config_flow_user_step_warns_on_bad_integration_fixture() -> None:
    """Fixture config_flow.py defines async_step_setup but not async_step_user — must WARN."""
    findings = _findings_by_id()
    f = findings["config_flow.user_step.exists"]
    assert f.status is RuleStatus.WARN
    assert "async_step_user" in f.message


# ---------------------------------------------------------------------------
# PR4: diagnostics.redaction.used must WARN (fixture returns entry.data raw,
#       no redaction call)
# ---------------------------------------------------------------------------


def test_diagnostics_redaction_warns_on_bad_integration_fixture() -> None:
    """Fixture diagnostics.py returns entry.data directly without redaction — must WARN."""
    findings = _findings_by_id()
    f = findings["diagnostics.redaction.used"]
    assert f.status is RuleStatus.WARN
    assert "likely exposes secrets" in f.message


# ---------------------------------------------------------------------------
# PR5 / issue #55: README content rules — bad_integration README is intentionally
# sparse (no installation/config/troubleshooting/removal/privacy sections)
# ---------------------------------------------------------------------------


def test_installation_section_warns_on_bad_integration_fixture() -> None:
    """bad_integration README has no Installation section — docs.installation.exists must WARN."""
    findings = _findings_by_id()
    f = findings["docs.installation.exists"]
    assert f.status is RuleStatus.WARN


def test_configuration_section_warns_on_bad_integration_fixture() -> None:
    """bad_integration README has no Configuration section — must WARN."""
    findings = _findings_by_id()
    assert findings["docs.configuration.exists"].status is RuleStatus.WARN


def test_troubleshooting_section_warns_on_bad_integration_fixture() -> None:
    """bad_integration README has no Troubleshooting section — must WARN."""
    findings = _findings_by_id()
    assert findings["docs.troubleshooting.exists"].status is RuleStatus.WARN


def test_removal_section_warns_on_bad_integration_fixture() -> None:
    """bad_integration README has no Removal section — must WARN."""
    findings = _findings_by_id()
    assert findings["docs.removal.exists"].status is RuleStatus.WARN


def test_privacy_section_warns_on_bad_integration_fixture() -> None:
    """bad_integration README has no Privacy section — must WARN."""
    findings = _findings_by_id()
    assert findings["docs.privacy.exists"].status is RuleStatus.WARN
