"""Tests for docs_render module — auto-generated per-rule docs pages."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from hasscheck.models import RuleSeverity
from hasscheck.rules.base import RuleDefinition
from hasscheck.rules.registry import RULES_BY_ID

# ---------------------------------------------------------------------------
# Minimal fixture rule for unit tests
# ---------------------------------------------------------------------------


def _make_rule(
    rule_id: str = "test.fake.rule",
    title: str = "Fake rule title",
    why: str = "Because testing is important.",
    category: str = "test_category",
    severity: RuleSeverity = RuleSeverity.REQUIRED,
    source_url: str = "https://example.com/docs",
    version: str = "1.0.0",
    overridable: bool = False,
    # --- 13 new optional metadata fields ---
    tags: tuple[str, ...] = (),
    profiles: tuple[str, ...] = (),
    min_ha_version: str | None = None,
    max_ha_version: str | None = None,
    introduced_by: str | None = None,
    introduced_at_version: str | None = None,
    advisory_id: str | None = None,
    related_quality_scale_rule: str | None = None,
    confidence: Literal["high", "medium", "low"] = "high",
    false_positive_notes: str | None = None,
    replacement_rule: str | None = None,
    deprecated: bool = False,
    deprecated_in_version: str | None = None,
) -> RuleDefinition:
    def _noop(ctx):  # pragma: no cover
        raise NotImplementedError

    return RuleDefinition(
        id=rule_id,
        version=version,
        category=category,
        severity=severity,
        title=title,
        why=why,
        source_url=source_url,
        check=_noop,
        overridable=overridable,
        tags=tags,
        profiles=profiles,
        min_ha_version=min_ha_version,
        max_ha_version=max_ha_version,
        introduced_by=introduced_by,
        introduced_at_version=introduced_at_version,
        advisory_id=advisory_id,
        related_quality_scale_rule=related_quality_scale_rule,
        confidence=confidence,
        false_positive_notes=false_positive_notes,
        replacement_rule=replacement_rule,
        deprecated=deprecated,
        deprecated_in_version=deprecated_in_version,
    )


# ---------------------------------------------------------------------------
# render_page
# ---------------------------------------------------------------------------


class TestRenderPage:
    """render_page() should produce correct Markdown for the auto section."""

    def test_includes_rule_id_as_heading(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(rule_id="manifest.exists")
        output = render_page(rule)

        assert "# manifest.exists" in output

    def test_includes_title(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(title="Manifest must exist")
        output = render_page(rule)

        assert "Manifest must exist" in output

    def test_includes_why(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(why="Integration needs a manifest to load.")
        output = render_page(rule)

        assert "Integration needs a manifest to load." in output

    def test_includes_source_url(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(source_url="https://developers.home-assistant.io/docs/test")
        output = render_page(rule)

        assert "https://developers.home-assistant.io/docs/test" in output

    def test_includes_category(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(category="manifest_metadata")
        output = render_page(rule)

        assert "manifest_metadata" in output

    def test_includes_severity(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(severity=RuleSeverity.RECOMMENDED)
        output = render_page(rule)

        assert "recommended" in output

    def test_includes_version(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(version="1.2.3")
        output = render_page(rule)

        assert "1.2.3" in output

    def test_includes_overridable(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(overridable=True)
        output = render_page(rule)

        assert "True" in output

    def test_inserts_handwritten_marker(self) -> None:
        from hasscheck.docs_render import _AUTOGEN_MARKER, render_page

        rule = _make_rule()
        output = render_page(rule)

        assert _AUTOGEN_MARKER in output

    def test_marker_is_at_end_of_generated_section(self) -> None:
        from hasscheck.docs_render import _AUTOGEN_MARKER, render_page

        rule = _make_rule()
        output = render_page(rule)

        # Marker should be the last meaningful line
        assert output.rstrip().endswith(_AUTOGEN_MARKER)


# ---------------------------------------------------------------------------
# write_page
# ---------------------------------------------------------------------------


class TestWritePage:
    """write_page() creates files and preserves handwritten sections."""

    def test_creates_new_file(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import write_page

        rule = _make_rule(rule_id="test.new.rule")
        path, was_changed = write_page(rule, tmp_path)

        assert path.is_file()
        assert path.name == "test.new.rule.md"
        assert was_changed is True

    def test_new_file_contains_auto_section(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import write_page

        rule = _make_rule(rule_id="test.new.rule", title="New rule")
        path, _ = write_page(rule, tmp_path)

        content = path.read_text(encoding="utf-8")
        assert "# test.new.rule" in content
        assert "New rule" in content

    def test_write_returns_false_when_no_change(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import write_page

        rule = _make_rule(rule_id="test.stable.rule")
        write_page(rule, tmp_path)
        _, was_changed = write_page(rule, tmp_path)

        assert was_changed is False

    def test_preserves_handwritten_section_below_marker(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import _AUTOGEN_MARKER, write_page

        rule = _make_rule(rule_id="test.preserve.rule")
        # Pre-write a file that already has a handwritten section
        existing_file = tmp_path / "test.preserve.rule.md"
        existing_file.write_text(
            f"# test.preserve.rule\n\n{_AUTOGEN_MARKER}\n\n## Examples\n\nSome hand-written example.",
            encoding="utf-8",
        )

        path, was_changed = write_page(rule, tmp_path)
        content = path.read_text(encoding="utf-8")

        assert "## Examples" in content
        assert "Some hand-written example." in content

    def test_updates_auto_section_and_keeps_handwritten(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import write_page

        rule_v1 = _make_rule(rule_id="test.update.rule", title="Old title")
        write_page(rule_v1, tmp_path)
        # Manually add handwritten section
        page = tmp_path / "test.update.rule.md"
        page.write_text(
            page.read_text(encoding="utf-8") + "\n\n## Notes\n\nKeep me.",
            encoding="utf-8",
        )

        rule_v2 = _make_rule(rule_id="test.update.rule", title="New title")
        _, was_changed = write_page(rule_v2, tmp_path)
        content = page.read_text(encoding="utf-8")

        assert "New title" in content
        assert "## Notes" in content
        assert "Keep me." in content
        assert was_changed is True

    def test_creates_parent_directory_if_missing(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import write_page

        docs_dir = tmp_path / "nested" / "docs" / "rules"
        rule = _make_rule(rule_id="test.nested.rule")
        path, _ = write_page(rule, docs_dir)

        assert path.is_file()


# ---------------------------------------------------------------------------
# render_all
# ---------------------------------------------------------------------------


class TestRenderAll:
    """render_all() should produce one page per registered rule."""

    def test_creates_a_page_per_rule(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import render_all

        results = render_all(tmp_path)

        assert len(results) == len(RULES_BY_ID)

    def test_all_pages_are_files(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import render_all

        render_all(tmp_path)

        for rule_id in RULES_BY_ID:
            page = tmp_path / f"{rule_id}.md"
            assert page.is_file(), f"Missing page: {rule_id}.md"

    def test_returns_changed_dict(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import render_all

        results = render_all(tmp_path)

        # All should be changed (new files) on first run
        assert all(v is True for v in results.values())

    def test_second_run_returns_no_changes(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import render_all

        render_all(tmp_path)
        results = render_all(tmp_path)

        assert all(v is False for v in results.values())


# ---------------------------------------------------------------------------
# check_drift
# ---------------------------------------------------------------------------


class TestCheckDrift:
    """check_drift() should detect stale auto sections."""

    def test_returns_empty_when_all_synced(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import check_drift, render_all

        render_all(tmp_path)
        drift = check_drift(tmp_path)

        assert drift == {}

    def test_detects_stale_page(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import _AUTOGEN_MARKER, check_drift, render_all

        render_all(tmp_path)
        # Corrupt the auto section of one rule
        rule_id = sorted(RULES_BY_ID.keys())[0]
        page = tmp_path / f"{rule_id}.md"
        # Write stale content — keep the marker but change the auto section
        stale_auto = f"# {rule_id}\n\nSTALE CONTENT\n\n{_AUTOGEN_MARKER}\n"
        page.write_text(stale_auto, encoding="utf-8")

        drift = check_drift(tmp_path)

        assert rule_id in drift

    def test_returns_diff_string(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import _AUTOGEN_MARKER, check_drift, render_all

        render_all(tmp_path)
        rule_id = sorted(RULES_BY_ID.keys())[0]
        page = tmp_path / f"{rule_id}.md"
        stale_auto = f"# {rule_id}\n\nSTALE\n\n{_AUTOGEN_MARKER}\n"
        page.write_text(stale_auto, encoding="utf-8")

        drift = check_drift(tmp_path)

        assert isinstance(drift[rule_id], str)
        assert len(drift[rule_id]) > 0

    def test_missing_page_is_reported_as_drift(self, tmp_path: Path) -> None:
        from hasscheck.docs_render import check_drift, render_all

        render_all(tmp_path)
        # Delete one page
        rule_id = sorted(RULES_BY_ID.keys())[0]
        (tmp_path / f"{rule_id}.md").unlink()

        drift = check_drift(tmp_path)

        assert rule_id in drift


# ---------------------------------------------------------------------------
# Metadata rendering — new sections from #147
# ---------------------------------------------------------------------------


class TestMetadataSectionsSkippedWhenDefault:
    """Scenario 7 — all new fields at defaults → no metadata section headers emitted."""

    def test_docs_render_skips_empty_metadata_sections(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule()  # all new fields at defaults
        output = render_page(rule)

        assert "## Tags" not in output
        assert "## Confidence" not in output
        assert "## Deprecated" not in output
        assert "## Replacement" not in output


class TestMetadataSectionsEmittedWhenPopulated:
    """Scenario 8 — non-default field values → metadata sections are rendered."""

    def test_docs_render_emits_populated_metadata_sections(self) -> None:
        from hasscheck.docs_render import render_page

        rule = _make_rule(
            tags=("ha-2026",),
            deprecated=True,
            replacement_rule="new.better.rule",
            confidence="low",
        )
        output = render_page(rule)

        assert "## Tags" in output
        assert "ha-2026" in output
        assert "## Confidence" in output
        assert "low" in output
        assert "## Deprecated" in output
        assert "## Replacement" in output
        assert "new.better.rule" in output


class TestDocsRenderCheckPassesAfterFieldAddition:
    """Scenario 9 — docs-render --check returns no drift after regeneration."""

    def test_docs_render_check_passes_after_field_addition(
        self, tmp_path: Path
    ) -> None:
        from hasscheck.docs_render import check_drift, render_all

        render_all(tmp_path)
        drift = check_drift(tmp_path)

        assert drift == {}, (
            f"Drift detected after render_all — renderer and docs are out of sync: "
            f"{list(drift.keys())}"
        )
