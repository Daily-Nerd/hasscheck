"""Tests for manifest.iot_class.{exists,valid} and manifest.integration_type.{exists,valid} (PR2, #52).

TDD cycle:
  - RED: written first, references production code that does not yet exist
  - GREEN: confirmed after implementation

Spec: sdd/v0-8-rule-depth/spec — Domain: manifest-rules (#52)
Design: D5 (frozensets), D7 (exact message strings)
"""

from __future__ import annotations

import json

import pytest

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(
    root, manifest: dict | None, *, raw_json: str | None = None
) -> None:
    """Create custom_components/test_integration/manifest.json."""
    integration = root / "custom_components" / "test_integration"
    integration.mkdir(parents=True)
    if raw_json is not None:
        (integration / "manifest.json").write_text(raw_json, encoding="utf-8")
    elif manifest is not None:
        (integration / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )


def _base_manifest(**extra) -> dict:
    """Minimal valid manifest with overridable fields."""
    return {
        "domain": "test_integration",
        "name": "Test Integration",
        "documentation": "https://example.com",
        "issue_tracker": "https://example.com/issues",
        "codeowners": ["@test"],
        "version": "0.1.0",
        **extra,
    }


def _findings_for(root):
    return {finding.rule_id: finding for finding in run_check(root).findings}


# ---------------------------------------------------------------------------
# Rule registration: all four rules must be present in the registry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rule_id",
    [
        "manifest.iot_class.exists",
        "manifest.iot_class.valid",
        "manifest.integration_type.exists",
        "manifest.integration_type.valid",
    ],
)
def test_rule_is_registered(rule_id: str) -> None:
    rule = RULES_BY_ID[rule_id]
    assert rule.id == rule_id
    assert rule.version == "1.0.0"
    assert rule.category == "manifest_metadata"
    assert str(rule.severity) == "recommended"
    assert rule.overridable is True
    assert rule.why, f"{rule_id}.why must be non-empty"


# ---------------------------------------------------------------------------
# manifest.iot_class.exists
# ---------------------------------------------------------------------------

IOT_CLASS_EXISTS_ID = "manifest.iot_class.exists"


def test_iot_class_exists_pass_when_field_present(tmp_path) -> None:
    """PASS when iot_class is present (any non-empty value)."""
    _write_manifest(tmp_path, _base_manifest(iot_class="local_polling"))
    findings = _findings_for(tmp_path)
    assert findings[IOT_CLASS_EXISTS_ID].status is RuleStatus.PASS


def test_iot_class_exists_warn_when_field_missing(tmp_path) -> None:
    """WARN when iot_class is absent."""
    _write_manifest(tmp_path, _base_manifest())
    findings = _findings_for(tmp_path)
    f = findings[IOT_CLASS_EXISTS_ID]
    assert f.status is RuleStatus.WARN
    assert "iot_class" in f.message


def test_iot_class_exists_not_applicable_when_no_manifest(tmp_path) -> None:
    """NOT_APPLICABLE when there is no manifest.json."""
    # No custom_components directory at all
    findings = _findings_for(tmp_path)
    assert findings[IOT_CLASS_EXISTS_ID].status is RuleStatus.NOT_APPLICABLE


def test_iot_class_exists_fail_when_manifest_is_invalid_json(tmp_path) -> None:
    """FAIL when manifest.json exists but cannot be parsed."""
    _write_manifest(tmp_path, None, raw_json="{invalid json here")
    findings = _findings_for(tmp_path)
    assert findings[IOT_CLASS_EXISTS_ID].status is RuleStatus.FAIL


# ---------------------------------------------------------------------------
# manifest.iot_class.valid
# ---------------------------------------------------------------------------

IOT_CLASS_VALID_ID = "manifest.iot_class.valid"

VALID_IOT_CLASSES = [
    "assumed_state",
    "calculated",
    "cloud_polling",
    "cloud_push",
    "local_polling",
    "local_push",
]


@pytest.mark.parametrize("value", VALID_IOT_CLASSES)
def test_iot_class_valid_pass_for_valid_value(tmp_path, value: str) -> None:
    """PASS for every value in the canonical frozenset."""
    _write_manifest(tmp_path, _base_manifest(iot_class=value))
    findings = _findings_for(tmp_path)
    assert findings[IOT_CLASS_VALID_ID].status is RuleStatus.PASS


def test_iot_class_valid_fail_for_invalid_value(tmp_path) -> None:
    """FAIL when iot_class is present but not in the allowed set."""
    _write_manifest(tmp_path, _base_manifest(iot_class="made_up_class"))
    findings = _findings_for(tmp_path)
    f = findings[IOT_CLASS_VALID_ID]
    assert f.status is RuleStatus.FAIL
    assert "made_up_class" in f.message
    # D7 exact substring: "is not a recognized value"
    assert "is not a recognized value" in f.message


def test_iot_class_valid_not_applicable_when_field_absent(tmp_path) -> None:
    """NOT_APPLICABLE when iot_class is absent (field not in manifest)."""
    _write_manifest(tmp_path, _base_manifest())
    findings = _findings_for(tmp_path)
    assert findings[IOT_CLASS_VALID_ID].status is RuleStatus.NOT_APPLICABLE


def test_iot_class_valid_not_applicable_when_no_manifest(tmp_path) -> None:
    """NOT_APPLICABLE when there is no manifest.json."""
    findings = _findings_for(tmp_path)
    assert findings[IOT_CLASS_VALID_ID].status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# manifest.integration_type.exists
# ---------------------------------------------------------------------------

INTEGRATION_TYPE_EXISTS_ID = "manifest.integration_type.exists"


def test_integration_type_exists_pass_when_field_present(tmp_path) -> None:
    """PASS when integration_type is present (any non-empty value)."""
    _write_manifest(tmp_path, _base_manifest(integration_type="hub"))
    findings = _findings_for(tmp_path)
    assert findings[INTEGRATION_TYPE_EXISTS_ID].status is RuleStatus.PASS


def test_integration_type_exists_warn_when_field_missing(tmp_path) -> None:
    """WARN when integration_type is absent."""
    _write_manifest(tmp_path, _base_manifest())
    findings = _findings_for(tmp_path)
    f = findings[INTEGRATION_TYPE_EXISTS_ID]
    assert f.status is RuleStatus.WARN
    assert "integration_type" in f.message


def test_integration_type_exists_not_applicable_when_no_manifest(tmp_path) -> None:
    """NOT_APPLICABLE when there is no manifest.json."""
    findings = _findings_for(tmp_path)
    assert findings[INTEGRATION_TYPE_EXISTS_ID].status is RuleStatus.NOT_APPLICABLE


def test_integration_type_exists_fail_when_manifest_is_invalid_json(tmp_path) -> None:
    """FAIL when manifest.json exists but cannot be parsed."""
    _write_manifest(tmp_path, None, raw_json="{invalid json here")
    findings = _findings_for(tmp_path)
    assert findings[INTEGRATION_TYPE_EXISTS_ID].status is RuleStatus.FAIL


# ---------------------------------------------------------------------------
# manifest.integration_type.valid
# ---------------------------------------------------------------------------

INTEGRATION_TYPE_VALID_ID = "manifest.integration_type.valid"

VALID_INTEGRATION_TYPES = [
    "device",
    "entity",
    "hardware",
    "helper",
    "hub",
    "service",
    "system",
    "virtual",
]


@pytest.mark.parametrize("value", VALID_INTEGRATION_TYPES)
def test_integration_type_valid_pass_for_valid_value(tmp_path, value: str) -> None:
    """PASS for every value in the canonical frozenset."""
    _write_manifest(tmp_path, _base_manifest(integration_type=value))
    findings = _findings_for(tmp_path)
    assert findings[INTEGRATION_TYPE_VALID_ID].status is RuleStatus.PASS


def test_integration_type_valid_fail_for_invalid_value(tmp_path) -> None:
    """FAIL when integration_type is present but not in the allowed set."""
    _write_manifest(tmp_path, _base_manifest(integration_type="fake_type"))
    findings = _findings_for(tmp_path)
    f = findings[INTEGRATION_TYPE_VALID_ID]
    assert f.status is RuleStatus.FAIL
    assert "fake_type" in f.message
    # D7 exact substring: "is not a recognized value"
    assert "is not a recognized value" in f.message


def test_integration_type_valid_not_applicable_when_field_absent(tmp_path) -> None:
    """NOT_APPLICABLE when integration_type is absent."""
    _write_manifest(tmp_path, _base_manifest())
    findings = _findings_for(tmp_path)
    assert findings[INTEGRATION_TYPE_VALID_ID].status is RuleStatus.NOT_APPLICABLE


def test_integration_type_valid_not_applicable_when_no_manifest(tmp_path) -> None:
    """NOT_APPLICABLE when there is no manifest.json."""
    findings = _findings_for(tmp_path)
    assert findings[INTEGRATION_TYPE_VALID_ID].status is RuleStatus.NOT_APPLICABLE
