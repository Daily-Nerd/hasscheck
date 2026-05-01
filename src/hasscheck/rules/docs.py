from __future__ import annotations

from hasscheck.models import (
    Applicability,
    Finding,
    FixSuggestion,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.rules.base import ProjectContext, RuleDefinition

CATEGORY = "docs_support"
DOCS_SOURCE = "https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/docs-installation-instructions/"


def readme_exists(context: ProjectContext) -> Finding:
    candidates = [
        context.root / "README.md",
        context.root / "README.rst",
        context.root / "README.txt",
    ]
    existing = next((path for path in candidates if path.is_file()), None)
    exists = existing is not None
    return Finding(
        rule_id="docs.readme.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="README exists",
        message=(
            f"Repository contains {existing.name}."
            if existing
            else "Repository does not contain a README file, so setup/support documentation cannot be inspected."
        ),
        applicability=Applicability(
            reason="Custom integration repositories should explain installation, configuration, and support."
        ),
        source=RuleSource(url=DOCS_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add README.md with installation, configuration, and support notes."
        ),
        path=existing.name if existing else "README.md",
    )


RULES = [
    RuleDefinition(
        id="docs.readme.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="README exists",
        why="A README gives users installation, configuration, troubleshooting, and support context.",
        source_url=DOCS_SOURCE,
        check=readme_exists,
        overridable=True,
    )
]
