"""Group 1: Package scaffold — assert smoke package has all required modules."""

from __future__ import annotations

import importlib.util


def _spec_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def test_smoke_init_exists() -> None:
    assert _spec_exists("hasscheck.smoke"), "hasscheck.smoke.__init__ missing"


def test_smoke_core_exists() -> None:
    assert _spec_exists("hasscheck.smoke.core"), "hasscheck.smoke.core missing"


def test_smoke_runner_exists() -> None:
    assert _spec_exists("hasscheck.smoke.runner"), "hasscheck.smoke.runner missing"


def test_smoke_cache_exists() -> None:
    assert _spec_exists("hasscheck.smoke.cache"), "hasscheck.smoke.cache missing"


def test_smoke_cli_exists() -> None:
    assert _spec_exists("hasscheck.smoke.cli"), "hasscheck.smoke.cli missing"


def test_smoke_errors_exists() -> None:
    assert _spec_exists("hasscheck.smoke.errors"), "hasscheck.smoke.errors missing"


def test_smoke_models_exists() -> None:
    assert _spec_exists("hasscheck.smoke.models"), "hasscheck.smoke.models missing"
