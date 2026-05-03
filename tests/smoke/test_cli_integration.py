"""Group 9: Integration test — full CLI with monkeypatched subprocess, 2-version matrix."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from hasscheck.smoke.cli import smoke_app

runner = CliRunner()


def _make_integration(tmp_path: Path) -> Path:
    """Create a minimal integration structure."""
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


def _fake_run_success(*args, **kwargs):
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    m.stderr = ""
    return m


def test_matrix_invokes_run_smoke_twice(monkeypatch, tmp_path) -> None:
    """--ha-version-matrix='2025.4,2025.5' → run_smoke invoked once per version (S5)."""
    repo = _make_integration(tmp_path)
    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", _fake_run_success)

    call_log: list[str] = []
    original_run_smoke = __import__(
        "hasscheck.smoke.core", fromlist=["run_smoke"]
    ).run_smoke

    def spy_run_smoke(target_path, *, ha_version, **kwargs):
        call_log.append(ha_version)
        return original_run_smoke(target_path, ha_version=ha_version, **kwargs)

    monkeypatch.setattr("hasscheck.smoke.cli.run_smoke", spy_run_smoke)

    result = runner.invoke(
        smoke_app,
        [
            "--path",
            str(repo),
            "--ha-version-matrix",
            "2025.4,2025.5",
        ],
    )
    assert result.exit_code == 0, result.output
    assert call_log == ["2025.4", "2025.5"], f"Expected 2 invocations, got: {call_log}"


def test_matrix_output_contains_both_version_strings(monkeypatch, tmp_path) -> None:
    """Terminal output contains both HA version strings when matrix is used."""
    repo = _make_integration(tmp_path)
    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", _fake_run_success)

    result = runner.invoke(
        smoke_app,
        [
            "--path",
            str(repo),
            "--ha-version-matrix",
            "2025.4,2025.5",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "2025.4" in result.output
    assert "2025.5" in result.output


def test_matrix_json_produces_two_element_array(monkeypatch, tmp_path) -> None:
    """--json with 2-version matrix produces a JSON array of length 2."""
    repo = _make_integration(tmp_path)
    monkeypatch.setattr("hasscheck.smoke.runner.subprocess.run", _fake_run_success)

    result = runner.invoke(
        smoke_app,
        [
            "--path",
            str(repo),
            "--ha-version-matrix",
            "2025.4,2025.5",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) == 2
    # Each element has schema_version (it's a HassCheckReport)
    for item in payload:
        assert "schema_version" in item
