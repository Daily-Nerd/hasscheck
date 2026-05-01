from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from hasscheck.models import Finding, RuleSource, RuleSeverity, RuleStatus


@dataclass(frozen=True)
class ProjectContext:
    root: Path
    integration_path: Path | None
    domain: str | None


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

    @property
    def source(self) -> RuleSource:
        return RuleSource(url=self.source_url)
