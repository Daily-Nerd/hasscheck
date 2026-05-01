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

CATEGORY = "tests_ci"
TESTS_SOURCE = "https://developers.home-assistant.io/docs/development_testing/"


def tests_folder_exists(context: ProjectContext) -> Finding:
    path = context.root / "tests"
    exists = path.is_dir()
    return Finding(
        rule_id="tests.folder.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="tests folder exists",
        message=(
            "Repository contains a tests directory."
            if exists
            else "Repository does not contain a tests directory; automated test coverage cannot be inspected."
        ),
        applicability=Applicability(
            reason="Tests help maintainers keep integration behavior stable as Home Assistant evolves."
        ),
        source=RuleSource(url=TESTS_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add a tests/ directory with pytest-based integration tests."
        ),
        path="tests",
    )


RULES = [
    RuleDefinition(
        id="tests.folder.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="tests folder exists",
        why="Tests provide maintainers a safety net for future Home Assistant and integration changes.",
        source_url=TESTS_SOURCE,
        check=tests_folder_exists,
        overridable=True,
    )
]
