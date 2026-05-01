from __future__ import annotations

import json

from hasscheck.models import Applicability, Finding, FixSuggestion, RuleSeverity, RuleSource, RuleStatus
from hasscheck.rules.base import ProjectContext, RuleDefinition

HACS_SOURCE = "https://www.hacs.xyz/docs/publish/integration/"


def custom_components_exists(context: ProjectContext) -> Finding:
    path = context.root / "custom_components"
    exists = path.is_dir()
    return Finding(
        rule_id="hacs.custom_components.exists",
        rule_version="1.0.0",
        category="hacs_structure",
        status=RuleStatus.PASS if exists else RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title="custom_components directory exists",
        message=(
            "Repository contains a custom_components directory."
            if exists
            else "Repository does not contain custom_components/, so HassCheck cannot find a custom integration."
        ),
        applicability=Applicability(reason="HACS custom integration repositories need a custom_components directory."),
        source=RuleSource(url=HACS_SOURCE),
        fix=None
        if exists
        else FixSuggestion(summary="Create custom_components/<domain>/ and place the integration files there."),
        path="custom_components",
    )



def hacs_file_parseable(context: ProjectContext) -> Finding:
    path = context.root / "hacs.json"
    if not path.exists():
        return Finding(
            rule_id="hacs.file.parseable",
            rule_version="1.0.0",
            category="hacs_structure",
            status=RuleStatus.WARN,
            severity=RuleSeverity.RECOMMENDED,
            title="hacs.json exists and parses",
            message="hacs.json is missing. HACS metadata cannot be inspected yet.",
            applicability=Applicability(reason="HACS repositories use hacs.json for repository metadata."),
            source=RuleSource(url=HACS_SOURCE),
            fix=FixSuggestion(summary="Add a repository-level hacs.json file, even if it starts as an empty JSON object."),
            path="hacs.json",
        )

    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Finding(
            rule_id="hacs.file.parseable",
            rule_version="1.0.0",
            category="hacs_structure",
            status=RuleStatus.FAIL,
            severity=RuleSeverity.RECOMMENDED,
            title="hacs.json exists and parses",
            message=f"hacs.json is present but is not valid JSON: {exc.msg}.",
            applicability=Applicability(reason="hacs.json must parse before HassCheck can inspect HACS metadata."),
            source=RuleSource(url=HACS_SOURCE),
            fix=FixSuggestion(summary="Fix hacs.json syntax, then rerun HassCheck."),
            path="hacs.json",
        )

    return Finding(
        rule_id="hacs.file.parseable",
        rule_version="1.0.0",
        category="hacs_structure",
        status=RuleStatus.PASS,
        severity=RuleSeverity.RECOMMENDED,
        title="hacs.json exists and parses",
        message="hacs.json is present and valid JSON.",
        applicability=Applicability(reason="HACS repositories use hacs.json for repository metadata."),
        source=RuleSource(url=HACS_SOURCE),
        fix=None,
        path="hacs.json",
    )


RULES = [
    RuleDefinition(
        id="hacs.custom_components.exists",
        version="1.0.0",
        category="hacs_structure",
        severity=RuleSeverity.REQUIRED,
        title="custom_components directory exists",
        why="HACS integration repositories are structured around custom_components/<domain>/.",
        source_url=HACS_SOURCE,
        check=custom_components_exists,
        overridable=False,
    ),
    RuleDefinition(
        id="hacs.file.parseable",
        version="1.0.0",
        category="hacs_structure",
        severity=RuleSeverity.RECOMMENDED,
        title="hacs.json exists and parses",
        why="hacs.json stores HACS repository metadata and must be valid JSON before it can be inspected.",
        source_url=HACS_SOURCE,
        check=hacs_file_parseable,
        overridable=False,
    ),
]
