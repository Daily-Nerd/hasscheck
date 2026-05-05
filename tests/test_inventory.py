from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from hasscheck.cli import app
from hasscheck.inventory import discover_integrations, run_inventory


def _make_integration(ha_config, domain: str, *, version: str = "0.1.0") -> None:
    integ = ha_config / "custom_components" / domain
    integ.mkdir(parents=True, exist_ok=True)
    (integ / "manifest.json").write_text(
        json.dumps(
            {
                "domain": domain,
                "name": domain.title(),
                "documentation": "https://example.com",
                "issue_tracker": "https://example.com/issues",
                "codeowners": ["@nobody"],
                "version": version,
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# G1 — Discovery tests
# ---------------------------------------------------------------------------


def test_discover_finds_all_valid_integrations(tmp_path) -> None:
    _make_integration(tmp_path, "alpha")
    _make_integration(tmp_path, "beta")
    _make_integration(tmp_path, "gamma")
    result = discover_integrations(tmp_path)
    assert [p.name for p in result] == ["alpha", "beta", "gamma"]


def test_discover_skips_dotfile_dirs(tmp_path) -> None:
    cc = tmp_path / "custom_components"
    cc.mkdir(parents=True)
    (cc / ".cache").mkdir()
    _make_integration(tmp_path, "valid")
    result = discover_integrations(tmp_path)
    assert [p.name for p in result] == ["valid"]


def test_discover_skips_dirs_without_manifest(tmp_path) -> None:
    _make_integration(tmp_path, "valid")
    incomplete = tmp_path / "custom_components" / "incomplete"
    incomplete.mkdir(parents=True, exist_ok=True)
    result = discover_integrations(tmp_path)
    assert [p.name for p in result] == ["valid"]


def test_discover_returns_empty_when_custom_components_missing(tmp_path) -> None:
    result = discover_integrations(tmp_path)
    assert result == []


def test_discover_returns_empty_when_custom_components_empty(tmp_path) -> None:
    (tmp_path / "custom_components").mkdir()
    result = discover_integrations(tmp_path)
    assert result == []


# ---------------------------------------------------------------------------
# G2 — Orchestration / run_inventory tests
# ---------------------------------------------------------------------------


def test_run_inventory_collects_one_entry_per_integration(tmp_path) -> None:
    _make_integration(tmp_path, "alpha")
    _make_integration(tmp_path, "beta")
    _make_integration(tmp_path, "gamma")
    result = run_inventory(tmp_path, no_config=True)
    assert len(result.entries) == 3
    for entry in result.entries:
        assert entry.ok
        assert entry.report is not None


def test_run_inventory_continues_after_check_exception(tmp_path) -> None:
    _make_integration(tmp_path, "good")
    _make_integration(tmp_path, "bad")

    def _raise_for_bad(root, integration_path, domain, **kwargs):
        if domain == "bad":
            raise RuntimeError("Simulated rule crash")
        from hasscheck.checker import run_check_at as _orig

        return _orig(root, integration_path, domain, **kwargs)

    with patch("hasscheck.inventory.run_check_at", side_effect=_raise_for_bad):
        result = run_inventory(tmp_path, no_config=True)

    assert len(result.entries) == 2
    domains = {e.domain for e in result.entries}
    assert domains == {"good", "bad"}
    bad_entry = next(e for e in result.entries if e.domain == "bad")
    good_entry = next(e for e in result.entries if e.domain == "good")
    assert bad_entry.error is not None
    assert "RuntimeError" in bad_entry.error
    assert good_entry.report is not None


def test_run_inventory_summary_counts_fails(tmp_path) -> None:
    # A minimal integration with only manifest.json will trigger FAIL findings
    # (many rules require additional files). This ensures summary.failed >= 1.
    _make_integration(tmp_path, "broken")
    result = run_inventory(tmp_path, no_config=True)
    assert result.summary.failed >= 1
    assert result.exit_code == 1


def test_run_inventory_exit_code_zero_on_empty(tmp_path) -> None:
    (tmp_path / "custom_components").mkdir()
    result = run_inventory(tmp_path, no_config=True)
    assert result.exit_code == 0
    assert result.summary.total == 0


def test_run_inventory_empty_returns_zero_exit_code(tmp_path) -> None:
    result = run_inventory(tmp_path, no_config=True)
    assert result.exit_code == 0
    assert result.summary.total == 0


# ---------------------------------------------------------------------------
# G3 — CLI tests
# ---------------------------------------------------------------------------

runner = CliRunner()


def test_cli_inventory_terminal_output(tmp_path) -> None:
    _make_integration(tmp_path, "myintegration")
    _make_integration(tmp_path, "another")
    result = runner.invoke(app, ["inventory", str(tmp_path), "--no-config"])
    assert "integration(s) scanned" in result.output
    assert "myintegration" in result.output
    assert "another" in result.output


def test_cli_inventory_json_output(tmp_path) -> None:
    _make_integration(tmp_path, "alpha")
    _make_integration(tmp_path, "beta")
    result = runner.invoke(
        app, ["inventory", str(tmp_path), "--format", "json", "--no-config"]
    )
    data = json.loads(result.output)
    assert "integrations" in data
    assert "ha_config" in data
    assert "summary" in data
    assert data["summary"]["total"] == 2
    assert len(data["integrations"]) == 2


def test_cli_inventory_missing_path(tmp_path) -> None:
    nonexistent = tmp_path / "does_not_exist"
    result = runner.invoke(app, ["inventory", str(nonexistent)])
    assert result.exit_code == 2
    # Error message goes to stderr, but CliRunner mixes by default
    assert "does not exist" in result.output or (
        result.output == "" and result.exit_code == 2
    )


def test_cli_inventory_no_custom_components(tmp_path) -> None:
    result = runner.invoke(app, ["inventory", str(tmp_path)])
    assert result.exit_code == 0
    assert "custom_components" in result.output


def test_cli_inventory_propagates_ha_version(tmp_path) -> None:
    _make_integration(tmp_path, "alpha")
    result = runner.invoke(
        app,
        [
            "inventory",
            str(tmp_path),
            "--format",
            "json",
            "--ha-version",
            "2026.5.0",
            "--no-config",
        ],
    )
    data = json.loads(result.output)
    integrations = data["integrations"]
    assert len(integrations) == 1
    # The report's target section should carry ha_version
    target = integrations[0].get("target", {})
    assert target.get("ha_version") == "2026.5.0"
