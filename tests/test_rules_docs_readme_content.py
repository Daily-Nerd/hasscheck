"""Tests for README content rules (issue #55).

Five rules:
  docs.installation.exists
  docs.configuration.exists
  docs.troubleshooting.exists
  docs.removal.exists
  docs.privacy.exists

All are RECOMMENDED + overridable=True.
- NOT_APPLICABLE when README.md is absent.
- PASS when a matching heading (or bold line) is found outside code fences.
- WARN when README exists but no matching section detected.
"""

from __future__ import annotations

import textwrap

import pytest

from hasscheck.models import RuleStatus
from hasscheck.rules.base import ProjectContext
from hasscheck.rules.docs_readme import (
    _extract_headings,
    docs_configuration_exists,
    docs_installation_exists,
    docs_privacy_exists,
    docs_removal_exists,
    docs_troubleshooting_exists,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(tmp_path, readme_content: str | None):
    """Build a minimal ProjectContext with an optional README."""
    if readme_content is not None:
        (tmp_path / "README.md").write_text(readme_content, encoding="utf-8")
    return ProjectContext(root=tmp_path, integration_path=None, domain=None)


# ---------------------------------------------------------------------------
# _extract_headings unit tests
# ---------------------------------------------------------------------------


def test_extract_headings_returns_heading_text():
    text = "# Installation\n\nSome text.\n\n## Configuration\n"
    headings = _extract_headings(text)
    assert "Installation" in headings
    assert "Configuration" in headings


def test_extract_headings_strips_code_fences():
    text = textwrap.dedent("""\
        # Installation

        ```
        # not a heading inside fence
        ## install something
        ```

        ## Real Heading
    """)
    headings = _extract_headings(text)
    assert "Real Heading" in headings
    assert "not a heading inside fence" not in headings
    assert "install something" not in headings


def test_extract_headings_includes_bold_lines():
    text = "**Installation**\n\nSome text.\n"
    headings = _extract_headings(text)
    assert "Installation" in headings


def test_extract_headings_includes_emphasis_lines():
    text = "_Configuration_\n\nSome text.\n"
    headings = _extract_headings(text)
    assert "Configuration" in headings


# ---------------------------------------------------------------------------
# Parametrized rule list for DRY tests
# ---------------------------------------------------------------------------

# (rule_fn, pass_heading, pass_keyword_in_heading, na_label)
RULE_CASES = [
    (docs_installation_exists, "## Installation", "installation", "installation"),
    (docs_configuration_exists, "## Configuration", "configuration", "configuration"),
    (
        docs_troubleshooting_exists,
        "## Troubleshooting",
        "troubleshooting",
        "troubleshooting",
    ),
    (docs_removal_exists, "## Removal", "removal", "removal"),
    (docs_privacy_exists, "## Privacy", "privacy", "privacy"),
]


@pytest.mark.parametrize("rule_fn,heading,_kw,_label", RULE_CASES)
def test_pass_with_standard_heading(rule_fn, heading, _kw, _label, tmp_path):
    """README with a matching markdown heading → PASS."""
    content = f"# My Integration\n\n{heading}\n\nSome content here.\n"
    ctx = _ctx(tmp_path, content)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.PASS, (
        f"{rule_fn.__name__}: expected PASS for heading '{heading}', got {finding.status}: {finding.message}"
    )


@pytest.mark.parametrize("rule_fn,heading,_kw,_label", RULE_CASES)
def test_pass_with_bold_section_header(rule_fn, heading, _kw, _label, tmp_path):
    """README with a bold line matching keyword → PASS."""
    # Derive a keyword from the heading: strip ## and use title case
    section = heading.lstrip("# ").strip()
    content = f"# My Integration\n\n**{section}**\n\nSome content here.\n"
    ctx = _ctx(tmp_path, content)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.PASS, (
        f"{rule_fn.__name__}: expected PASS for bold '**{section}**', got {finding.status}: {finding.message}"
    )


@pytest.mark.parametrize("rule_fn,_heading,_kw,_label", RULE_CASES)
def test_warn_on_minimal_readme(rule_fn, _heading, _kw, _label, tmp_path):
    """Minimal README with no matching section → WARN."""
    content = "# My Integration\n\nThis integration does something great.\n"
    ctx = _ctx(tmp_path, content)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.WARN, (
        f"{rule_fn.__name__}: expected WARN for minimal README, got {finding.status}"
    )


@pytest.mark.parametrize("rule_fn,_heading,kw,_label", RULE_CASES)
def test_warn_keyword_inside_code_fence(rule_fn, _heading, kw, _label, tmp_path):
    """Keyword only inside a code fence must NOT trigger PASS — expect WARN."""
    content = textwrap.dedent(f"""\
        # My Integration

        ```bash
        # {kw} step
        ```
    """)
    ctx = _ctx(tmp_path, content)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.WARN, (
        f"{rule_fn.__name__}: keyword '{kw}' inside code fence should NOT cause PASS, got {finding.status}"
    )


@pytest.mark.parametrize("rule_fn,_heading,_kw,_label", RULE_CASES)
def test_not_applicable_when_readme_missing(rule_fn, _heading, _kw, _label, tmp_path):
    """No README at all → NOT_APPLICABLE."""
    ctx = _ctx(tmp_path, None)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.NOT_APPLICABLE, (
        f"{rule_fn.__name__}: expected NOT_APPLICABLE when README absent, got {finding.status}"
    )


# ---------------------------------------------------------------------------
# Installation-specific: sub-heading keyword variants
# ---------------------------------------------------------------------------


def test_installation_passes_for_hacs_subheading(tmp_path):
    """### HACS is a recognized installation-related heading."""
    content = "# My Integration\n\n### HACS\n\nInstall via HACS.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_installation_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_installation_passes_for_manual_install_heading(tmp_path):
    """## Manual Install heading → PASS."""
    content = "# My Integration\n\n## Manual Install\n\nCopy files.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_installation_exists(ctx)
    assert finding.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# Privacy rule: broad keyword set
# ---------------------------------------------------------------------------


def test_privacy_passes_for_cloud_heading(tmp_path):
    """## Cloud heading satisfies privacy rule."""
    content = "# My Integration\n\n## Cloud\n\nData goes to the cloud.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_privacy_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_privacy_passes_for_data_heading(tmp_path):
    """## Data heading satisfies privacy rule."""
    content = "# My Integration\n\n## Data\n\nAll data is local.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_privacy_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_privacy_passes_for_local_heading(tmp_path):
    """## Local heading satisfies privacy rule."""
    content = "# My Integration\n\n## Local Processing\n\nNo cloud.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_privacy_exists(ctx)
    assert finding.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# Case-insensitivity checks
# ---------------------------------------------------------------------------


def test_installation_passes_case_insensitive(tmp_path):
    """INSTALLATION (all caps) heading → PASS."""
    content = "# My Integration\n\n## INSTALLATION\n\nStep 1.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_installation_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_configuration_passes_mixed_case(tmp_path):
    """## ConFiguration → PASS."""
    content = "# My Integration\n\n## ConFiguration\n\nSet things.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_configuration_exists(ctx)
    assert finding.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# Rule metadata checks
# ---------------------------------------------------------------------------

from hasscheck.models import RuleSeverity  # noqa: E402
from hasscheck.rules.docs_readme import RULES as DOCS_README_RULES  # noqa: E402


def test_all_five_rules_registered():
    rule_ids = {r.id for r in DOCS_README_RULES}
    expected = {
        "docs.installation.exists",
        "docs.configuration.exists",
        "docs.troubleshooting.exists",
        "docs.removal.exists",
        "docs.privacy.exists",
    }
    assert rule_ids == expected


def test_all_five_rules_are_recommended_and_overridable():
    for rule in DOCS_README_RULES:
        assert rule.severity is RuleSeverity.RECOMMENDED, (
            f"{rule.id} should be RECOMMENDED"
        )
        assert rule.overridable is True, f"{rule.id} should be overridable=True"
