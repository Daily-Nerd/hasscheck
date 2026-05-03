"""Venv path resolution and cache key derivation for the smoke harness.

No platformdirs dependency — uses stdlib os.environ + pathlib.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def cache_root() -> Path:
    """Resolve the user cache directory for hasscheck smoke venvs.

    Linux/macOS: ``$XDG_CACHE_HOME/hasscheck`` or ``~/.cache/hasscheck``.
    Windows: ``%LOCALAPPDATA%/hasscheck`` or ``~/AppData/Local/hasscheck``.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "hasscheck"


def cache_key(ha_version: str, python_version: str) -> str:
    """Return a normalised cache key string.

    Strips the leading ``v`` from *ha_version* and normalises *python_version*
    to ``X.Y`` (drops any patch component).
    """
    ha = ha_version.lstrip("v")
    py_parts = python_version.split(".")
    py = ".".join(py_parts[:2]) if len(py_parts) >= 2 else python_version
    return f"ha-{ha}-py-{py}"


def get_venv_path(
    ha_version: str,
    python_version: str,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """Return the deterministic venv path for the given (ha_version, python_version).

    Does NOT create the venv. Callers must check :func:`is_venv_ready` and
    create if needed.
    """
    root = cache_dir if cache_dir is not None else cache_root()
    return root / "smoke" / cache_key(ha_version, python_version)


def is_venv_ready(venv_path: Path) -> bool:
    """Return ``True`` if the python binary inside *venv_path* exists.

    Uses the platform-appropriate binary path:
    - Linux/macOS: ``<venv>/bin/python``
    - Windows: ``<venv>/Scripts/python.exe``
    """
    if sys.platform == "win32":
        py_bin = venv_path / "Scripts" / "python.exe"
    else:
        py_bin = venv_path / "bin" / "python"
    return py_bin.exists()
