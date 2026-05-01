"""Unit tests for hasscheck.ast_utils.parse_module."""

from __future__ import annotations

import ast
from pathlib import Path

from hasscheck.ast_utils import parse_module


def test_parse_module_success(tmp_path: Path) -> None:
    """Valid Python file returns (tree, None)."""
    py_file = tmp_path / "good.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    tree, error = parse_module(py_file)

    assert tree is not None
    assert isinstance(tree, ast.Module)
    assert error is None


def test_parse_module_oserror_nonexistent(tmp_path: Path) -> None:
    """Non-existent path returns (None, error) where error mentions the path."""
    missing = tmp_path / "does_not_exist.py"

    tree, error = parse_module(missing)

    assert tree is None
    assert error is not None
    assert "does_not_exist.py" in error or "No such file" in error


def test_parse_module_syntax_error(tmp_path: Path) -> None:
    """File with invalid Python syntax returns (None, error)."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(\n", encoding="utf-8")

    tree, error = parse_module(bad_file)

    assert tree is None
    assert error is not None
