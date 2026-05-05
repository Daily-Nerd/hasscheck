from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from hasscheck.checker import run_check_at
from hasscheck.models import HassCheckReport, RuleStatus


@dataclass(frozen=True)
class InventoryEntry:
    """One row in the inventory: either a successful report or an error."""

    domain: str  # always present; derived from directory name
    integration_path: Path  # absolute path to the integration dir
    report: HassCheckReport | None = None  # None iff error is set
    error: str | None = None  # None iff report is set

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class InventorySummary:
    total: int
    passed: int  # entries whose report has zero FAIL findings
    failed: int  # entries with >=1 FAIL finding OR error set
    warned: int  # entries with >=1 WARN and zero FAIL


@dataclass(frozen=True)
class InventoryResult:
    ha_config: Path
    entries: list[InventoryEntry] = field(default_factory=list)

    @property
    def summary(self) -> InventorySummary:
        total = len(self.entries)
        failed = sum(1 for e in self.entries if not e.ok or _has_fail(e.report))
        warned = sum(
            1
            for e in self.entries
            if e.ok and not _has_fail(e.report) and _has_warn(e.report)
        )
        passed = total - failed - warned
        return InventorySummary(
            total=total, passed=passed, failed=failed, warned=warned
        )

    @property
    def exit_code(self) -> int:
        return 1 if self.summary.failed > 0 else 0

    def to_json_dict(self) -> dict:
        return {
            "ha_config": str(self.ha_config),
            "integrations": [
                e.report.to_json_dict()
                if e.ok
                else {
                    "domain": e.domain,
                    "integration_path": str(e.integration_path),
                    "error": e.error,
                }
                for e in self.entries
            ],
        }


def _has_fail(report: HassCheckReport | None) -> bool:
    return report is not None and any(
        f.status is RuleStatus.FAIL for f in report.findings
    )


def _has_warn(report: HassCheckReport | None) -> bool:
    return report is not None and any(
        f.status is RuleStatus.WARN for f in report.findings
    )


def discover_integrations(ha_config: Path) -> list[Path]:
    """Return sorted list of integration directories under ha_config/custom_components/.

    Filters: must be a directory, must NOT start with '.', must contain
    a manifest.json file (file presence only — not parsed). Returned in
    deterministic alphabetical order so terminal/JSON output is stable.

    Returns [] if custom_components/ does not exist (caller decides whether
    that's an error or empty inventory).
    """
    cc = ha_config / "custom_components"
    if not cc.is_dir():
        return []
    return sorted(
        p
        for p in cc.iterdir()
        if p.is_dir() and not p.name.startswith(".") and (p / "manifest.json").is_file()
    )


def run_inventory(
    ha_config: Path,
    *,
    ha_version: str | None = None,
    no_config: bool = False,
) -> InventoryResult:
    """Discover integrations under ha_config and run the full ruleset on each.

    Errors during a single integration's check are captured as an
    InventoryEntry with `error` set and `report=None`; the scan continues.
    No exception escapes this function except for argument-validation
    errors raised before iteration starts.
    """
    ha_config = ha_config.resolve()
    integrations = discover_integrations(ha_config)
    entries: list[InventoryEntry] = []

    for integ_path in integrations:
        domain = integ_path.name  # HA convention: dir name == domain
        try:
            # Each integration is its own "root" for config discovery purposes.
            # We deliberately do NOT pass a hasscheck.yaml from ha_config — HA
            # config dirs are not the right place for hasscheck overrides.
            report = run_check_at(
                root=integ_path.parent.parent,  # the ha_config dir
                integration_path=integ_path,
                domain=domain,
                no_config=no_config,
                ha_version=ha_version,
            )
            entries.append(
                InventoryEntry(
                    domain=domain,
                    integration_path=integ_path,
                    report=report,
                )
            )
        except Exception as exc:  # noqa: BLE001 — explicit broad catch is the contract
            entries.append(
                InventoryEntry(
                    domain=domain,
                    integration_path=integ_path,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    return InventoryResult(ha_config=ha_config, entries=entries)
