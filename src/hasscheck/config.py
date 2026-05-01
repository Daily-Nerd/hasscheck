"""hasscheck.yaml schema models, config loader, and override engine."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConfigError(Exception):
    """Raised when hasscheck.yaml is malformed or contains an invalid override."""


class RuleOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["not_applicable", "manual_review"]
    reason: str = Field(min_length=1)


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["integration"] = "integration"


class HassCheckConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.2.0"] = "0.2.0"
    project: ProjectConfig | None = None
    rules: dict[str, RuleOverride] = Field(default_factory=dict)
