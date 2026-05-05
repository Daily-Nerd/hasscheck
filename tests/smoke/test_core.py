"""Group 5: Tests for hasscheck.smoke.core — Finding helpers, venv orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hasscheck.models import RuleStatus
from hasscheck.smoke.errors import SmokeError
from hasscheck.smoke.models import ProbeTarget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_probe_target(
    module: str = "custom_components.foo", path: str = "/foo/__init__.py"
) -> ProbeTarget:
    return ProbeTarget(module=module, file_path=Path(path))


def _fake_run_success(*args, **kwargs):
    """Simulate subprocess.run returning success (rc=0)."""
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    m.stderr = ""
    return m


def _fake_run_import_error(*args, **kwargs):
    """Simulate subprocess.run returning an ImportError in stderr."""
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = "Traceback (most recent call last):\n  ...\nImportError: No module named 'homeassistant.components.foo'"
    return m


def _fake_run_attribute_error(*args, **kwargs):
    """Simulate subprocess.run returning an AttributeError in stderr."""
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = "Traceback (most recent call last):\n  ...\nAttributeError: module 'homeassistant' has no attribute 'old_thing'"
    return m


# ---------------------------------------------------------------------------
# Task 5.1 RED — Finding construction helpers
# ---------------------------------------------------------------------------


def test_make_finding_pass_returns_pass_finding() -> None:
    """_make_finding_pass returns Finding(rule_id='smoke.import.pass', status=PASS)."""
    from hasscheck.smoke.core import _make_finding_pass

    t = _make_probe_target()
    finding = _make_finding_pass(t, "2025.4")
    assert finding.rule_id == "smoke.import.pass"
    assert finding.status is RuleStatus.PASS
    assert finding.category == "compatibility"


def test_make_finding_fail_import_error_maps_to_smoke_import_fail(monkeypatch) -> None:
    """_make_finding_fail maps ImportError in stderr → rule_id='smoke.import.fail'."""
    from hasscheck.smoke.core import _make_finding_fail

    t = _make_probe_target()
    stderr = "ImportError: No module named 'homeassistant.components.foo'"
    finding = _make_finding_fail(t, "2025.4", stderr)
    assert finding.rule_id == "smoke.import.fail"
    assert finding.status is RuleStatus.FAIL
    assert finding.category == "compatibility"


def test_make_finding_fail_module_not_found_maps_to_smoke_import_fail(
    monkeypatch,
) -> None:
    """_make_finding_fail maps ModuleNotFoundError → rule_id='smoke.import.fail'."""
    from hasscheck.smoke.core import _make_finding_fail

    t = _make_probe_target()
    stderr = "ModuleNotFoundError: No module named 'foo'"
    finding = _make_finding_fail(t, "2025.4", stderr)
    assert finding.rule_id == "smoke.import.fail"


def test_make_finding_fail_attribute_error_maps_to_smoke_import_error(
    monkeypatch,
) -> None:
    """_make_finding_fail maps AttributeError in stderr → rule_id='smoke.import.error'."""
    from hasscheck.smoke.core import _make_finding_fail

    t = _make_probe_target()
    stderr = "AttributeError: module 'homeassistant' has no attribute 'old_thing'"
    finding = _make_finding_fail(t, "2025.4", stderr)
    assert finding.rule_id == "smoke.import.error"
    assert finding.status is RuleStatus.FAIL


def test_make_finding_harness_error_returns_correct_rule_id() -> None:
    """_make_finding_harness_error returns rule_id='smoke.harness.error'."""
    from hasscheck.smoke.core import _make_finding_harness_error

    finding = _make_finding_harness_error("harness exploded", "2025.4")
    assert finding.rule_id == "smoke.harness.error"
    assert finding.status is RuleStatus.FAIL
    assert finding.category == "compatibility"


# ---------------------------------------------------------------------------
# Task 5.3 RED — _create_venv / _install_packages
# ---------------------------------------------------------------------------


def test_create_venv_calls_uv_venv(monkeypatch, tmp_path) -> None:
    """_create_venv calls runner with ['uv', 'venv', '--python', ...]."""
    calls = []

    def fake_run(cmd, *, timeout, cwd=None, env=None):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(
        "hasscheck.smoke.runner.subprocess.run", lambda *a, **kw: _fake_run_success()
    )

    from hasscheck.smoke.core import _create_venv

    _create_venv(tmp_path / "venv", "3.12", run_fn=fake_run)
    assert len(calls) == 1
    assert calls[0][0] == "uv"
    assert "venv" in calls[0]
    assert "--python" in calls[0]
    assert "3.12" in calls[0]


def test_create_venv_raises_smoke_error_on_nonzero_rc(tmp_path) -> None:
    """_create_venv raises SmokeError when runner returns non-zero rc."""

    def failing_run(cmd, *, timeout, cwd=None, env=None):
        return (1, "", "uv venv failed")

    from hasscheck.smoke.core import _create_venv

    with pytest.raises(SmokeError):
        _create_venv(tmp_path / "venv", "3.12", run_fn=failing_run)


def test_install_packages_calls_uv_pip_install(tmp_path) -> None:
    """_install_packages calls runner with uv pip install --python ..."""
    calls = []

    def fake_run(cmd, *, timeout, cwd=None, env=None):
        calls.append(cmd)
        return (0, "", "")

    # Create fake python binary
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python").touch()

    from hasscheck.smoke.core import _install_packages

    _install_packages(tmp_path, ["homeassistant==2025.4"], run_fn=fake_run)
    assert len(calls) == 1
    assert "uv" in calls[0]
    assert "pip" in calls[0]
    assert "install" in calls[0]
    assert "--python" in calls[0]


def test_install_packages_raises_smoke_error_on_failure(tmp_path) -> None:
    """_install_packages raises SmokeError when runner returns non-zero rc (S10)."""

    def failing_run(cmd, *, timeout, cwd=None, env=None):
        return (1, "", "installation failed")

    # Create fake python binary
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python").touch()

    from hasscheck.smoke.core import _install_packages

    with pytest.raises(SmokeError):
        _install_packages(tmp_path, ["homeassistant==2025.4"], run_fn=failing_run)


# ---------------------------------------------------------------------------
# Task 5.7 RED — run_smoke orchestration
# ---------------------------------------------------------------------------


def _make_integration(tmp_path: Path) -> Path:
    """Create a minimal integration structure for run_smoke tests."""
    integration = tmp_path / "custom_components" / "foo"
    integration.mkdir(parents=True)
    (integration / "__init__.py").write_text("", encoding="utf-8")
    manifest = {
        "domain": "foo",
        "name": "Foo",
        "documentation": "https://example.com",
        "issue_tracker": "https://example.com/issues",
        "codeowners": ["@foo"],
        "version": "0.1.0",
        "requirements": [],
    }
    (integration / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_run_smoke_all_imports_succeed_produces_pass_findings(
    monkeypatch, tmp_path
) -> None:
    """run_smoke with all subprocess calls succeeding → all PASS findings, venv_reused=False (S1)."""
    repo = _make_integration(tmp_path)

    monkeypatch.setattr(
        "hasscheck.smoke.runner.subprocess.run",
        _fake_run_success,
    )

    from hasscheck.smoke.core import run_smoke

    result = run_smoke(
        repo,
        ha_version="2025.4",
        python_version="3.12",
        timeout_s=30.0,
        cache_dir=tmp_path / "cache",
    )
    assert result.venv_reused is False
    pass_findings = [
        f for f in result.report.findings if f.rule_id == "smoke.import.pass"
    ]
    fail_findings = [f for f in result.report.findings if f.status is RuleStatus.FAIL]
    assert len(pass_findings) >= 1
    assert len(fail_findings) == 0


def test_run_smoke_one_import_error_produces_fail_finding(
    monkeypatch, tmp_path
) -> None:
    """run_smoke with one ImportError in stderr → one FAIL finding (S2)."""
    repo = _make_integration(tmp_path)

    call_count = {"n": 0}

    def selective_fake_run(*args, **kwargs):
        call_count["n"] += 1
        cmd = args[0]
        # First two calls (uv venv + uv pip install) succeed
        if "venv" in cmd or "pip" in cmd:
            return _fake_run_success()
        # Probe calls: fail the first probe
        if call_count["n"] <= 3:
            return _fake_run_import_error()
        return _fake_run_success()

    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", selective_fake_run)

    from hasscheck.smoke.core import run_smoke

    result = run_smoke(
        repo,
        ha_version="2025.4",
        python_version="3.12",
        timeout_s=30.0,
        cache_dir=tmp_path / "cache",
    )
    fail_findings = [f for f in result.report.findings if f.status is RuleStatus.FAIL]
    assert len(fail_findings) >= 1
    assert any(f.rule_id == "smoke.import.fail" for f in fail_findings)


def test_run_smoke_timeout_produces_harness_error_finding(
    monkeypatch, tmp_path
) -> None:
    """run_smoke with SmokeTimeoutError → single harness.error finding (S6)."""
    import subprocess

    repo = _make_integration(tmp_path)

    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=0.001)

    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", timeout_run)

    from hasscheck.smoke.core import run_smoke

    result = run_smoke(
        repo,
        ha_version="2025.4",
        python_version="3.12",
        timeout_s=0.001,
        cache_dir=tmp_path / "cache",
    )
    assert any(f.rule_id == "smoke.harness.error" for f in result.report.findings)


# ---------------------------------------------------------------------------
# TestBuildReportIdentity — issue #185: smoke reports must carry exact-build
# target identity (integration_version, manifest_hash, repo_slug, validity,
# provenance, check_mode override, python_version override).
# ---------------------------------------------------------------------------

_GITHUB_ENV_KEYS = (
    "GITHUB_SHA",
    "GITHUB_REF",
    "GITHUB_ACTIONS",
    "GITHUB_REPOSITORY",
    "GITHUB_SERVER_URL",
)


def _make_integration_with_meta(
    tmp_path: Path,
    version: str = "2.5.0",
    issue_tracker: str | None = None,
) -> tuple[Path, Path, str]:
    """Create tmp_path/custom_components/demo_int/manifest.json.

    Returns (root, integration_path, domain).
    """
    domain = "demo_int"
    integration_path = tmp_path / "custom_components" / domain
    integration_path.mkdir(parents=True)
    manifest: dict = {
        "domain": domain,
        "name": "Demo",
        "version": version,
        "documentation": "https://example.com",
        "codeowners": ["@x"],
        "requirements": [],
    }
    if issue_tracker is not None:
        manifest["issue_tracker"] = issue_tracker
    (integration_path / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path, integration_path, domain


class TestBuildReportIdentity:
    """Tests for _build_report() identity parity with the static path (issue #185)."""

    @pytest.fixture(autouse=True)
    def _scrub_github_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Remove all GitHub Actions env vars so detectors fall back to local mode."""
        for key in _GITHUB_ENV_KEYS:
            monkeypatch.delenv(key, raising=False)

    # G1.2 — S1-happy: integration_version propagated from manifest
    def test_build_report_carries_integration_version(self, tmp_path: Path) -> None:
        """_build_report propagates integration_version from manifest.json."""
        from hasscheck.smoke.core import _build_report

        root, integration_path, domain = _make_integration_with_meta(
            tmp_path, version="2.5.0"
        )
        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.target.integration_version == "2.5.0"

    # G1.3 — S1-happy: manifest_hash is a 64-char hex string
    def test_build_report_carries_manifest_hash(self, tmp_path: Path) -> None:
        """_build_report produces a 64-char hex manifest_hash."""
        from hasscheck.smoke.core import _build_report

        root, integration_path, domain = _make_integration_with_meta(tmp_path)
        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.target.manifest_hash is not None
        assert len(report.target.manifest_hash) == 64
        assert all(c in "0123456789abcdef" for c in report.target.manifest_hash)

    # G1.4 — S2-python-version-override: caller-supplied python_version wins
    def test_build_report_python_version_override_wins(self, tmp_path: Path) -> None:
        """_build_report keeps caller-supplied python_version (\"3.11\") regardless of host."""
        from hasscheck.smoke.core import _build_report

        root, integration_path, domain = _make_integration_with_meta(tmp_path)
        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.11",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.target.python_version == "3.11"

    # G1.5 — S1-happy: check_mode must equal "import-smoke" (not "static")
    def test_build_report_check_mode_override_wins(self, tmp_path: Path) -> None:
        """_build_report forces check_mode to \"import-smoke\" regardless of detect_target."""
        from hasscheck.smoke.core import _build_report

        root, integration_path, domain = _make_integration_with_meta(tmp_path)
        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.target.check_mode == "import-smoke"

    # G1.6 — S5-validity-fields: build_validity semantics
    def test_build_report_validity_uses_build_validity(self, tmp_path: Path) -> None:
        """_build_report uses build_validity: claim_scope=exact_build_only, expires_after_days=90."""
        from hasscheck.smoke.core import _build_report

        root, integration_path, domain = _make_integration_with_meta(tmp_path)
        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.validity.claim_scope == "exact_build_only"
        assert report.validity.expires_after_days == 90

    # G1.7 — S6-provenance-present: provenance populated in local mode
    def test_build_report_provenance_populated_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_build_report populates provenance with source=\"local\" outside CI."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        from hasscheck.smoke.core import _build_report

        root, integration_path, domain = _make_integration_with_meta(tmp_path)
        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.provenance is not None
        assert report.provenance.source == "local"

    # G1.8 — ADR-185-D4: shared timestamp invariant
    def test_build_report_validity_and_provenance_share_timestamp(
        self, tmp_path: Path
    ) -> None:
        """validity.checked_at.isoformat() == provenance.published_at (ADR-185-D4)."""
        from hasscheck.smoke.core import _build_report

        root, integration_path, domain = _make_integration_with_meta(tmp_path)
        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.validity.checked_at.isoformat() == report.provenance.published_at

    # G1.9 — S7-error-path-none-args: error path with None domain/integration_path
    def test_build_report_error_path_no_integration_path(self, tmp_path: Path) -> None:
        """_build_report with integration_path=None returns valid report with check_mode=import-smoke."""
        from hasscheck.smoke.core import _build_report

        harness_err = _make_finding_harness_error_helper()
        report = _build_report(
            tmp_path,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=None,
            integration_path=None,
        )
        assert report.target.check_mode == "import-smoke"

    # G1.10 — S3-detect-target-none: fallback when detect_target returns None
    def test_build_report_fallback_when_detect_target_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When detect_target returns None, _build_report falls back to bare 4-field target."""
        monkeypatch.setattr("hasscheck.smoke.core.detect_target", lambda *a, **kw: None)
        from hasscheck.smoke.core import _build_report

        harness_err = _make_finding_harness_error_helper()
        root, integration_path, domain = _make_integration_with_meta(tmp_path)
        report = _build_report(
            root,
            [harness_err],
            ha_version="2025.4",
            python_version="3.12",
            domain=domain,
            integration_path=integration_path,
        )
        assert report.target.check_mode == "import-smoke"
        assert report.target.integration_version is None
        assert report.target.manifest_hash is None


def _make_finding_harness_error_helper():
    """Create a minimal harness Finding for use in _build_report tests."""
    from hasscheck.smoke.core import _make_finding_harness_error

    return _make_finding_harness_error("test harness error", "2025.4")
