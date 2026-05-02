from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hasscheck.config import ProjectApplicability

from hasscheck.models import Finding, RuleSeverity, RuleSource


@dataclass(frozen=True)
class ProjectContext:
    root: Path
    integration_path: Path | None
    domain: str | None
    applicability: ProjectApplicability | None = None
    rule_settings: dict[str, dict[str, Any]] = field(default_factory=dict)


def get_rule_setting(
    context: ProjectContext, rule_id: str, key: str, default: Any
) -> Any:
    """Read a per-rule setting value with default fallback.

    Returns the configured value for key within rule_id's settings, or
    default when the rule has no settings or the key is absent.
    """
    return context.rule_settings.get(rule_id, {}).get(key, default)


@dataclass(frozen=True)
class RuleDefinition:
    id: str
    version: str
    category: str
    severity: RuleSeverity
    title: str
    why: str
    source_url: str
    check: Callable[[ProjectContext], Finding]
    overridable: bool

    @property
    def source(self) -> RuleSource:
        return RuleSource(url=self.source_url)
