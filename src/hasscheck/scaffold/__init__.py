"""hasscheck.scaffold — scaffold infrastructure public API."""

from __future__ import annotations

from hasscheck.scaffold.cli import scaffold_app
from hasscheck.scaffold.engine import (
    check_applicability_gate,
    load_template,
    render,
    write_or_refuse,
)

__all__ = [
    "scaffold_app",
    "load_template",
    "render",
    "write_or_refuse",
    "check_applicability_gate",
]
