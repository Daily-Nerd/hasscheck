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


# ---------------------------------------------------------------------------
# Group 2: ADVISORIES loader
# ---------------------------------------------------------------------------


def test_advisories_count_is_ten() -> None:
    """len(ADVISORIES) == 10 at import (spec S1)."""
    from hasscheck.advisories import ADVISORIES

    assert len(ADVISORIES) == 10, (
        f"Expected 10 advisories, got {len(ADVISORIES)}: {list(ADVISORIES.keys())}"
    )


def test_advisories_all_valid_instances() -> None:
    """Every value in ADVISORIES is an Advisory instance."""
    from hasscheck.advisories import ADVISORIES, Advisory

    for key, advisory in ADVISORIES.items():
        assert isinstance(advisory, Advisory), (
            f"ADVISORIES[{key!r}] is not an Advisory instance"
        )


def test_get_advisory_returns_matching_instance() -> None:
    """get_advisory returns Advisory for known id (spec S3)."""
    from hasscheck.advisories import ADVISORIES, get_advisory

    # Pick the first advisory ID from the loaded dict
    known_id = next(iter(ADVISORIES))
    result = get_advisory(known_id)

    assert result is not None
    assert result.id == known_id


def test_get_advisory_returns_none_for_unknown_id() -> None:
    """get_advisory returns None for unknown id."""
    from hasscheck.advisories import get_advisory

    result = get_advisory("nonexistent-advisory-id")

    assert result is None


def test_loader_malformed_yaml_raises_runtime_error(
    tmp_path: pytest.MonkeyPatch,
) -> None:
    """Malformed YAML (extra field) raises RuntimeError at load time (spec S2)."""

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    bad_yaml = data_dir / "bad-advisory.yaml"
    bad_yaml.write_text(
        "id: bad-advisory\n"
        "source_url: https://example.com\n"
        "title: Bad\n"
        "summary: Bad advisory\n"
        "affected_patterns: []\n"
        "rule_ids: []\n"
        "unknown_extra_field: should_fail\n",
        encoding="utf-8",
    )

    # Import loader module directly with patched data path
    from hasscheck.advisories import loader as loader_mod

    original_data_dir = loader_mod._DATA_DIR
    try:
        loader_mod._DATA_DIR = data_dir
        with pytest.raises(RuntimeError, match="bad-advisory"):
            loader_mod._load_all()
    finally:
        loader_mod._DATA_DIR = original_data_dir


def test_loader_missing_directory_raises_runtime_error(
    tmp_path: pytest.MonkeyPatch,
) -> None:
    """Missing data directory raises RuntimeError at load time."""
    from hasscheck.advisories import loader as loader_mod

    nonexistent = tmp_path / "does_not_exist"
    original_data_dir = loader_mod._DATA_DIR
    try:
        loader_mod._DATA_DIR = nonexistent
        with pytest.raises(RuntimeError, match="does_not_exist"):
            loader_mod._load_all()
    finally:
        loader_mod._DATA_DIR = original_data_dir
