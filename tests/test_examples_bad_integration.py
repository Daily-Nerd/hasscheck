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


# ---------------------------------------------------------------------------
# issue #100: manifest.requirements rules — fixture has
#   ["pyhomematic", "git+https://github.com/example/lib.git"]
#   → is_list PASS, entries_well_formed PASS, no_git_or_url_specs WARN
# ---------------------------------------------------------------------------


def test_requirements_is_list_passes_on_bad_integration_fixture() -> None:
    """Fixture requirements is a list — is_list must PASS."""
    findings = _findings_by_id()
    assert findings["manifest.requirements.is_list"].status is RuleStatus.PASS


def test_requirements_well_formed_passes_on_bad_integration_fixture() -> None:
    """Fixture has 'pyhomematic' (valid PEP 508) + git+ (filtered) — entries_well_formed PASS."""
    findings = _findings_by_id()
    assert (
        findings["manifest.requirements.entries_well_formed"].status is RuleStatus.PASS
    )


def test_requirements_no_git_warns_on_bad_integration_fixture() -> None:
    """Fixture has git+https://... entry — no_git_or_url_specs must WARN."""
    findings = _findings_by_id()
    f = findings["manifest.requirements.no_git_or_url_specs"]
    assert f.status is RuleStatus.WARN
    assert "git+https://github.com/example/lib.git" in f.message


# ---------------------------------------------------------------------------
# issue #101: config_flow advanced rules — bad fixture has async_step_setup
# (no reauth, no reconfigure, no unique_id, no discovery-flow step)
# All four must WARN.
# ---------------------------------------------------------------------------


def test_reauth_step_warns_on_bad_integration_fixture() -> None:
    """Fixture config_flow.py has no reauth step — must WARN."""
    findings = _findings_by_id()
    assert findings["config_flow.reauth_step.exists"].status is RuleStatus.WARN


def test_reconfigure_step_warns_on_bad_integration_fixture() -> None:
    """Fixture config_flow.py has no reconfigure step — must WARN."""
    findings = _findings_by_id()
    assert findings["config_flow.reconfigure_step.exists"].status is RuleStatus.WARN


def test_unique_id_set_warns_on_bad_integration_fixture() -> None:
    """Fixture config_flow.py has no async_set_unique_id call — must WARN."""
    findings = _findings_by_id()
    assert findings["config_flow.unique_id.set"].status is RuleStatus.WARN


def test_connection_test_warns_on_bad_integration_fixture() -> None:
    """Fixture config_flow.py has no discovery-flow step — connection_test must WARN."""
    findings = _findings_by_id()
    assert findings["config_flow.connection_test"].status is RuleStatus.WARN


# ---------------------------------------------------------------------------
# issue #107: init.* rules — bad_integration __init__.py lacks async_setup_entry
# and runtime_data usage → both WARN.
# entity.* rules are NOT_APPLICABLE (no platform files in bad fixture).
# ---------------------------------------------------------------------------


def test_init_async_setup_entry_warns_on_bad_integration_fixture() -> None:
    """Fixture __init__.py has no async_setup_entry — must WARN."""
    findings = _findings_by_id()
    f = findings["init.async_setup_entry.defined"]
    assert f.status is RuleStatus.WARN


def test_init_runtime_data_warns_on_bad_integration_fixture() -> None:
    """Fixture __init__.py has no runtime_data usage — must WARN."""
    findings = _findings_by_id()
    f = findings["init.runtime_data.used"]
    assert f.status is RuleStatus.WARN
