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
GITHUB_ACTIONS_SOURCE = (
    "https://docs.github.com/actions/using-workflows/about-workflows"
)


def _workflow_files(context: ProjectContext):
    workflows_dir = context.root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    return sorted(
        path
        for path in workflows_dir.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def github_actions_exists(context: ProjectContext) -> Finding:
    workflows = _workflow_files(context)
    exists = bool(workflows)
    path = workflows[0] if exists else context.root / ".github" / "workflows"
    return Finding(
        rule_id="ci.github_actions.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="GitHub Actions workflow exists",
        message=(
            f"Repository contains GitHub Actions workflow {workflows[0].name}."
            if exists
            else "Repository does not contain a GitHub Actions workflow file."
        ),
        applicability=Applicability(
            reason="CI helps maintainers catch regressions before releases and pull request merges."
        ),
        source=RuleSource(url=GITHUB_ACTIONS_SOURCE),
        fix=None
        if exists
        else FixSuggestion(
            summary="Add a .github/workflows/*.yml workflow that runs HassCheck and tests."
        ),
        path=str(path.relative_to(context.root)) if exists else ".github/workflows",
    )


RULES = [
    RuleDefinition(
        id="ci.github_actions.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="GitHub Actions workflow exists",
        why="A CI workflow makes quality checks repeatable for pushes and pull requests.",
        source_url=GITHUB_ACTIONS_SOURCE,
        check=github_actions_exists,
        overridable=True,
    )
]
