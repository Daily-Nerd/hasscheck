"""Group 3: Tests for hasscheck.smoke.cache — venv path resolution."""

from __future__ import annotations

import sys

import pytest

from hasscheck.smoke.cache import cache_key, cache_root, get_venv_path, is_venv_ready


def test_cache_key_strips_leading_v_from_ha_version() -> None:
    """cache_key strips the leading 'v' from ha_version."""
    key = cache_key("v2025.4.0", "3.12")
    assert "v" not in key.split("-")[1]  # ha part should not have leading v
    assert "2025.4.0" in key


def test_cache_key_normalises_python_to_x_y() -> None:
    """cache_key normalises python_version 3.12.1 → 3.12."""
    key_full = cache_key("2025.4", "3.12.1")
    key_short = cache_key("2025.4", "3.12")
    assert key_full == key_short


def test_cache_key_deterministic() -> None:
    """Identical inputs produce the same cache key."""
    assert cache_key("2025.4", "3.12") == cache_key("2025.4", "3.12")


def test_get_venv_path_returns_same_path_on_identical_inputs(tmp_path) -> None:
    """get_venv_path is deterministic (S9): same inputs → same Path."""
    p1 = get_venv_path("2025.4", "3.12", cache_dir=tmp_path)
    p2 = get_venv_path("2025.4", "3.12", cache_dir=tmp_path)
    assert p1 == p2


def test_get_venv_path_differs_for_different_ha_versions(tmp_path) -> None:
    """Different ha_versions produce different paths."""
    p1 = get_venv_path("2025.4", "3.12", cache_dir=tmp_path)
    p2 = get_venv_path("2025.5", "3.12", cache_dir=tmp_path)
    assert p1 != p2


def test_get_venv_path_is_under_cache_dir(tmp_path) -> None:
    """Returned path is rooted under cache_dir."""
    p = get_venv_path("2025.4", "3.12", cache_dir=tmp_path)
    assert str(p).startswith(str(tmp_path))


@pytest.mark.skipif(
    sys.platform == "win32", reason="XDG_CACHE_HOME is Linux/macOS only"
)
def test_cache_root_honours_xdg_cache_home(monkeypatch, tmp_path) -> None:
    """cache_root uses XDG_CACHE_HOME when set."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    root = cache_root()
    assert str(root).startswith(str(tmp_path))


def test_is_venv_ready_returns_false_when_python_binary_absent(tmp_path) -> None:
    """is_venv_ready returns False when the python binary does not exist."""
    assert is_venv_ready(tmp_path) is False


def test_is_venv_ready_returns_true_when_python_binary_present(tmp_path) -> None:
    """is_venv_ready returns True when the platform python binary is present."""
    if sys.platform == "win32":
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        (scripts / "python.exe").touch()
    else:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "python").touch()
    assert is_venv_ready(tmp_path) is True
