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
