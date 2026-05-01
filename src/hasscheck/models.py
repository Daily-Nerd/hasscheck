from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hasscheck import __version__

SCHEMA_VERSION = "0.3.0"
# See docs/decisions/0006-ruleset-versioning.md for bump policy.
DEFAULT_RULESET_ID = "hasscheck-ha-2026.4"
DEFAULT_SOURCE_CHECKED_AT = "2026-05-01"


class RuleStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    MANUAL_REVIEW = "manual_review"


class ApplicabilityStatus(StrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    MANUAL_REVIEW = "manual_review"


class RuleSeverity(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    INFORMATIONAL = "informational"


ApplicabilitySource = Literal["default", "detected", "config"]


class RuleSource(BaseModel):
    url: str
    checked_at: str = DEFAULT_SOURCE_CHECKED_AT


class Applicability(BaseModel):
    status: ApplicabilityStatus = ApplicabilityStatus.APPLICABLE
    reason: str
    source: ApplicabilitySource = "default"


class FixSuggestion(BaseModel):
    summary: str
    command: str | None = None
    docs_url: str | None = None


class Finding(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    rule_id: str
    rule_version: str
    ruleset: str = DEFAULT_RULESET_ID
    category: str
    status: RuleStatus
    severity: RuleSeverity
    title: str
    message: str
    applicability: Applicability
    source: RuleSource
    fix: FixSuggestion | None = None
    path: str | None = None


class CategorySignal(BaseModel):
    id: str
    label: str
    points_awarded: int
    points_possible: int


class OverridesApplied(BaseModel):
    count: int = 0
    rule_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _invariant(self) -> OverridesApplied:
        if self.count != len(self.rule_ids):
            raise ValueError(
                f"overrides_applied invariant violated: count={self.count} but "
                f"rule_ids has {len(self.rule_ids)} entries"
            )
        if self.rule_ids != sorted(self.rule_ids):
            raise ValueError("overrides_applied.rule_ids must be alphabetically sorted")
        return self


class ApplicabilityApplied(BaseModel):
    count: int = 0
    rule_ids: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _invariant(self) -> ApplicabilityApplied:
        if self.count != len(self.rule_ids):
            raise ValueError(
                f"applicability_applied invariant violated: count={self.count} but "
                f"rule_ids has {len(self.rule_ids)} entries"
            )
        if self.rule_ids != sorted(self.rule_ids):
            raise ValueError(
                "applicability_applied.rule_ids must be alphabetically sorted"
            )
        if self.flags != sorted(self.flags):
            raise ValueError(
                "applicability_applied.flags must be alphabetically sorted"
            )
        return self


class ReportSummary(BaseModel):
    overall: Literal["informational_only"] = "informational_only"
    security_review: Literal["not_performed"] = "not_performed"
    official_ha_tier: Literal["not_assigned"] = "not_assigned"
    hacs_acceptance: Literal["not_guaranteed"] = "not_guaranteed"
    categories: list[CategorySignal] = Field(default_factory=list)
    overrides_applied: OverridesApplied = Field(default_factory=OverridesApplied)
    applicability_applied: ApplicabilityApplied = Field(
        default_factory=ApplicabilityApplied
    )


class ProjectInfo(BaseModel):
    path: str
    type: Literal["integration", "unknown"] = "unknown"
    domain: str | None = None
    integration_path: str | None = None
    repo_slug: str | None = None


class ToolInfo(BaseModel):
    name: Literal["hasscheck"] = "hasscheck"
    version: str = __version__


class RulesetInfo(BaseModel):
    id: str = DEFAULT_RULESET_ID
    source_checked_at: str = DEFAULT_SOURCE_CHECKED_AT


class HassCheckReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    tool: ToolInfo = Field(default_factory=ToolInfo)
    project: ProjectInfo
    ruleset: RulesetInfo = Field(default_factory=RulesetInfo)
    summary: ReportSummary
    findings: list[Finding]

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
