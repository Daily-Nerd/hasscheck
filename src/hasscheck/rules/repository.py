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

CATEGORY = "maintenance_signals"
LICENSE_SOURCE = "https://www.hacs.xyz/docs/publish/integration/"


def license_exists(context: ProjectContext) -> Finding:
    candidates = [
        context.root / "LICENSE",
        context.root / "LICENSE.md",
        context.root / "LICENSE.txt",
        context.root / "COPYING",
    ]
    existing = next((path for path in candidates if path.is_file()), None)
    exists = existing is not None
    return Finding(
        rule_id="repo.license.exists",
        rule_version="1.0.0",
        category=CATEGORY,
        status=RuleStatus.PASS if exists else RuleStatus.WARN,
        severity=RuleSeverity.RECOMMENDED,
        title="License exists",
        message=(
            f"Repository contains {existing.name}."
            if existing
            else "Repository does not contain a recognized license file."
        ),
        applicability=Applicability(
            reason="A license makes reuse and distribution terms explicit."
        ),
        source=RuleSource(url=LICENSE_SOURCE),
        fix=None
        if exists
        else FixSuggestion(summary="Add a repository license file such as LICENSE."),
        path=existing.name if existing else "LICENSE",
    )


RULES = [
    RuleDefinition(
        id="repo.license.exists",
        version="1.0.0",
        category=CATEGORY,
        severity=RuleSeverity.RECOMMENDED,
        title="License exists",
        why="A license clarifies how users and contributors may use and distribute the integration.",
        source_url=LICENSE_SOURCE,
        check=license_exists,
        overridable=True,
    )
]
