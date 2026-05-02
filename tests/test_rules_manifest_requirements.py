"""Tests for manifest.requirements sanity check rules (issue #100).

Rules:
  - manifest.requirements.is_list         (REQUIRED, overridable=False)
  - manifest.requirements.entries_well_formed  (RECOMMENDED, overridable=True)
  - manifest.requirements.no_git_or_url_specs  (RECOMMENDED, overridable=True)

TDD cycle:
  - RED: written first, production code does not yet exist
  - GREEN: confirmed after implementation
"""

from __future__ import annotations

import json

import pytest

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RULE_IS_LIST = "manifest.requirements.is_list"
RULE_WELL_FORMED = "manifest.requirements.entries_well_formed"
RULE_NO_GIT = "manifest.requirements.no_git_or_url_specs"

ALL_THREE = [RULE_IS_LIST, RULE_WELL_FORMED, RULE_NO_GIT]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {
    "domain": "demo",
    "name": "Demo",
    "documentation": "https://example.com",
    "issue_tracker": "https://example.com/issues",
    "codeowners": ["@demo"],
    "version": "0.1.0",
}


def _write_manifest(
    root, manifest: dict | None, *, raw_json: str | None = None
) -> None:
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    if raw_json is not None:
        (integration / "manifest.json").write_text(raw_json, encoding="utf-8")
    elif manifest is not None:
        (integration / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )


def _findings(root):
    return {f.rule_id: f for f in run_check(root).findings}


# ---------------------------------------------------------------------------
# Rule registration checks
# ---------------------------------------------------------------------------


def test_is_list_rule_is_registered() -> None:
    rule = RULES_BY_ID[RULE_IS_LIST]
    assert rule.id == RULE_IS_LIST
    assert rule.overridable is False
    assert str(rule.severity) == "required"
    assert rule.version == "1.0.0"
    assert rule.why


def test_well_formed_rule_is_registered() -> None:
    rule = RULES_BY_ID[RULE_WELL_FORMED]
    assert rule.id == RULE_WELL_FORMED
    assert rule.overridable is True
    assert str(rule.severity) == "recommended"
    assert rule.version == "1.0.0"
    assert rule.why


def test_no_git_rule_is_registered() -> None:
    rule = RULES_BY_ID[RULE_NO_GIT]
    assert rule.id == RULE_NO_GIT
    assert rule.overridable is True
    assert str(rule.severity) == "recommended"
    assert rule.version == "1.0.0"
    assert rule.why


# ---------------------------------------------------------------------------
# Missing manifest → all three NOT_APPLICABLE
# ---------------------------------------------------------------------------


def test_all_not_applicable_when_manifest_missing(tmp_path) -> None:
    """No manifest.json at all — all three rules are NOT_APPLICABLE."""
    # Create integration dir but no manifest
    (tmp_path / "custom_components" / "demo").mkdir(parents=True)
    f = _findings(tmp_path)
    for rule_id in ALL_THREE:
        assert f[rule_id].status is RuleStatus.NOT_APPLICABLE, (
            f"{rule_id}: expected NOT_APPLICABLE, got {f[rule_id].status}"
        )


def test_all_not_applicable_when_no_integration_dir(tmp_path) -> None:
    """No custom_components/ at all — all three rules are NOT_APPLICABLE."""
    f = _findings(tmp_path)
    for rule_id in ALL_THREE:
        assert f[rule_id].status is RuleStatus.NOT_APPLICABLE, (
            f"{rule_id}: expected NOT_APPLICABLE, got {f[rule_id].status}"
        )


# ---------------------------------------------------------------------------
# requirements key absent → all three NOT_APPLICABLE
# ---------------------------------------------------------------------------


def test_all_not_applicable_when_requirements_key_absent(tmp_path) -> None:
    """Manifest present but no 'requirements' key — all three NOT_APPLICABLE."""
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS})
    f = _findings(tmp_path)
    for rule_id in ALL_THREE:
        assert f[rule_id].status is RuleStatus.NOT_APPLICABLE, (
            f"{rule_id}: expected NOT_APPLICABLE, got {f[rule_id].status}"
        )


# ---------------------------------------------------------------------------
# requirements present but not a list
# ---------------------------------------------------------------------------


def test_is_list_fails_when_requirements_is_string(tmp_path) -> None:
    _write_manifest(
        tmp_path, {**_REQUIRED_FIELDS, "requirements": "pyhomematic==0.1.77"}
    )
    f = _findings(tmp_path)
    assert f[RULE_IS_LIST].status is RuleStatus.FAIL
    assert "str" in f[RULE_IS_LIST].message


def test_is_list_fails_when_requirements_is_number(tmp_path) -> None:
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": 42})
    f = _findings(tmp_path)
    assert f[RULE_IS_LIST].status is RuleStatus.FAIL
    assert "int" in f[RULE_IS_LIST].message


def test_is_list_fails_when_requirements_is_object(tmp_path) -> None:
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": {"pkg": "1.0"}})
    f = _findings(tmp_path)
    assert f[RULE_IS_LIST].status is RuleStatus.FAIL
    assert "dict" in f[RULE_IS_LIST].message


def test_well_formed_not_applicable_when_requirements_is_not_list(tmp_path) -> None:
    _write_manifest(
        tmp_path, {**_REQUIRED_FIELDS, "requirements": "pyhomematic==0.1.77"}
    )
    f = _findings(tmp_path)
    assert f[RULE_WELL_FORMED].status is RuleStatus.NOT_APPLICABLE


def test_no_git_not_applicable_when_requirements_is_not_list(tmp_path) -> None:
    _write_manifest(
        tmp_path, {**_REQUIRED_FIELDS, "requirements": "pyhomematic==0.1.77"}
    )
    f = _findings(tmp_path)
    assert f[RULE_NO_GIT].status is RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# Empty list → all pass (degenerate case)
# ---------------------------------------------------------------------------


def test_empty_requirements_list_all_pass(tmp_path) -> None:
    """requirements: [] — is_list PASS, well_formed PASS, no_git PASS."""
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": []})
    f = _findings(tmp_path)
    assert f[RULE_IS_LIST].status is RuleStatus.PASS
    assert f[RULE_WELL_FORMED].status is RuleStatus.PASS
    assert f[RULE_NO_GIT].status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# Valid PEP 508 entries → all pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entries",
    [
        ["pyhomematic==0.1.77"],
        ["requests>=2.0"],
        ["pyhomematic==0.1.77", "requests>=2.0"],
        ["pyhomematic"],
        ["some-pkg>=1.0,<2.0"],
    ],
)
def test_all_pass_for_valid_pep508_entries(tmp_path, entries) -> None:
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": entries})
    f = _findings(tmp_path)
    assert f[RULE_IS_LIST].status is RuleStatus.PASS
    assert f[RULE_WELL_FORMED].status is RuleStatus.PASS
    assert f[RULE_NO_GIT].status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# Invalid PEP 508 entries → entries_well_formed FAIL
# ---------------------------------------------------------------------------


def test_well_formed_fails_on_invalid_pep508_entry(tmp_path) -> None:
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": ["<<bogus>>"]})
    f = _findings(tmp_path)
    assert f[RULE_WELL_FORMED].status is RuleStatus.FAIL
    assert "<<bogus>>" in f[RULE_WELL_FORMED].message


def test_well_formed_fails_names_the_bad_entry(tmp_path) -> None:
    """Mixed list with one valid + one invalid — FAIL and message names the bad entry."""
    _write_manifest(
        tmp_path,
        {**_REQUIRED_FIELDS, "requirements": ["requests>=2.0", "<<bogus>>"]},
    )
    f = _findings(tmp_path)
    assert f[RULE_WELL_FORMED].status is RuleStatus.FAIL
    assert "<<bogus>>" in f[RULE_WELL_FORMED].message


def test_well_formed_fails_on_non_string_entry_integer(tmp_path) -> None:
    """Non-string entry like 123 → FAIL with type info."""
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": [123]})
    f = _findings(tmp_path)
    assert f[RULE_WELL_FORMED].status is RuleStatus.FAIL
    assert "int" in f[RULE_WELL_FORMED].message


def test_well_formed_fails_on_non_string_entry_dict(tmp_path) -> None:
    """Non-string entry like {"x": 1} → FAIL with type info."""
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": [{"x": 1}]})
    f = _findings(tmp_path)
    assert f[RULE_WELL_FORMED].status is RuleStatus.FAIL
    assert "dict" in f[RULE_WELL_FORMED].message


# ---------------------------------------------------------------------------
# git+ / URL specs → no_git_or_url_specs WARN, well_formed PASS (filtered)
# ---------------------------------------------------------------------------


def test_no_git_warns_for_git_plus_entry(tmp_path) -> None:
    """git+https://... entry → no_git_or_url_specs WARN."""
    _write_manifest(
        tmp_path,
        {**_REQUIRED_FIELDS, "requirements": ["git+https://github.com/x/y.git"]},
    )
    f = _findings(tmp_path)
    assert f[RULE_NO_GIT].status is RuleStatus.WARN
    assert "git+https://github.com/x/y.git" in f[RULE_NO_GIT].message


def test_well_formed_passes_when_only_git_entry(tmp_path) -> None:
    """git+ entry is filtered out for PEP 508 parsing — well_formed PASS."""
    _write_manifest(
        tmp_path,
        {**_REQUIRED_FIELDS, "requirements": ["git+https://github.com/x/y.git"]},
    )
    f = _findings(tmp_path)
    assert f[RULE_WELL_FORMED].status is RuleStatus.PASS


def test_no_git_warns_for_https_url_entry(tmp_path) -> None:
    """https://example.com/wheel.whl entry → no_git_or_url_specs WARN."""
    _write_manifest(
        tmp_path,
        {**_REQUIRED_FIELDS, "requirements": ["https://example.com/wheel.whl"]},
    )
    f = _findings(tmp_path)
    assert f[RULE_NO_GIT].status is RuleStatus.WARN
    assert "https://example.com/wheel.whl" in f[RULE_NO_GIT].message


def test_no_git_warns_for_http_url_entry(tmp_path) -> None:
    """http://example.com/wheel.whl entry → no_git_or_url_specs WARN."""
    _write_manifest(
        tmp_path,
        {**_REQUIRED_FIELDS, "requirements": ["http://example.com/wheel.whl"]},
    )
    f = _findings(tmp_path)
    assert f[RULE_NO_GIT].status is RuleStatus.WARN


def test_no_git_not_applicable_when_empty_list(tmp_path) -> None:
    """requirements: [] → no entries, no_git PASS (not NOT_APPLICABLE — empty is trivially clean)."""
    _write_manifest(tmp_path, {**_REQUIRED_FIELDS, "requirements": []})
    f = _findings(tmp_path)
    # Empty list: passes (nothing to flag), consistent with test_empty_requirements_list_all_pass
    assert f[RULE_NO_GIT].status is RuleStatus.PASS


def test_no_git_passes_when_no_url_specs(tmp_path) -> None:
    """Normal PyPI specs → no_git PASS."""
    _write_manifest(
        tmp_path,
        {**_REQUIRED_FIELDS, "requirements": ["pyhomematic==0.1.77", "requests>=2.0"]},
    )
    f = _findings(tmp_path)
    assert f[RULE_NO_GIT].status is RuleStatus.PASS


def test_mixed_valid_and_git_entry(tmp_path) -> None:
    """One valid PyPI + one git+ → is_list PASS, well_formed PASS, no_git WARN."""
    _write_manifest(
        tmp_path,
        {
            **_REQUIRED_FIELDS,
            "requirements": ["pyhomematic", "git+https://github.com/example/lib.git"],
        },
    )
    f = _findings(tmp_path)
    assert f[RULE_IS_LIST].status is RuleStatus.PASS
    assert f[RULE_WELL_FORMED].status is RuleStatus.PASS
    assert f[RULE_NO_GIT].status is RuleStatus.WARN


# ---------------------------------------------------------------------------
# Manifest parse error → all three FAIL (consistent with existing manifest rules)
# ---------------------------------------------------------------------------


def test_all_fail_on_manifest_parse_error(tmp_path) -> None:
    """Invalid JSON manifest → all three rules FAIL."""
    _write_manifest(tmp_path, None, raw_json="{invalid json here")
    f = _findings(tmp_path)
    for rule_id in ALL_THREE:
        assert f[rule_id].status is RuleStatus.FAIL, (
            f"{rule_id}: expected FAIL on parse error, got {f[rule_id].status}"
        )
