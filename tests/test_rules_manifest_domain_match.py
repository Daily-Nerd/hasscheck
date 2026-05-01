"""Tests for manifest.domain.matches_directory rule (PR1, #51).

TDD cycle:
  - RED: written first, references production code that does not yet exist
  - GREEN: confirmed after implementation
"""

from __future__ import annotations

import json

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RULE_ID = "manifest.domain.matches_directory"


def _write_integration(
    root, *, dir_name: str, manifest: dict | None, raw_json: str | None = None
) -> None:
    """Create custom_components/<dir_name>/ with an optional manifest.json."""
    integration = root / "custom_components" / dir_name
    integration.mkdir(parents=True)
    if raw_json is not None:
        (integration / "manifest.json").write_text(raw_json, encoding="utf-8")
    elif manifest is not None:
        (integration / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )


def _findings_for(root):
    return {finding.rule_id: finding for finding in run_check(root).findings}


# ---------------------------------------------------------------------------
# Subtask 1.11: Explain reachability — rule is registered with non-empty why
# ---------------------------------------------------------------------------


def test_rule_is_registered_with_non_empty_why() -> None:
    rule = RULES_BY_ID[RULE_ID]
    assert rule.id == RULE_ID
    assert rule.overridable is False
    assert str(rule.severity) == "required"
    assert rule.version == "1.0.0"
    assert rule.why, "why field must be non-empty"


# ---------------------------------------------------------------------------
# Subtask 1.4 / 1.6: PASS when domain matches directory name
# ---------------------------------------------------------------------------


def test_pass_when_domain_matches_directory(tmp_path) -> None:
    _write_integration(
        tmp_path,
        dir_name="my_light",
        manifest={
            "domain": "my_light",
            "name": "My Light",
            "documentation": "https://example.com",
            "issue_tracker": "https://example.com/issues",
            "codeowners": ["@demo"],
            "version": "0.1.0",
        },
    )

    findings = _findings_for(tmp_path)

    assert findings[RULE_ID].status is RuleStatus.PASS
    assert "my_light" in findings[RULE_ID].message


# ---------------------------------------------------------------------------
# FAIL when domain differs from directory name
# ---------------------------------------------------------------------------


def test_fail_when_domain_does_not_match_directory(tmp_path) -> None:
    _write_integration(
        tmp_path,
        dir_name="my_light",
        manifest={
            "domain": "wrong_light",
            "name": "Wrong Light",
            "documentation": "https://example.com",
            "issue_tracker": "https://example.com/issues",
            "codeowners": ["@demo"],
            "version": "0.1.0",
        },
    )

    findings = _findings_for(tmp_path)

    assert findings[RULE_ID].status is RuleStatus.FAIL
    assert "wrong_light" in findings[RULE_ID].message
    assert "my_light" in findings[RULE_ID].message


# ---------------------------------------------------------------------------
# NOT_APPLICABLE when no integration directory
# ---------------------------------------------------------------------------


def test_not_applicable_when_no_integration_path(tmp_path) -> None:
    # No custom_components/ directory at all
    findings = _findings_for(tmp_path)

    assert findings[RULE_ID].status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# NOT_APPLICABLE when manifest is absent
# ---------------------------------------------------------------------------


def test_not_applicable_when_manifest_missing(tmp_path) -> None:
    # Integration directory exists but no manifest.json
    integration = tmp_path / "custom_components" / "my_light"
    integration.mkdir(parents=True)

    findings = _findings_for(tmp_path)

    assert findings[RULE_ID].status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# FAIL when manifest exists but cannot be parsed
# ---------------------------------------------------------------------------


def test_fail_when_manifest_is_invalid_json(tmp_path) -> None:
    _write_integration(
        tmp_path,
        dir_name="my_light",
        manifest=None,
        raw_json="{invalid json here",
    )

    findings = _findings_for(tmp_path)

    assert findings[RULE_ID].status is RuleStatus.FAIL
