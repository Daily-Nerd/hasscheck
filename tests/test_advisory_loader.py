"""Tests for Advisory Pydantic model and YAML loader."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Group 1: Advisory Pydantic model
# ---------------------------------------------------------------------------

VALID_ADVISORY_DATA = {
    "id": "ha-2025-03-unique-id-ip-source",
    "introduced_in": "2025.3",
    "enforced_in": None,
    "source_url": "https://developers.home-assistant.io/docs/example",
    "title": "Config flow unique ID derived from mutable IP address",
    "summary": "Using an IP address as the unique ID source is fragile.",
    "affected_patterns": ["async_set_unique_id called with IP-derived value"],
    "severity": "warn",
    "rule_ids": ["config_flow.unique_id.uses_ip_address"],
}


def test_advisory_valid_instantiation() -> None:
    """Advisory.model_validate with all required fields returns a valid instance."""
    from hasscheck.advisories import Advisory

    advisory = Advisory.model_validate(VALID_ADVISORY_DATA)

    assert advisory.id == "ha-2025-03-unique-id-ip-source"
    assert advisory.introduced_in == "2025.3"
    assert advisory.enforced_in is None
    assert advisory.severity == "warn"
    assert advisory.rule_ids == ["config_flow.unique_id.uses_ip_address"]


def test_advisory_extra_field_raises_validation_error() -> None:
    """Extra field in data raises ValidationError (extra='forbid')."""
    from hasscheck.advisories import Advisory

    bad_data = {**VALID_ADVISORY_DATA, "unknown_field": "unexpected"}

    with pytest.raises(ValidationError):
        Advisory.model_validate(bad_data)


def test_advisory_invalid_severity_raises_validation_error() -> None:
    """Invalid severity literal raises ValidationError."""
    from hasscheck.advisories import Advisory

    bad_data = {**VALID_ADVISORY_DATA, "severity": "critical"}

    with pytest.raises(ValidationError):
        Advisory.model_validate(bad_data)


def test_advisory_missing_required_field_raises_validation_error() -> None:
    """Missing required field (title) raises ValidationError."""
    from hasscheck.advisories import Advisory

    bad_data = {k: v for k, v in VALID_ADVISORY_DATA.items() if k != "title"}

    with pytest.raises(ValidationError):
        Advisory.model_validate(bad_data)


def test_advisory_defaults() -> None:
    """Optional fields have correct defaults."""
    from hasscheck.advisories import Advisory

    minimal_data = {
        "id": "ha-test-id",
        "source_url": "https://example.com",
        "title": "Test advisory",
        "summary": "Test summary",
        "affected_patterns": [],
        "rule_ids": [],
    }
    advisory = Advisory.model_validate(minimal_data)

    assert advisory.severity == "warn"
    assert advisory.introduced_in is None
    assert advisory.enforced_in is None
