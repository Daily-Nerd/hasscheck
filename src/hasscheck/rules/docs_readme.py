"""README content rules — issue #55.

Five RECOMMENDED + overridable checks that look for documentation sections
in README.md using conservative heuristic heading detection:

  docs.installation.exists
  docs.configuration.exists
  docs.troubleshooting.exists
  docs.removal.exists
  docs.privacy.exists

Detection strategy (conservative, heading-only):
1. Strip code-fence blocks (lines between ``` markers).
2. Match markdown headings  ^#{1,6}\\s+(.*)$
3. Match bold/emphasis solo lines  ^\\*\\*(.*?)\\*\\*$  or  ^_(.*?)_$
4. PASS if any heading text contains any rule keyword as a whole word (\\b).
5. Otherwise WARN if README exists, NOT_APPLICABLE if README is absent.

Source: https://developers.home-assistant.io/docs/documenting_integrations
Source-checked-at: 2026-05-01
"""

from __future__ import annotations

import re
from collections.abc import Callable

from hasscheck.models import (
    Applicability,
    ApplicabilityStatus,
    Finding,
    FixSuggestion,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.rules.base import ProjectContext, RuleDefinition

CATEGORY = "docs_support"

# ---------------------------------------------------------------------------
# Source constants
# Source: https://developers.home-assistant.io/docs/documenting_integrations
# Verified: 2026-05-01
# ---------------------------------------------------------------------------

_DOCS_SOURCE_URL = "https://developers.home-assistant.io/docs/documenting_integrations"
_SOURCE_CHECKED_AT = "2026-05-01"

# ---------------------------------------------------------------------------
# Heading extraction helper
# ---------------------------------------------------------------------------

_FENCE_OPEN = re.compile(r"^```")
_MD_HEADING = re.compile(r"^#{1,6}\s+(.*)")
_BOLD_LINE = re.compile(r"^\*\*(.*?)\*\*\s*$")
_EMPHASIS_LINE = re.compile(r"^_(.*?)_\s*$")


def _extract_headings(readme_text: str) -> list[str]:
    """Return a list of heading texts found outside code fences.

    Recognises:
    - Markdown ATX headings: ``# Title``, ``## Title``, …
    - Bold solo lines: ``**Title**``
    - Emphasis solo lines: ``_Title_``

    Lines inside ``` fences are skipped entirely.
    """
    headings: list[str] = []
    inside_fence = False

    for line in readme_text.splitlines():
        stripped = line.strip()

        # Toggle fence state
        if _FENCE_OPEN.match(stripped):
            inside_fence = not inside_fence
            continue

        if inside_fence:
            continue

        m = _MD_HEADING.match(stripped)
        if m:
            headings.append(m.group(1).strip())
            continue

        m = _BOLD_LINE.match(stripped)
        if m:
            headings.append(m.group(1).strip())
            continue

        m = _EMPHASIS_LINE.match(stripped)
        if m:
            headings.append(m.group(1).strip())
            continue

    return headings


def _heading_matches_any_keyword(heading: str, keywords: frozenset[str]) -> bool:
    """Return True if heading contains any keyword as a whole word (case-insensitive)."""
    lower = heading.lower()
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", lower):
            return True
    return False


def _readme_path(context: ProjectContext):
    for name in ("README.md", "README.rst", "README.txt"):
        p = context.root / name
        if p.is_file():
            return p
    return None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _required_readme_section_rule(
    *,
    rule_id: str,
    title: str,
    why: str,
    keywords: frozenset[str],
    fix_summary: str,
) -> Callable[[ProjectContext], Finding]:
    """Return a check function for a README section rule.

    Semantics:
    - NOT_APPLICABLE: README is absent (docs.readme.exists handles that)
    - PASS: a heading outside code fences matches any keyword
    - WARN: README exists but no matching heading found
    """

    def check(context: ProjectContext) -> Finding:
        readme = _readme_path(context)

        if readme is None:
            return Finding(
                rule_id=rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.NOT_APPLICABLE,
                severity=RuleSeverity.RECOMMENDED,
                title=title,
                message=(
                    "README is missing; content inspection is skipped. "
                    "Add README.md first (see docs.readme.exists)."
                ),
                applicability=Applicability(
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason="README must exist before section content can be inspected.",
                ),
                source=RuleSource(url=_DOCS_SOURCE_URL),
                fix=FixSuggestion(summary=fix_summary),
                path="README.md",
            )

        text = readme.read_text(encoding="utf-8")
        headings = _extract_headings(text)
        found = any(_heading_matches_any_keyword(h, keywords) for h in headings)

        if found:
            return Finding(
                rule_id=rule_id,
                rule_version="1.0.0",
                category=CATEGORY,
                status=RuleStatus.PASS,
                severity=RuleSeverity.RECOMMENDED,
                title=title,
                message=f"README contains a recognisable {title.lower()} section.",
                applicability=Applicability(
                    reason="Documenting this topic helps users install and maintain the integration.",
                ),
                source=RuleSource(url=_DOCS_SOURCE_URL),
                fix=None,
                path=readme.name,
            )

        return Finding(
            rule_id=rule_id,
            rule_version="1.0.0",
            category=CATEGORY,
            status=RuleStatus.WARN,
            severity=RuleSeverity.RECOMMENDED,
            title=title,
            message=(
                f"README does not appear to contain a {title.lower()} section "
                f"(no heading matching: {', '.join(sorted(keywords))})."
            ),
            applicability=Applicability(
                reason="Documenting this topic helps users install and maintain the integration.",
            ),
            source=RuleSource(url=_DOCS_SOURCE_URL),
            fix=FixSuggestion(summary=fix_summary),
            path=readme.name,
        )

    check.__name__ = rule_id.replace(".", "_")
    return check


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

_INSTALLATION_KEYWORDS: frozenset[str] = frozenset(
    {"installation", "install", "hacs", "manual installation", "manual install"}
)
_CONFIGURATION_KEYWORDS: frozenset[str] = frozenset(
    {"configuration", "configure", "setup", "options"}
)
_TROUBLESHOOTING_KEYWORDS: frozenset[str] = frozenset(
    {
        "troubleshooting",
        "troubleshoot",
        "known issues",
        "known limitations",
        "faq",
        "support",
        "debug",
    }
)
_REMOVAL_KEYWORDS: frozenset[str] = frozenset(
    {"removal", "remove", "uninstall", "uninstalling"}
)
_PRIVACY_KEYWORDS: frozenset[str] = frozenset(
    {"privacy", "data", "telemetry", "cloud", "local"}
)


docs_installation_exists = _required_readme_section_rule(
    rule_id="docs.installation.exists",
    title="README installation section",
    why=(
        "A README installation section guides users through HACS or manual setup. "
        f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
    ),
    keywords=_INSTALLATION_KEYWORDS,
    fix_summary=(
        "Add an Installation section to README.md covering HACS and/or manual installation steps."
    ),
)

docs_configuration_exists = _required_readme_section_rule(
    rule_id="docs.configuration.exists",
    title="README configuration section",
    why=(
        "A README configuration section explains how to set up and configure the integration. "
        f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
    ),
    keywords=_CONFIGURATION_KEYWORDS,
    fix_summary=(
        "Add a Configuration section to README.md describing available options and setup steps."
    ),
)

docs_troubleshooting_exists = _required_readme_section_rule(
    rule_id="docs.troubleshooting.exists",
    title="README troubleshooting section",
    why=(
        "A README troubleshooting section reduces support burden by documenting known issues and solutions. "
        f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
    ),
    keywords=_TROUBLESHOOTING_KEYWORDS,
    fix_summary=(
        "Add a Troubleshooting or FAQ section to README.md with known issues and debug steps."
    ),
)

docs_removal_exists = _required_readme_section_rule(
    rule_id="docs.removal.exists",
    title="README removal section",
    why=(
        "A README removal section explains how to cleanly uninstall the integration without leaving stale data. "
        f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
    ),
    keywords=_REMOVAL_KEYWORDS,
    fix_summary=(
        "Add a Removal or Uninstall section to README.md with steps to cleanly remove the integration."
    ),
)

docs_privacy_exists = _required_readme_section_rule(
    rule_id="docs.privacy.exists",
    title="README privacy section",
    why=(
        "A README privacy section shows users the maintainer considered data handling "
        "(cloud vs. local, telemetry, privacy). "
        f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
    ),
    keywords=_PRIVACY_KEYWORDS,
    fix_summary=(
        "Add a Privacy or Data section to README.md describing what data the integration collects or sends."
    ),
)


RULES = [
    RuleDefinition(
        id="docs.installation.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="README installation section",
        why=(
            "A README installation section guides users through HACS or manual setup. "
            f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
        ),
        source_url=_DOCS_SOURCE_URL,
        check=docs_installation_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="docs.configuration.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="README configuration section",
        why=(
            "A README configuration section explains how to set up and configure the integration. "
            f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
        ),
        source_url=_DOCS_SOURCE_URL,
        check=docs_configuration_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="docs.troubleshooting.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="README troubleshooting section",
        why=(
            "A README troubleshooting section reduces support burden by documenting known issues. "
            f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
        ),
        source_url=_DOCS_SOURCE_URL,
        check=docs_troubleshooting_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="docs.removal.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="README removal section",
        why=(
            "A README removal section explains how to cleanly uninstall the integration. "
            f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
        ),
        source_url=_DOCS_SOURCE_URL,
        check=docs_removal_exists,
        overridable=True,
    ),
    RuleDefinition(
        id="docs.privacy.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="README privacy section",
        why=(
            "A README privacy section shows users the maintainer considered data handling. "
            f"Source: {_DOCS_SOURCE_URL} (verified {_SOURCE_CHECKED_AT})."
        ),
        source_url=_DOCS_SOURCE_URL,
        check=docs_privacy_exists,
        overridable=True,
    ),
]
