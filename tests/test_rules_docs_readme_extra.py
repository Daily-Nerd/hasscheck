"""Tests for four additional README content rules (issue #102).

Four rules:
  docs.examples.exists
  docs.supported_devices.exists
  docs.limitations.exists
  docs.hacs_instructions.exists

All are RECOMMENDED + overridable=True.
- NOT_APPLICABLE when README.md is absent.
- PASS when a matching heading (or bold line) is found outside code fences.
- WARN when README exists but no matching section detected.
"""

from __future__ import annotations

import textwrap

import pytest

from hasscheck.models import RuleSeverity, RuleStatus
from hasscheck.rules.base import ProjectContext
from hasscheck.rules.docs_readme import (
    docs_examples_exists,
    docs_hacs_instructions_exists,
    docs_limitations_exists,
    docs_supported_devices_exists,
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
# Parametrized rule list for DRY tests
# ---------------------------------------------------------------------------

# (rule_fn, pass_heading, representative_keyword)
RULE_CASES = [
    (docs_examples_exists, "## Examples", "examples"),
    (docs_supported_devices_exists, "## Supported Devices", "devices"),
    (docs_limitations_exists, "## Limitations", "limitations"),
    (docs_hacs_instructions_exists, "## HACS Installation", "hacs"),
]


@pytest.mark.parametrize("rule_fn,heading,_kw", RULE_CASES)
def test_pass_with_standard_heading(rule_fn, heading, _kw, tmp_path):
    """README with a matching markdown heading → PASS."""
    content = f"# My Integration\n\n{heading}\n\nSome content here.\n"
    ctx = _ctx(tmp_path, content)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.PASS, (
        f"{rule_fn.__name__}: expected PASS for heading '{heading}', "
        f"got {finding.status}: {finding.message}"
    )


@pytest.mark.parametrize("rule_fn,heading,_kw", RULE_CASES)
def test_pass_with_bold_section_header(rule_fn, heading, _kw, tmp_path):
    """README with a bold line matching keyword → PASS."""
    section = heading.lstrip("# ").strip()
    content = f"# My Integration\n\n**{section}**\n\nSome content here.\n"
    ctx = _ctx(tmp_path, content)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.PASS, (
        f"{rule_fn.__name__}: expected PASS for bold '**{section}**', "
        f"got {finding.status}: {finding.message}"
    )


@pytest.mark.parametrize("rule_fn,_heading,_kw", RULE_CASES)
def test_warn_on_minimal_readme(rule_fn, _heading, _kw, tmp_path):
    """Minimal README with no matching section → WARN."""
    content = "# My Integration\n\nThis integration does something great.\n"
    ctx = _ctx(tmp_path, content)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.WARN, (
        f"{rule_fn.__name__}: expected WARN for minimal README, got {finding.status}"
    )


@pytest.mark.parametrize("rule_fn,_heading,kw", RULE_CASES)
def test_warn_keyword_inside_code_fence(rule_fn, _heading, kw, tmp_path):
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
        f"{rule_fn.__name__}: keyword '{kw}' inside code fence should NOT cause PASS, "
        f"got {finding.status}"
    )


@pytest.mark.parametrize("rule_fn,_heading,_kw", RULE_CASES)
def test_not_applicable_when_readme_missing(rule_fn, _heading, _kw, tmp_path):
    """No README at all → NOT_APPLICABLE."""
    ctx = _ctx(tmp_path, None)
    finding = rule_fn(ctx)
    assert finding.status is RuleStatus.NOT_APPLICABLE, (
        f"{rule_fn.__name__}: expected NOT_APPLICABLE when README absent, "
        f"got {finding.status}"
    )


# ---------------------------------------------------------------------------
# docs.examples.exists — keyword variants
# ---------------------------------------------------------------------------


def test_examples_passes_for_usage_heading(tmp_path):
    """## Usage heading satisfies examples rule."""
    content = "# My Integration\n\n## Usage\n\nHere is how to use it.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_examples_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_examples_passes_for_demo_heading(tmp_path):
    """## Demo heading satisfies examples rule."""
    content = "# My Integration\n\n## Demo\n\nWatch the demo.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_examples_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_examples_passes_for_example_singular(tmp_path):
    """## Example (singular) heading satisfies examples rule."""
    content = "# My Integration\n\n## Example\n\nAn example.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_examples_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_examples_passes_case_insensitive(tmp_path):
    """## EXAMPLES (all-caps) heading → PASS."""
    content = "# My Integration\n\n## EXAMPLES\n\nSome examples.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_examples_exists(ctx)
    assert finding.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# docs.supported_devices.exists — keyword variants
# ---------------------------------------------------------------------------


def test_supported_devices_passes_for_hardware_heading(tmp_path):
    """## Hardware heading satisfies supported_devices rule."""
    content = "# My Integration\n\n## Hardware\n\nSupported hardware list.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_supported_devices_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_supported_devices_passes_for_compatibility_heading(tmp_path):
    """## Compatibility heading satisfies supported_devices rule."""
    content = "# My Integration\n\n## Compatibility\n\nCompatible with:\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_supported_devices_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_supported_devices_passes_for_models_heading(tmp_path):
    """## Supported Models heading satisfies supported_devices rule."""
    content = "# My Integration\n\n## Supported Models\n\nModel A, Model B.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_supported_devices_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_supported_devices_passes_for_services_heading(tmp_path):
    """## Supported Services heading satisfies supported_devices rule."""
    content = "# My Integration\n\n## Supported Services\n\nService A.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_supported_devices_exists(ctx)
    assert finding.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# docs.limitations.exists — keyword variants
# ---------------------------------------------------------------------------


def test_limitations_passes_for_caveats_heading(tmp_path):
    """## Caveats heading satisfies limitations rule."""
    content = "# My Integration\n\n## Caveats\n\nSome caveats.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_limitations_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_limitations_passes_for_known_limitations_heading(tmp_path):
    """## Known Limitations heading satisfies limitations rule."""
    content = "# My Integration\n\n## Known Limitations\n\nKnown issue 1.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_limitations_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_limitations_passes_for_restrictions_heading(tmp_path):
    """## Restrictions heading satisfies limitations rule."""
    content = "# My Integration\n\n## Restrictions\n\nSome restrictions apply.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_limitations_exists(ctx)
    assert finding.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# docs.hacs_instructions.exists — keyword variants
# ---------------------------------------------------------------------------


def test_hacs_instructions_passes_for_hacs_subheading(tmp_path):
    """### HACS install sub-heading satisfies hacs_instructions rule."""
    content = (
        "# My Integration\n\n## Installation\n\n### HACS install\n\nAdd via HACS.\n"
    )
    ctx = _ctx(tmp_path, content)
    finding = docs_hacs_instructions_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_hacs_instructions_passes_for_custom_repository_heading(tmp_path):
    """## Custom Repository heading satisfies hacs_instructions rule."""
    content = "# My Integration\n\n## Custom Repository\n\nAdd as custom repo.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_hacs_instructions_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_hacs_instructions_passes_for_hacs_heading_alone(tmp_path):
    """## HACS heading (standalone) satisfies hacs_instructions rule."""
    content = "# My Integration\n\n## HACS\n\nInstall via HACS.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_hacs_instructions_exists(ctx)
    assert finding.status is RuleStatus.PASS


def test_hacs_instructions_passes_case_insensitive(tmp_path):
    """## hacs installation (lowercase) → PASS."""
    content = "# My Integration\n\n## hacs installation\n\nInstall via HACS.\n"
    ctx = _ctx(tmp_path, content)
    finding = docs_hacs_instructions_exists(ctx)
    assert finding.status is RuleStatus.PASS


# ---------------------------------------------------------------------------
# Rule metadata checks
# ---------------------------------------------------------------------------

from hasscheck.rules.docs_readme import RULES as DOCS_README_RULES  # noqa: E402


def test_nine_rules_registered():
    """All 9 README content rules (5 original + 4 new) are registered."""
    rule_ids = {r.id for r in DOCS_README_RULES}
    expected = {
        "docs.installation.exists",
        "docs.configuration.exists",
        "docs.troubleshooting.exists",
        "docs.removal.exists",
        "docs.privacy.exists",
        "docs.examples.exists",
        "docs.supported_devices.exists",
        "docs.limitations.exists",
        "docs.hacs_instructions.exists",
    }
    assert rule_ids == expected


def test_four_new_rules_are_recommended_and_overridable():
    """New rules are RECOMMENDED severity and overridable=True."""
    new_ids = {
        "docs.examples.exists",
        "docs.supported_devices.exists",
        "docs.limitations.exists",
        "docs.hacs_instructions.exists",
    }
    rules_by_id = {r.id: r for r in DOCS_README_RULES}
    for rule_id in new_ids:
        rule = rules_by_id[rule_id]
        assert rule.severity is RuleSeverity.RECOMMENDED, (
            f"{rule_id} should be RECOMMENDED"
        )
        assert rule.overridable is True, f"{rule_id} should be overridable=True"
