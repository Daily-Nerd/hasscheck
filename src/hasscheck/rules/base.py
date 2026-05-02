from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

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
    """A single hasscheck rule with its check function and metadata.

    Required fields (positional-safe, keyword-only in practice):
        id, version, category, severity, title, why, source_url, check, overridable

    Optional metadata fields (all have safe defaults; append AFTER overridable):
        tags             — tuple[str, ...]; MUST be a tuple, not list/set (frozen dataclass).
                           Raises TypeError in __post_init__ if a list or set is passed.
        profiles         — tuple[str, ...]; same constraint as tags. Semantics deferred to O6.
        min_ha_version   — minimum HA version string this rule applies to; None = all versions.
        max_ha_version   — maximum HA version string this rule applies to; None = all versions.
        introduced_by    — attribution string (e.g. author email); None = unknown/legacy.
        introduced_at_version — hasscheck version when this rule was added; None = legacy.
        advisory_id      — opaque advisory ID string; validation deferred to O4 / #155.
        related_quality_scale_rule — opaque QS rule ID; validation deferred to O15.
        confidence       — Literal["high", "medium", "low"]; validated eagerly in __post_init__.
                           Raises ValueError if an unknown value is passed.
                           Default "high" preserves semantics for all existing rules.
        false_positive_notes — prose describing known false-positive scenarios; None = none known.
        replacement_rule — ID of the rule that supersedes this one; cross-reference validated by
                           registry-level contract test, NOT at construction time (chicken-and-egg
                           with registration order).
        deprecated       — True when this rule is retired; renders a deprecation notice in docs.
        deprecated_in_version — hasscheck version when deprecated; only meaningful when deprecated=True.
                               Logical constraint (requires deprecated=True) is deferred.

    Deferred validations (NOT enforced in this PR):
        - deprecated_in_version implies deprecated=True
        - min_ha_version <= max_ha_version semver ordering
        - advisory_id format or existence (O4)
        - profiles string membership (O6)
        - related_quality_scale_rule existence (O15)
        - element types inside tags / profiles tuples
    """

    # --- required (existing — DO NOT REORDER) ---
    id: str
    version: str
    category: str
    severity: RuleSeverity
    title: str
    why: str
    source_url: str
    check: Callable[[ProjectContext], Finding]
    overridable: bool

    # --- optional metadata (new — appended AFTER overridable) ---
    tags: tuple[str, ...] = ()
    profiles: tuple[str, ...] = ()
    min_ha_version: str | None = None
    max_ha_version: str | None = None
    introduced_by: str | None = None
    introduced_at_version: str | None = None
    advisory_id: str | None = None
    related_quality_scale_rule: str | None = None
    confidence: Literal["high", "medium", "low"] = "high"
    false_positive_notes: str | None = None
    replacement_rule: str | None = None
    deprecated: bool = False
    deprecated_in_version: str | None = None

    def __post_init__(self) -> None:
        """Eager validation of collection types and confidence literal.

        Frozen dataclasses do not validate Literal types natively. We check
        explicitly here so that misconfigured rule definitions fail loudly at
        the construction site rather than silently at hash-time or later.
        """
        if not isinstance(self.tags, tuple):
            raise TypeError(
                f"RuleDefinition.tags must be a tuple, got {type(self.tags).__name__}. "
                f"Use tags=('x', 'y') not tags=['x', 'y'] (frozen dataclass requires hashable)."
            )
        if not isinstance(self.profiles, tuple):
            raise TypeError(
                f"RuleDefinition.profiles must be a tuple, got {type(self.profiles).__name__}. "
                f"Use profiles=('x',) not profiles=['x']."
            )
        if self.confidence not in ("high", "medium", "low"):
            raise ValueError(
                f"RuleDefinition.confidence must be 'high', 'medium', or 'low'; "
                f"got {self.confidence!r}."
            )

    @property
    def source(self) -> RuleSource:
        return RuleSource(url=self.source_url)
