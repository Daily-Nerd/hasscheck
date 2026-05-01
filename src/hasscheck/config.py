"""hasscheck.yaml schema models, config loader, and override engine."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


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
