"""Internal dataclasses for the smoke harness.

These are NOT Pydantic models. The serialised artifact is HassCheckReport.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hasscheck.models import HassCheckReport


@dataclass(frozen=True)
class ProbeTarget:
    """One importable module to probe, with its on-disk path for Finding.path."""

    module: str  # e.g. "custom_components.foo.config_flow"
    file_path: Path  # absolute path to the .py file


@dataclass(frozen=True)
class RunSmokeResult:
    """Lightweight orchestration container for one (ha_version, python_version) run.

    NOT a Pydantic model — the serialised artifact is the contained HassCheckReport.
    """

    ha_version: str
    python_version: str
    report: HassCheckReport
    venv_reused: bool  # True when the cached venv was reused without recreation
