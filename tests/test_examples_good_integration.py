"""Integration tests against the good_integration fixture.

Whitelist-asserts only the README content rules added in issue #55.
The good_integration README is designed to pass all five rules.
"""

from __future__ import annotations

from pathlib import Path

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus

FIXTURE_PATH = Path(__file__).parent.parent / "examples" / "good_integration"


def _findings_by_id():
    return {f.rule_id: f for f in run_check(FIXTURE_PATH).findings}


# ---------------------------------------------------------------------------
# issue #55 — README content rules pass on good_integration fixture
# ---------------------------------------------------------------------------


def test_installation_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.installation.exists"].status is RuleStatus.PASS


def test_configuration_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.configuration.exists"].status is RuleStatus.PASS


def test_troubleshooting_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.troubleshooting.exists"].status is RuleStatus.PASS


def test_removal_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.removal.exists"].status is RuleStatus.PASS


def test_privacy_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.privacy.exists"].status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# issue #102 — four more README content rules pass on good_integration fixture
# ---------------------------------------------------------------------------


def test_examples_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.examples.exists"].status is RuleStatus.PASS


def test_supported_devices_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.supported_devices.exists"].status is RuleStatus.PASS


def test_limitations_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.limitations.exists"].status is RuleStatus.PASS


def test_hacs_instructions_passes_on_good_integration_fixture() -> None:
    findings = _findings_by_id()
    assert findings["docs.hacs_instructions.exists"].status is RuleStatus.PASS
