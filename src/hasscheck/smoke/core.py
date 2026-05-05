"""Smoke harness orchestration: venv creation, package install, import probing."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from hasscheck.models import (
    DEFAULT_SOURCE_CHECKED_AT,
    Applicability,
    ApplicabilityStatus,
    CategorySignal,
    Finding,
    HassCheckReport,
    ProjectInfo,
    ReportSummary,
    ReportTarget,
    RuleSeverity,
    RuleSource,
    RuleStatus,
)
from hasscheck.provenance import detect_provenance
from hasscheck.slug import detect_repo_slug
from hasscheck.smoke import runner as _runner
from hasscheck.smoke.cache import get_venv_path, is_venv_ready
from hasscheck.smoke.errors import SmokeError, SmokeTimeoutError
from hasscheck.smoke.models import ProbeTarget, RunSmokeResult
from hasscheck.target import build_validity, detect_target

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SMOKE_RULE_VERSION = "0.1.0"

_SMOKE_SOURCE = RuleSource(
    url="https://github.com/Daily-Nerd/hasscheck/blob/main/docs/decisions/0017-import-smoke-harness.md",
    checked_at=DEFAULT_SOURCE_CHECKED_AT,
)

_SMOKE_APPLICABILITY = Applicability(
    status=ApplicabilityStatus.APPLICABLE,
    reason="import-smoke harness probed this module against the requested HA version",
    source="default",
)

# RunFn type alias — allows test-injection without touching subprocess boundary
RunFn = Callable[..., tuple[int, str, str]]

# ---------------------------------------------------------------------------
# Finding construction helpers
# ---------------------------------------------------------------------------


def _make_finding_pass(t: ProbeTarget, ha_version: str) -> Finding:
    return Finding(
        rule_id="smoke.import.pass",
        rule_version=SMOKE_RULE_VERSION,
        category="compatibility",
        status=RuleStatus.PASS,
        severity=RuleSeverity.INFORMATIONAL,
        title=f"Imported {t.module}",
        message=f"Module imported cleanly against homeassistant=={ha_version}.",
        applicability=_SMOKE_APPLICABILITY,
        source=_SMOKE_SOURCE,
        path=str(t.file_path),
    )


def _make_finding_fail(t: ProbeTarget, ha_version: str, stderr: str) -> Finding:
    last_line = stderr.strip().splitlines()[-1] if stderr.strip() else "(no stderr)"
    if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
        rule_id = "smoke.import.fail"
    else:
        rule_id = "smoke.import.error"
    return Finding(
        rule_id=rule_id,
        rule_version=SMOKE_RULE_VERSION,
        category="compatibility",
        status=RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title=f"Failed to import {t.module}",
        message=f"Import failed against homeassistant=={ha_version}: {last_line}",
        applicability=_SMOKE_APPLICABILITY,
        source=_SMOKE_SOURCE,
        path=str(t.file_path),
    )


def _make_finding_harness_error(message: str, ha_version: str) -> Finding:
    """Used when the harness itself fails — uv missing mid-run, install failure, timeout."""
    return Finding(
        rule_id="smoke.harness.error",
        rule_version=SMOKE_RULE_VERSION,
        category="compatibility",
        status=RuleStatus.FAIL,
        severity=RuleSeverity.REQUIRED,
        title="Smoke harness failed",
        message=message,
        applicability=_SMOKE_APPLICABILITY,
        source=_SMOKE_SOURCE,
    )


# ---------------------------------------------------------------------------
# Venv management helpers
# ---------------------------------------------------------------------------


def _create_venv(
    venv_path: Path,
    python_version: str,
    run_fn: RunFn | None = None,
) -> None:
    """Create a venv at *venv_path* using ``uv venv``.

    Raises:
        SmokeError: if uv returns a non-zero exit code.
    """
    _run = run_fn or _runner.run_command
    rc, _stdout, stderr = _run(
        ["uv", "venv", "--python", python_version, str(venv_path)],
        timeout=60.0,
    )
    if rc != 0:
        raise SmokeError(f"uv venv failed (rc={rc}): {stderr.strip()}")


def _install_packages(
    venv_path: Path,
    packages: list[str],
    run_fn: RunFn | None = None,
) -> None:
    """Install *packages* into the venv using ``uv pip install``.

    Raises:
        SmokeError: if uv returns a non-zero exit code (S10).
    """
    _run = run_fn or _runner.run_command
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"
    rc, _stdout, stderr = _run(
        ["uv", "pip", "install", "--python", str(python_path), *packages],
        timeout=300.0,
    )
    if rc != 0:
        raise SmokeError(f"uv pip install failed (rc={rc}): {stderr.strip()}")


# ---------------------------------------------------------------------------
# Probe-target list construction
# ---------------------------------------------------------------------------


def build_probe_targets(integration_path: Path, manifest: dict) -> list[ProbeTarget]:
    """Build the list of modules to probe from *manifest*, skipping absent files.

    Only includes a module if its corresponding .py file exists on disk (D8).
    """
    domain = manifest["domain"]
    candidates: list[tuple[str, Path]] = [
        (f"custom_components.{domain}", integration_path / "__init__.py"),
        (
            f"custom_components.{domain}.config_flow",
            integration_path / "config_flow.py",
        ),
    ]
    for platform in manifest.get("platforms", []):
        candidates.append(
            (
                f"custom_components.{domain}.{platform}",
                integration_path / f"{platform}.py",
            )
        )
    return [ProbeTarget(module=m, file_path=p) for m, p in candidates if p.exists()]


# ---------------------------------------------------------------------------
# Per-module probe
# ---------------------------------------------------------------------------


def _probe_module(
    venv: Path,
    target: ProbeTarget,
    work_dir: Path,
    ha_version: str,
    timeout_s: float = 30.0,
    run_fn: RunFn | None = None,
) -> Finding:
    """Run ``python -c "import <module>"`` inside *venv* and return a Finding."""
    _run = run_fn or _runner.run_command
    if sys.platform == "win32":
        py = venv / "Scripts" / "python.exe"
    else:
        py = venv / "bin" / "python"
    # sys.path.insert(0, work_dir) so that custom_components.<domain> resolves
    code = (
        f"import importlib, sys; "
        f"sys.path.insert(0, {str(work_dir)!r}); "
        f"importlib.import_module({target.module!r})"
    )
    rc, _stdout, stderr = _run(
        [str(py), "-c", code],
        timeout=timeout_s,
        cwd=work_dir,
    )
    if rc == 0:
        return _make_finding_pass(target, ha_version)
    return _make_finding_fail(target, ha_version, stderr)


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _build_report(
    target_path: Path,
    findings: list[Finding],
    *,
    ha_version: str,
    python_version: str,
    domain: str | None,
    integration_path: Path | None,
) -> HassCheckReport:
    now = datetime.now(UTC)

    detected = detect_target(
        target_path, integration_path, domain, ha_version=ha_version
    )
    if detected is not None:
        target = detected.model_copy(
            update={
                "check_mode": "import-smoke",
                "python_version": python_version,  # smoke venv Python, not host
            }
        )
    else:
        # Extreme-failure fallback: detect_target returned None
        target = ReportTarget(
            integration_domain=domain,
            ha_version=ha_version,
            python_version=python_version,
            check_mode="import-smoke",
        )

    pass_count = sum(1 for f in findings if f.status is RuleStatus.PASS)
    category_signal = CategorySignal(
        id="compatibility",
        label="Import Compatibility",
        points_awarded=pass_count,
        points_possible=len(findings),
    )
    summary = ReportSummary(categories=[category_signal] if findings else [])

    project = ProjectInfo(
        path=str(target_path),
        type="integration" if integration_path is not None else "unknown",
        domain=domain,
        integration_path=str(integration_path.relative_to(target_path))
        if integration_path
        else None,
        repo_slug=detect_repo_slug(target_path, integration_path),
    )

    return HassCheckReport(
        project=project,
        summary=summary,
        findings=findings,
        target=target,
        validity=build_validity(checked_at=now),
        provenance=detect_provenance(now=now),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_smoke(
    target_path: Path,
    *,
    ha_version: str,
    python_version: str,
    timeout_s: float = 120.0,
    cache_dir: Path | None = None,
) -> RunSmokeResult:
    """Orchestrate one (ha_version, python_version) smoke run.

    Steps:
    1. Resolve the integration domain and manifest.
    2. Compute venv path; check reuse.
    3. Create venv if not ready.
    4. Install homeassistant==<ver> + manifest requirements.
    5. Build probe targets.
    6. Probe each module.
    7. Build and return RunSmokeResult.

    Error boundary: SmokeError subclasses caught here → harness.error Finding.
    """
    root = Path(target_path).resolve()

    try:
        # Resolve integration path and manifest
        custom_components = root / "custom_components"
        integration_path: Path | None = None
        domain: str | None = None
        manifest: dict = {}

        if custom_components.is_dir():
            subdirs = sorted(
                p
                for p in custom_components.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            )
            if subdirs:
                integration_path = subdirs[0]
                domain = integration_path.name
                manifest_file = integration_path / "manifest.json"
                if manifest_file.exists():
                    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        venv = get_venv_path(ha_version, python_version, cache_dir=cache_dir)
        reused = is_venv_ready(venv)

        if not reused:
            _create_venv(venv, python_version)

        # Determine packages to install
        requirements: list[str] = list(manifest.get("requirements", []))
        packages = [f"homeassistant=={ha_version}", *requirements]
        _install_packages(venv, packages)

        # Build probe targets and run probes
        probe_targets: list[ProbeTarget] = []
        if integration_path is not None and manifest:
            probe_targets = build_probe_targets(integration_path, manifest)

        # work_dir is the repo root (parent of custom_components/)
        findings = [
            _probe_module(venv, t, root, ha_version, timeout_s=timeout_s)
            for t in probe_targets
        ]

    except (SmokeError, SmokeTimeoutError) as exc:
        error_finding = _make_finding_harness_error(str(exc), ha_version)
        report = _build_report(
            root,
            [error_finding],
            ha_version=ha_version,
            python_version=python_version,
            domain=None,
            integration_path=None,
        )
        return RunSmokeResult(
            ha_version=ha_version,
            python_version=python_version,
            report=report,
            venv_reused=False,
        )

    report = _build_report(
        root,
        findings,
        ha_version=ha_version,
        python_version=python_version,
        domain=domain,
        integration_path=integration_path,
    )
    return RunSmokeResult(
        ha_version=ha_version,
        python_version=python_version,
        report=report,
        venv_reused=reused,
    )
