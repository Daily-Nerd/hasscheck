from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hasscheck.config import ProjectApplicability

from hasscheck.models import Finding, RuleSeverity, RuleSource


@dataclass(frozen=True)
class ProjectContext:
    root: Path
    integration_path: Path | None
    domain: str | None
    applicability: ProjectApplicability | None = None


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
