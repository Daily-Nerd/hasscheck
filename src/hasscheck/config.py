"""hasscheck.yaml schema models, config loader, and override engine."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TextIO

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

if TYPE_CHECKING:
    from hasscheck.models import Finding, OverridesApplied
    from hasscheck.rules.base import RuleDefinition


class ConfigError(Exception):
    """Raised when hasscheck.yaml is malformed or contains an invalid override."""


class RuleOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["not_applicable", "manual_review"]
    reason: str = Field(min_length=1)
    settings: dict[str, Any] | None = None  # per-rule config; contents are open dict


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["integration"] = "integration"


class ProjectApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supports_diagnostics: bool | None = None
    has_user_fixable_repairs: bool | None = None
    uses_config_flow: bool | None = None


class PublishConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: str | None = None


class HassCheckConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.2.0", "0.3.0", "0.4.0"] = "0.4.0"
    project: ProjectConfig | None = None
    applicability: ProjectApplicability | None = None
    rules: dict[str, RuleOverride] = Field(default_factory=dict)
    publish: PublishConfig | None = None

    @model_validator(mode="after")
    def _schema_version_matches_fields(self) -> HassCheckConfig:
        if self.schema_version == "0.2.0" and self.applicability is not None:
            raise ValueError(
                "schema_version 0.2.0 does not support applicability; use 0.3.0"
            )
        return self


def load_config_file(path: Path) -> HassCheckConfig:
    """Parse a hasscheck.yaml file into a validated HassCheckConfig.

    Raises ConfigError on YAML parse errors, non-mapping top-level, or
    Pydantic validation failures.
    """
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error in {path.name}: {exc}") from exc

    if raw is None:
        raw = {}

    if not isinstance(raw, dict):
        raise ConfigError(
            f"{path.name} must contain a YAML mapping at the top level, got {type(raw).__name__}"
        )

    try:
        return HassCheckConfig(**raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid {path.name}: {exc}") from exc


def discover_config(repo_root: Path) -> HassCheckConfig | None:
    """Look for hasscheck.yaml at repo_root exactly (no parent walk).

    Returns a parsed HassCheckConfig if found, None if absent.
    Propagates ConfigError if the file exists but is malformed.
    """
    candidate = repo_root / "hasscheck.yaml"
    if not candidate.is_file():
        return None
    return load_config_file(candidate)


def apply_overrides(
    findings: list[Finding],
    config: HassCheckConfig,
    rules_by_id: dict[str, RuleDefinition] | None = None,
    *,
    stderr: TextIO | None = None,
) -> tuple[list[Finding], OverridesApplied]:
    """Apply per-rule overrides from config to a findings list.

    Returns (new_findings, overrides_applied). Emits warnings to stderr for
    stale or redundant overrides. Raises ConfigError for locked-rule overrides.
    """
    from hasscheck.models import (
        Applicability,
        ApplicabilityStatus,
        OverridesApplied,
        RuleStatus,
    )
    from hasscheck.rules.registry import RULES_BY_ID

    if stderr is None:
        stderr = sys.stderr
    if rules_by_id is None:
        rules_by_id = RULES_BY_ID

    applied: list[str] = []
    finding_by_id = {f.rule_id: f for f in findings}
    new_findings = list(findings)

    for rule_id, override in config.rules.items():
        # Step 1: unknown rule_id → warn-and-skip
        rule = rules_by_id.get(rule_id)
        if rule is None:
            print(
                f"hasscheck: warning: unknown rule_id '{rule_id}' in hasscheck.yaml — "
                f"skipping. (Run `hasscheck check --json` to see emitted rule IDs.)",
                file=stderr,
            )
            continue

        # Step 2: locked rule → hard fail (takes precedence over all other checks)
        if not rule.overridable:
            raise ConfigError(
                f"Rule '{rule_id}' is not overridable. "
                f"Locked rules cannot be softened via hasscheck.yaml. "
                f"Remove this entry or open an issue if you believe it should be softenable."
            )

        finding = finding_by_id.get(rule_id)
        if finding is None:
            continue

        natural_status = finding.status

        # Step 3: natural PASS → stale warning, skip (not counted)
        if natural_status is RuleStatus.PASS:
            print(
                f"hasscheck: warning: rule '{rule_id}' is currently PASS; "
                f"override in hasscheck.yaml is stale and was ignored.",
                file=stderr,
            )
            continue

        # Step 4: natural NOT_APPLICABLE → silent no-op
        if natural_status is RuleStatus.NOT_APPLICABLE:
            continue

        # Step 5: natural MANUAL_REVIEW + override=manual_review → redundant, warn-skip
        if (
            natural_status is RuleStatus.MANUAL_REVIEW
            and override.status == "manual_review"
        ):
            print(
                f"hasscheck: warning: rule '{rule_id}' is already MANUAL_REVIEW; "
                f"override in hasscheck.yaml is redundant.",
                file=stderr,
            )
            continue

        # Step 6: apply override
        if override.status == "not_applicable":
            new_status = RuleStatus.NOT_APPLICABLE
            new_app_status = ApplicabilityStatus.NOT_APPLICABLE
        else:
            new_status = RuleStatus.MANUAL_REVIEW
            new_app_status = ApplicabilityStatus.MANUAL_REVIEW

        idx = new_findings.index(finding)
        new_findings[idx] = finding.model_copy(
            update={
                "status": new_status,
                "applicability": Applicability(
                    status=new_app_status,
                    reason=override.reason,
                    source="config",
                ),
            }
        )
        applied.append(rule_id)

    overrides_applied = OverridesApplied(
        count=len(applied),
        rule_ids=sorted(applied),
    )
    return new_findings, overrides_applied
