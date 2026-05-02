"""Tests for integration test detection rules (issue #108, v0.11 first batch).

TDD cycle:
  - RED: written first, before production code exists
  - GREEN: confirmed after implementation

Rules covered:
  - tests.config_flow.detected
  - tests.setup_entry.detected
  - tests.unload.detected

Spec: issue #108 — integration test detection (heuristic, static inspection only)
Source: https://developers.home-assistant.io/docs/development_testing/
"""

from __future__ import annotations

from pathlib import Path

from hasscheck.checker import run_check
from hasscheck.models import RuleStatus
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_integration(
    root: Path,
    *,
    dir_name: str = "demo",
    manifest: str | None = None,
) -> Path:
    """Create custom_components/<dir_name>/ with a manifest.json."""
    integration = root / "custom_components" / dir_name
    integration.mkdir(parents=True)

    mf = manifest or (
        '{"domain": "'
        + dir_name
        + '", "name": "Test", "documentation": "https://example.com",'
        ' "issue_tracker": "https://example.com/issues", "codeowners": ["@test"],'
        ' "version": "0.1.0"}'
    )
    (integration / "manifest.json").write_text(mf, encoding="utf-8")
    return integration


def _write_tests_dir(root: Path) -> Path:
    """Create tests/ directory at repo root."""
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    return tests_dir


def _finding_for(root: Path, rule_id: str):
    return {f.rule_id: f for f in run_check(root).findings}[rule_id]


# ===========================================================================
# tests.config_flow.detected
# ===========================================================================

CF_RULE = "tests.config_flow.detected"


class TestConfigFlowDetected:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[CF_RULE]
        assert rule.id == CF_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "tests_ci"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_not_applicable_without_integration(self, tmp_path: Path) -> None:
        """No integration directory → NOT_APPLICABLE."""
        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_without_tests_folder(self, tmp_path: Path) -> None:
        """Integration exists but tests/ missing → NOT_APPLICABLE."""
        _write_integration(tmp_path)
        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_pass_by_filename(self, tmp_path: Path) -> None:
        """tests/test_config_flow.py filename pattern → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_config_flow.py").write_text("", encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_filename_variant(self, tmp_path: Path) -> None:
        """tests/test_config_flow_user.py also matches filename pattern → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_config_flow_user.py").write_text("", encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_ast_import(self, tmp_path: Path) -> None:
        """File imports from config_flow module → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "from custom_components.demo.config_flow import DemoConfigFlow\n"
        (tests / "test_things.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_function_name(self, tmp_path: Path) -> None:
        """Function named test_config_flow_user_step → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "def test_config_flow_user_step():\n    pass\n"
        (tests / "test_things.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_async_step_function_name(self, tmp_path: Path) -> None:
        """Function named test_async_step_user → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "async def test_async_step_user():\n    pass\n"
        (tests / "test_things.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.PASS

    def test_warn_when_tests_dir_exists_but_no_match(self, tmp_path: Path) -> None:
        """tests/ folder with unrelated test file → WARN."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "def test_something_else():\n    pass\n"
        (tests / "test_unrelated.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.WARN

    def test_warn_empty_tests_dir(self, tmp_path: Path) -> None:
        """Empty tests/ folder → WARN."""
        _write_integration(tmp_path)
        _write_tests_dir(tmp_path)

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.WARN

    def test_parse_error_tolerated_other_file_passes(self, tmp_path: Path) -> None:
        """Syntax error in one file is skipped; another file that matches → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_broken.py").write_text("def (((:\n", encoding="utf-8")
        (tests / "test_config_flow.py").write_text("", encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.PASS

    def test_parse_error_all_files_broken_warns(self, tmp_path: Path) -> None:
        """All test files have syntax errors and no filename match → WARN."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_broken.py").write_text("def (((:\n", encoding="utf-8")
        (tests / "test_also_broken.py").write_text("class )(:\n", encoding="utf-8")

        finding = _finding_for(tmp_path, CF_RULE)
        assert finding.status is RuleStatus.WARN


# ===========================================================================
# tests.setup_entry.detected
# ===========================================================================

SE_RULE = "tests.setup_entry.detected"


class TestSetupEntryDetected:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[SE_RULE]
        assert rule.id == SE_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "tests_ci"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_not_applicable_without_integration(self, tmp_path: Path) -> None:
        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_without_tests_folder(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_pass_by_name_reference(self, tmp_path: Path) -> None:
        """AST Name node referencing async_setup_entry → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "result = await async_setup_entry(hass, entry)\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_attribute_reference(self, tmp_path: Path) -> None:
        """AST Attribute node referencing async_setup_entry → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "mock.async_setup_entry.return_value = True\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_unload_reference(self, tmp_path: Path) -> None:
        """async_unload_entry reference also counts → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "await async_unload_entry(hass, entry)\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_function_name_setup(self, tmp_path: Path) -> None:
        """Function named test_setup_entry_ok → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "async def test_setup_entry_ok():\n    pass\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_function_name_async_setup(self, tmp_path: Path) -> None:
        """Function named test_async_setup_entry_success → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "async def test_async_setup_entry_success():\n    pass\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.PASS

    def test_warn_when_no_match(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "def test_something_else():\n    pass\n"
        (tests / "test_unrelated.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.WARN

    def test_parse_error_tolerated_other_file_passes(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_broken.py").write_text("def (((:\n", encoding="utf-8")
        src = "async def test_async_setup_entry_ok():\n    pass\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.PASS

    def test_parse_error_all_files_broken_warns(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_broken.py").write_text("def (((:\n", encoding="utf-8")

        finding = _finding_for(tmp_path, SE_RULE)
        assert finding.status is RuleStatus.WARN


# ===========================================================================
# tests.unload.detected
# ===========================================================================

UNLOAD_RULE = "tests.unload.detected"


class TestUnloadDetected:
    def test_rule_is_registered(self) -> None:
        rule = RULES_BY_ID[UNLOAD_RULE]
        assert rule.id == UNLOAD_RULE
        assert rule.version == "1.0.0"
        assert rule.category == "tests_ci"
        assert str(rule.severity) == "recommended"
        assert rule.overridable is True
        assert rule.why

    def test_not_applicable_without_integration(self, tmp_path: Path) -> None:
        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_not_applicable_without_tests_folder(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.NOT_APPLICABLE

    def test_pass_by_name_reference(self, tmp_path: Path) -> None:
        """async_unload_entry Name reference → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "await async_unload_entry(hass, entry)\n"
        (tests / "test_unload.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_attribute_reference(self, tmp_path: Path) -> None:
        """async_unload_entry Attribute reference → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "mock.async_unload_entry.return_value = True\n"
        (tests / "test_unload.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_function_name_unload(self, tmp_path: Path) -> None:
        """Function named test_unload_entry → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "async def test_unload_entry():\n    pass\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.PASS

    def test_pass_by_function_name_async_unload(self, tmp_path: Path) -> None:
        """Function named test_async_unload_works → PASS."""
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "async def test_async_unload_works():\n    pass\n"
        (tests / "test_init.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.PASS

    def test_warn_when_no_match(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        src = "def test_something_else():\n    pass\n"
        (tests / "test_unrelated.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.WARN

    def test_parse_error_tolerated_other_file_passes(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_broken.py").write_text("def (((:\n", encoding="utf-8")
        src = "async def test_unload_ok():\n    pass\n"
        (tests / "test_unload.py").write_text(src, encoding="utf-8")

        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.PASS

    def test_parse_error_all_files_broken_warns(self, tmp_path: Path) -> None:
        _write_integration(tmp_path)
        tests = _write_tests_dir(tmp_path)
        (tests / "test_broken.py").write_text("def (((:\n", encoding="utf-8")

        finding = _finding_for(tmp_path, UNLOAD_RULE)
        assert finding.status is RuleStatus.WARN
