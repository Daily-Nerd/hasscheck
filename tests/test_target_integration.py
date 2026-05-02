"""Integration test: checker.py populates target and validity on reports."""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Scenario 18 — test_checker_populates_target_and_validity_on_report
# ---------------------------------------------------------------------------


def test_checker_populates_target_and_validity_on_report(tmp_path: Path) -> None:
    from hasscheck.checker import run_check

    # Write a minimal manifest.json with a version
    integration_dir = tmp_path / "custom_components" / "my_integration"
    integration_dir.mkdir(parents=True)
    (integration_dir / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "my_integration",
                "name": "My Integration",
                "version": "1.0.0",
                "documentation": "https://example.com",
                "requirements": [],
                "codeowners": [],
            }
        )
    )

    report = run_check(tmp_path)

    assert report.target is not None, "report.target must not be None after run_check"
    assert report.validity is not None, (
        "report.validity must not be None after run_check"
    )
