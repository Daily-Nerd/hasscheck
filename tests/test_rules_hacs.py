"""Tests for hasscheck.rules.hacs — 9 HACS installability rules.

TDD cycle (strict):
  - RED: written first, references production code that does NOT exist yet
  - GREEN: confirmed after implementation
  - REFACTOR: code improved with tests still passing

Spec: sdd/145-hacs-rules/spec
Design: sdd/145-hacs-rules/design
Issue: #145
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_ctx(
    tmp_path: Path,
    *,
    integration_path: Path | None = None,
    domain: str | None = "my_domain",
):
    """Create a minimal ProjectContext backed by tmp_path."""
    from hasscheck.rules.base import ProjectContext

    return ProjectContext(
        root=tmp_path,
        integration_path=integration_path,
        domain=domain,
    )


def _write_hacs_json(root: Path, content: str | dict) -> Path:
    """Write hacs.json to root. Pass a string for raw content, dict for JSON-serialised."""
    path = root / "hacs.json"
    if isinstance(content, dict):
        path.write_text(json.dumps(content), encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Group 1: _read_hacs_json helper
# ---------------------------------------------------------------------------


class TestReadHacsJson:
    """Unit tests for the private _read_hacs_json helper."""

    def test_returns_dict_for_valid_file(self, tmp_path: Path) -> None:
        _write_hacs_json(tmp_path, {"name": "My Integration", "hacs": "1.0.0"})
        from hasscheck.rules.hacs import _read_hacs_json

        ctx = _make_ctx(tmp_path)
        result = _read_hacs_json(ctx)
        assert result == {"name": "My Integration", "hacs": "1.0.0"}

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        from hasscheck.rules.hacs import _read_hacs_json

        ctx = _make_ctx(tmp_path)
        result = _read_hacs_json(ctx)
        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        _write_hacs_json(tmp_path, "{broken json")
        from hasscheck.rules.hacs import _read_hacs_json

        ctx = _make_ctx(tmp_path)
        result = _read_hacs_json(ctx)
        assert result is None

    def test_returns_none_for_non_dict_root(self, tmp_path: Path) -> None:
        """A JSON array at the root should return None (not a dict)."""
        _write_hacs_json(tmp_path, '["name", "hacs"]')
        from hasscheck.rules.hacs import _read_hacs_json

        ctx = _make_ctx(tmp_path)
        result = _read_hacs_json(ctx)
        assert result is None


# ---------------------------------------------------------------------------
# Group 1: hacs.hacs_json_schema_valid rule
# ---------------------------------------------------------------------------


class TestHacsJsonSchemaValid:
    """Unit tests for check_hacs_json_schema_valid."""

    def test_absent_hacs_json_passes(self, tmp_path: Path) -> None:
        """hacs.json absent → PASS (HACS uses defaults)."""
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_hacs_json_schema_valid

        ctx = _make_ctx(tmp_path)
        finding = check_hacs_json_schema_valid(ctx)
        assert finding.status == RuleStatus.PASS
        assert finding.rule_id == "hacs.hacs_json_schema_valid"

    def test_invalid_json_fails(self, tmp_path: Path) -> None:
        """hacs.json present but invalid JSON → FAIL."""
        _write_hacs_json(tmp_path, "{broken json")
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_hacs_json_schema_valid

        ctx = _make_ctx(tmp_path)
        finding = check_hacs_json_schema_valid(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_unknown_key_fails(self, tmp_path: Path) -> None:
        """hacs.json with unknown key → FAIL."""
        _write_hacs_json(tmp_path, {"name": "x", "unknown_key": True})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_hacs_json_schema_valid

        ctx = _make_ctx(tmp_path)
        finding = check_hacs_json_schema_valid(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_missing_name_key_fails(self, tmp_path: Path) -> None:
        """hacs.json with all known keys but no 'name' → FAIL."""
        _write_hacs_json(tmp_path, {"content_in_root": False})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_hacs_json_schema_valid

        ctx = _make_ctx(tmp_path)
        finding = check_hacs_json_schema_valid(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_valid_schema_with_name_passes(self, tmp_path: Path) -> None:
        """hacs.json with valid schema and 'name' present → PASS."""
        _write_hacs_json(tmp_path, {"name": "My Integration", "hacs": "1.0.0"})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_hacs_json_schema_valid

        ctx = _make_ctx(tmp_path)
        finding = check_hacs_json_schema_valid(ctx)
        assert finding.status == RuleStatus.PASS

    def test_rule_severity_is_required(self, tmp_path: Path) -> None:
        """Rule definition must carry REQUIRED severity and overridable=False."""
        from hasscheck.models import RuleSeverity
        from hasscheck.rules.hacs import RULES

        schema_rule = next(r for r in RULES if r.id == "hacs.hacs_json_schema_valid")
        assert schema_rule.severity == RuleSeverity.REQUIRED
        assert schema_rule.overridable is False


# ---------------------------------------------------------------------------
# Group 2: hacs.one_integration_per_repo rule
# ---------------------------------------------------------------------------


class TestOneIntegrationPerRepo:
    """Unit tests for check_one_integration_per_repo."""

    def test_single_integration_passes(self, tmp_path: Path) -> None:
        """One subdir with manifest.json → PASS."""
        cc = tmp_path / "custom_components" / "my_domain"
        cc.mkdir(parents=True)
        (cc / "manifest.json").write_text("{}", encoding="utf-8")

        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_one_integration_per_repo

        ctx = _make_ctx(tmp_path)
        finding = check_one_integration_per_repo(ctx)
        assert finding.status == RuleStatus.PASS
        assert finding.rule_id == "hacs.one_integration_per_repo"

    def test_two_integrations_fails(self, tmp_path: Path) -> None:
        """Two subdirs with manifest.json → FAIL."""
        for domain in ("a", "b"):
            d = tmp_path / "custom_components" / domain
            d.mkdir(parents=True)
            (d / "manifest.json").write_text("{}", encoding="utf-8")

        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_one_integration_per_repo

        ctx = _make_ctx(tmp_path)
        finding = check_one_integration_per_repo(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_no_custom_components_passes(self, tmp_path: Path) -> None:
        """No custom_components/ directory → PASS."""
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_one_integration_per_repo

        ctx = _make_ctx(tmp_path)
        finding = check_one_integration_per_repo(ctx)
        assert finding.status == RuleStatus.PASS

    def test_rule_severity_is_required(self, tmp_path: Path) -> None:
        """Rule definition must carry REQUIRED severity and overridable=False."""
        from hasscheck.models import RuleSeverity
        from hasscheck.rules.hacs import RULES

        rule = next(r for r in RULES if r.id == "hacs.one_integration_per_repo")
        assert rule.severity == RuleSeverity.REQUIRED
        assert rule.overridable is False


# ---------------------------------------------------------------------------
# Group 3: hacs.info_or_readme_present rule
# ---------------------------------------------------------------------------


class TestInfoOrReadmePresent:
    """Unit tests for check_info_or_readme_present."""

    def test_readme_md_present_and_non_empty_passes(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# My Integration\n", encoding="utf-8")
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_info_or_readme_present

        ctx = _make_ctx(tmp_path)
        finding = check_info_or_readme_present(ctx)
        assert finding.status == RuleStatus.PASS
        assert finding.rule_id == "hacs.info_or_readme_present"

    def test_info_md_present_and_non_empty_passes(self, tmp_path: Path) -> None:
        (tmp_path / "info.md").write_text("Some info.\n", encoding="utf-8")
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_info_or_readme_present

        ctx = _make_ctx(tmp_path)
        finding = check_info_or_readme_present(ctx)
        assert finding.status == RuleStatus.PASS

    def test_both_absent_fails(self, tmp_path: Path) -> None:
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_info_or_readme_present

        ctx = _make_ctx(tmp_path)
        finding = check_info_or_readme_present(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_file_present_but_empty_fails(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_bytes(b"")
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_info_or_readme_present

        ctx = _make_ctx(tmp_path)
        finding = check_info_or_readme_present(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_case_insensitive_readme_passes(self, tmp_path: Path) -> None:
        """readme.md (lowercase) must also be found."""
        (tmp_path / "readme.md").write_text("content", encoding="utf-8")
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_info_or_readme_present

        ctx = _make_ctx(tmp_path)
        finding = check_info_or_readme_present(ctx)
        assert finding.status == RuleStatus.PASS


# ---------------------------------------------------------------------------
# Group 3: hacs.download_strategy_clear rule
# ---------------------------------------------------------------------------


class TestDownloadStrategyClear:
    """Unit tests for check_download_strategy_clear."""

    def test_both_flags_true_fails(self, tmp_path: Path) -> None:
        _write_hacs_json(
            tmp_path, {"name": "x", "content_in_root": True, "zip_release": True}
        )
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_download_strategy_clear

        ctx = _make_ctx(tmp_path)
        finding = check_download_strategy_clear(ctx)
        assert finding.status == RuleStatus.FAIL
        assert finding.rule_id == "hacs.download_strategy_clear"

    def test_only_content_in_root_passes(self, tmp_path: Path) -> None:
        _write_hacs_json(tmp_path, {"name": "x", "content_in_root": True})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_download_strategy_clear

        ctx = _make_ctx(tmp_path)
        finding = check_download_strategy_clear(ctx)
        assert finding.status == RuleStatus.PASS

    def test_only_zip_release_passes(self, tmp_path: Path) -> None:
        _write_hacs_json(tmp_path, {"name": "x", "zip_release": True})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_download_strategy_clear

        ctx = _make_ctx(tmp_path)
        finding = check_download_strategy_clear(ctx)
        assert finding.status == RuleStatus.PASS

    def test_neither_flag_set_passes(self, tmp_path: Path) -> None:
        _write_hacs_json(tmp_path, {"name": "x"})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_download_strategy_clear

        ctx = _make_ctx(tmp_path)
        finding = check_download_strategy_clear(ctx)
        assert finding.status == RuleStatus.PASS

    def test_absent_hacs_json_passes(self, tmp_path: Path) -> None:
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_download_strategy_clear

        ctx = _make_ctx(tmp_path)
        finding = check_download_strategy_clear(ctx)
        assert finding.status == RuleStatus.PASS


# ---------------------------------------------------------------------------
# Group 3: hacs.content_in_root_consistent rule
# ---------------------------------------------------------------------------


class TestContentInRootConsistent:
    """Unit tests for check_content_in_root_consistent."""

    def test_content_in_root_true_no_custom_components_passes(
        self, tmp_path: Path
    ) -> None:
        _write_hacs_json(tmp_path, {"name": "x", "content_in_root": True})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_content_in_root_consistent

        ctx = _make_ctx(tmp_path)
        finding = check_content_in_root_consistent(ctx)
        assert finding.status == RuleStatus.PASS
        assert finding.rule_id == "hacs.content_in_root_consistent"

    def test_content_in_root_true_custom_components_present_fails(
        self, tmp_path: Path
    ) -> None:
        _write_hacs_json(tmp_path, {"name": "x", "content_in_root": True})
        (tmp_path / "custom_components").mkdir()
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_content_in_root_consistent

        ctx = _make_ctx(tmp_path)
        finding = check_content_in_root_consistent(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_content_in_root_false_custom_components_present_passes(
        self, tmp_path: Path
    ) -> None:
        _write_hacs_json(tmp_path, {"name": "x", "content_in_root": False})
        (tmp_path / "custom_components").mkdir()
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_content_in_root_consistent

        ctx = _make_ctx(tmp_path)
        finding = check_content_in_root_consistent(ctx)
        assert finding.status == RuleStatus.PASS

    def test_content_in_root_absent_custom_components_present_passes(
        self, tmp_path: Path
    ) -> None:
        _write_hacs_json(tmp_path, {"name": "x"})
        (tmp_path / "custom_components").mkdir()
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_content_in_root_consistent

        ctx = _make_ctx(tmp_path)
        finding = check_content_in_root_consistent(ctx)
        assert finding.status == RuleStatus.PASS

    def test_content_in_root_false_no_custom_components_fails(
        self, tmp_path: Path
    ) -> None:
        _write_hacs_json(tmp_path, {"name": "x", "content_in_root": False})
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_content_in_root_consistent

        ctx = _make_ctx(tmp_path)
        finding = check_content_in_root_consistent(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_absent_hacs_json_not_applicable(self, tmp_path: Path) -> None:
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_content_in_root_consistent

        ctx = _make_ctx(tmp_path)
        finding = check_content_in_root_consistent(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# Group 4: hacs.default_branch_installable rule
# ---------------------------------------------------------------------------


class TestDefaultBranchInstallable:
    """Unit tests for check_default_branch_installable."""

    def test_integration_dir_with_manifest_passes(self, tmp_path: Path) -> None:
        integration = tmp_path / "custom_components" / "my_domain"
        integration.mkdir(parents=True)
        (integration / "manifest.json").write_text("{}", encoding="utf-8")
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_default_branch_installable

        ctx = _make_ctx(tmp_path, integration_path=integration)
        finding = check_default_branch_installable(ctx)
        assert finding.status == RuleStatus.PASS
        assert finding.rule_id == "hacs.default_branch_installable"

    def test_integration_dir_without_manifest_fails(self, tmp_path: Path) -> None:
        integration = tmp_path / "custom_components" / "my_domain"
        integration.mkdir(parents=True)
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_default_branch_installable

        ctx = _make_ctx(tmp_path, integration_path=integration)
        finding = check_default_branch_installable(ctx)
        assert finding.status == RuleStatus.FAIL

    def test_no_integration_path_fails(self, tmp_path: Path) -> None:
        from hasscheck.models import RuleStatus
        from hasscheck.rules.hacs import check_default_branch_installable

        ctx = _make_ctx(tmp_path, integration_path=None)
        finding = check_default_branch_installable(ctx)
        assert finding.status == RuleStatus.FAIL


# ---------------------------------------------------------------------------
# Group 4: GH-API NOT_APPLICABLE rules
# ---------------------------------------------------------------------------


class TestNotApplicableHubRules:
    """Unit tests for the three GH-API rules that always return NOT_APPLICABLE."""

    @pytest.mark.parametrize(
        "check_fn_name,expected_rule_id",
        [
            ("check_release_zip_valid", "hacs.release_zip_valid"),
            ("check_github_release_assets_valid", "hacs.github_release_assets_valid"),
            ("check_repository_topics_present", "hacs.repository_topics_present"),
        ],
    )
    def test_returns_not_applicable(
        self,
        tmp_path: Path,
        check_fn_name: str,
        expected_rule_id: str,
    ) -> None:
        import hasscheck.rules.hacs as hacs_module
        from hasscheck.models import RuleStatus

        check_fn = getattr(hacs_module, check_fn_name)
        ctx = _make_ctx(tmp_path)
        finding = check_fn(ctx)
        assert finding.status == RuleStatus.NOT_APPLICABLE
        assert finding.rule_id == expected_rule_id

    @pytest.mark.parametrize(
        "check_fn_name",
        [
            "check_release_zip_valid",
            "check_github_release_assets_valid",
            "check_repository_topics_present",
        ],
    )
    def test_message_contains_github_api_not_available(
        self,
        tmp_path: Path,
        check_fn_name: str,
    ) -> None:
        import hasscheck.rules.hacs as hacs_module

        check_fn = getattr(hacs_module, check_fn_name)
        ctx = _make_ctx(tmp_path)
        finding = check_fn(ctx)
        assert "GitHub API not available in static check mode" in finding.message


# ---------------------------------------------------------------------------
# Group 5: Registry wiring — all 9 rule IDs must be present
# ---------------------------------------------------------------------------


_EXPECTED_RULE_IDS = {
    "hacs.one_integration_per_repo",
    "hacs.hacs_json_schema_valid",
    "hacs.content_in_root_consistent",
    "hacs.default_branch_installable",
    "hacs.info_or_readme_present",
    "hacs.download_strategy_clear",
    "hacs.release_zip_valid",
    "hacs.github_release_assets_valid",
    "hacs.repository_topics_present",
}


def test_all_9_hacs_rule_ids_in_registry() -> None:
    """All 9 new hacs.* rule IDs must be registered in RULES_BY_ID."""
    from hasscheck.rules.registry import RULES_BY_ID

    for rule_id in _EXPECTED_RULE_IDS:
        assert rule_id in RULES_BY_ID, f"Rule {rule_id!r} not found in RULES_BY_ID"


def test_registry_import_does_not_raise() -> None:
    """Importing the registry must not raise RuntimeError (no duplicate IDs)."""
    # Import is already done above — this confirms it was clean
    from hasscheck.rules.registry import RULES_BY_ID

    assert len(RULES_BY_ID) > 0


def test_registry_rule_metadata_correct() -> None:
    """Spot-check severity and overridable flags on wired rules."""
    from hasscheck.models import RuleSeverity
    from hasscheck.rules.registry import RULES_BY_ID

    required_non_overridable = {
        "hacs.one_integration_per_repo",
        "hacs.hacs_json_schema_valid",
    }
    recommended_overridable = {
        "hacs.content_in_root_consistent",
        "hacs.default_branch_installable",
        "hacs.info_or_readme_present",
        "hacs.download_strategy_clear",
        "hacs.release_zip_valid",
        "hacs.github_release_assets_valid",
        "hacs.repository_topics_present",
    }

    for rule_id in required_non_overridable:
        rule = RULES_BY_ID[rule_id]
        assert rule.severity == RuleSeverity.REQUIRED, f"{rule_id} should be REQUIRED"
        assert rule.overridable is False, f"{rule_id} should be non-overridable"

    for rule_id in recommended_overridable:
        rule = RULES_BY_ID[rule_id]
        assert rule.severity == RuleSeverity.RECOMMENDED, (
            f"{rule_id} should be RECOMMENDED"
        )
        assert rule.overridable is True, f"{rule_id} should be overridable"
