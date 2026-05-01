"""Tests for hasscheck.scaffold.engine — TDD first pass.

Tests cover:
- load_template: loads a .tmpl file via importlib.resources
- render: performs $-style substitution on a template string
- write_or_refuse: file write helper with force / dry_run semantics
- check_applicability_gate: returns warning or None based on config flags
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hasscheck.config import HassCheckConfig, ProjectApplicability
from hasscheck.scaffold.engine import (
    check_applicability_gate,
    load_template,
    render,
    write_or_refuse,
)

# ---------------------------------------------------------------------------
# load_template
# ---------------------------------------------------------------------------


class TestLoadTemplate:
    def test_load_template_returns_string(self) -> None:
        """load_template should return the raw text of a .tmpl file."""
        fake_content = "Hello $domain, welcome to diagnostics."
        mock_files = MagicMock()
        mock_path = MagicMock()
        mock_path.read_text.return_value = fake_content
        mock_files.return_value.joinpath.return_value = mock_path

        with patch("hasscheck.scaffold.engine.files", mock_files):
            result = load_template("diagnostics.tmpl")

        mock_files.assert_called_once_with("hasscheck.scaffold.templates")
        mock_path.read_text.assert_called_once_with(encoding="utf-8")
        assert result == fake_content

    def test_load_template_passes_name_to_joinpath(self) -> None:
        """load_template must join the template name, not a hardcoded path."""
        mock_files = MagicMock()
        mock_path = MagicMock()
        mock_path.read_text.return_value = "content"
        mock_files.return_value.joinpath.return_value = mock_path

        with patch("hasscheck.scaffold.engine.files", mock_files):
            load_template("repairs.tmpl")

        mock_files.return_value.joinpath.assert_called_once_with("repairs.tmpl")

    def test_load_template_raises_if_file_missing(self) -> None:
        """load_template should propagate FileNotFoundError for unknown templates."""
        mock_files = MagicMock()
        mock_path = MagicMock()
        mock_path.read_text.side_effect = FileNotFoundError("not found")
        mock_files.return_value.joinpath.return_value = mock_path

        with patch("hasscheck.scaffold.engine.files", mock_files):
            with pytest.raises(FileNotFoundError):
                load_template("nonexistent.tmpl")


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


class TestRender:
    def test_render_substitutes_single_variable(self) -> None:
        template = "Hello $domain!"
        result = render(template, {"domain": "my_integration"})
        assert result == "Hello my_integration!"

    def test_render_substitutes_multiple_variables(self) -> None:
        template = "domain=$domain version=$version"
        result = render(template, {"domain": "abc", "version": "1.0"})
        assert result == "domain=abc version=1.0"

    def test_render_leaves_unrelated_content_intact(self) -> None:
        template = "no variables here"
        result = render(template, {})
        assert result == "no variables here"

    def test_render_raises_on_missing_key(self) -> None:
        """string.Template raises KeyError when a variable has no mapping."""
        template = "$domain and $missing"
        with pytest.raises(KeyError):
            render(template, {"domain": "abc"})

    def test_render_empty_substitution_map(self) -> None:
        """Template with no variables should pass through with empty mapping."""
        template = "static content"
        result = render(template, {})
        assert result == "static content"


# ---------------------------------------------------------------------------
# write_or_refuse
# ---------------------------------------------------------------------------


class TestWriteOrRefuse:
    def test_writes_when_file_does_not_exist(self, tmp_path: Path) -> None:
        target = tmp_path / "output.py"
        write_or_refuse(target, "content here")
        assert target.read_text(encoding="utf-8") == "content here"

    def test_raises_file_exists_error_when_exists_and_no_force(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "existing.py"
        target.write_text("old content", encoding="utf-8")

        with pytest.raises(FileExistsError) as exc_info:
            write_or_refuse(target, "new content")

        assert str(target) in str(exc_info.value) or "existing.py" in str(
            exc_info.value
        )

    def test_overwrites_when_exists_and_force_true(self, tmp_path: Path) -> None:
        target = tmp_path / "existing.py"
        target.write_text("old content", encoding="utf-8")

        write_or_refuse(target, "new content", force=True)

        assert target.read_text(encoding="utf-8") == "new content"

    def test_dry_run_prints_to_stdout_and_does_not_write(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = tmp_path / "output.py"
        write_or_refuse(target, "dry run content", dry_run=True)

        # File must NOT be created
        assert not target.exists()

        # Content must appear on stdout
        captured = capsys.readouterr()
        assert "dry run content" in captured.out

    def test_dry_run_on_existing_file_does_not_raise(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """dry_run=True should bypass the FileExistsError check."""
        target = tmp_path / "existing.py"
        target.write_text("old content", encoding="utf-8")

        # Should not raise even though file exists
        write_or_refuse(target, "new content", dry_run=True)

        # Original file must be unchanged
        assert target.read_text(encoding="utf-8") == "old content"


# ---------------------------------------------------------------------------
# check_applicability_gate
# ---------------------------------------------------------------------------


class TestCheckApplicabilityGate:
    def test_none_config_allows_all(self) -> None:
        """No config means no restrictions — all scaffold types are allowed."""
        result = check_applicability_gate(None, "diagnostics")
        assert result is None

    def test_none_config_allows_repairs(self) -> None:
        result = check_applicability_gate(None, "repairs")
        assert result is None

    def test_none_config_allows_github_action(self) -> None:
        result = check_applicability_gate(None, "github-action")
        assert result is None

    # --- diagnostics ---

    def test_diagnostics_refused_when_flag_explicitly_false(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(supports_diagnostics=False)
        )
        result = check_applicability_gate(config, "diagnostics")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_diagnostics_allowed_when_flag_true(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(supports_diagnostics=True)
        )
        result = check_applicability_gate(config, "diagnostics")
        assert result is None

    def test_diagnostics_allowed_when_flag_none(self) -> None:
        """Unset flag (None) must NOT block generation."""
        config = HassCheckConfig(
            applicability=ProjectApplicability(supports_diagnostics=None)
        )
        result = check_applicability_gate(config, "diagnostics")
        assert result is None

    def test_diagnostics_allowed_when_applicability_block_absent(self) -> None:
        config = HassCheckConfig()
        result = check_applicability_gate(config, "diagnostics")
        assert result is None

    # --- repairs ---

    def test_repairs_refused_when_flag_explicitly_false(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(has_user_fixable_repairs=False)
        )
        result = check_applicability_gate(config, "repairs")
        assert result is not None
        assert isinstance(result, str)

    def test_repairs_allowed_when_flag_true(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(has_user_fixable_repairs=True)
        )
        result = check_applicability_gate(config, "repairs")
        assert result is None

    def test_repairs_allowed_when_flag_none(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(has_user_fixable_repairs=None)
        )
        result = check_applicability_gate(config, "repairs")
        assert result is None

    # --- github-action (no applicability gate) ---

    def test_github_action_always_allowed_even_with_restrictive_config(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(
                supports_diagnostics=False,
                has_user_fixable_repairs=False,
            )
        )
        result = check_applicability_gate(config, "github-action")
        assert result is None

    # --- unknown scaffold type ---

    def test_unknown_scaffold_type_allowed(self) -> None:
        """Unknown scaffold types have no gate — return None (allow)."""
        config = HassCheckConfig()
        result = check_applicability_gate(config, "some-future-type")
        assert result is None

    # --- warning message quality ---

    def test_diagnostics_warning_mentions_flag_name(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(supports_diagnostics=False)
        )
        result = check_applicability_gate(config, "diagnostics")
        assert result is not None
        assert "supports_diagnostics" in result

    def test_repairs_warning_mentions_flag_name(self) -> None:
        config = HassCheckConfig(
            applicability=ProjectApplicability(has_user_fixable_repairs=False)
        )
        result = check_applicability_gate(config, "repairs")
        assert result is not None
        assert "has_user_fixable_repairs" in result
