"""Baseline mode public surface.

Imports here are the stable contract for the rest of the codebase
(cli.py, output.py, tests). Subapp wiring is exposed under `cli`.
"""

from hasscheck.baseline.core import (
    BaselineEntry,
    BaselineError,
    BaselineFile,
    FindingPartition,
    baseline_from_findings,
    compute_finding_hash,
    drop_from_baseline,
    load_baseline,
    merge_baseline,
    partition_findings,
    write_baseline,
)

__all__ = [
    "BaselineEntry",
    "BaselineError",
    "BaselineFile",
    "FindingPartition",
    "baseline_from_findings",
    "compute_finding_hash",
    "drop_from_baseline",
    "load_baseline",
    "merge_baseline",
    "partition_findings",
    "write_baseline",
]
