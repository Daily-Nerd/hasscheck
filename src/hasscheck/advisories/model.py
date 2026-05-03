"""Advisory Pydantic model for HassCheck deprecation advisories."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Advisory(BaseModel):
    """Structured advisory for a HassCheck deprecation rule.

    extra="forbid" ensures YAML typos are caught at import time.
    frozen=True makes Advisory instances hashable and immutable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    introduced_in: str | None = None
    enforced_in: str | None = None
    source_url: str
    title: str
    summary: str
    affected_patterns: list[str]
    severity: Literal["info", "warn", "error"] = "warn"
    rule_ids: list[str]
