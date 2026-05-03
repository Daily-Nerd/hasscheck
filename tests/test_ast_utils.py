"""Unit tests for hasscheck.ast_utils."""

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


# ---------------------------------------------------------------------------
# module_calls_name
# ---------------------------------------------------------------------------


def _make_tree(source: str) -> ast.Module:
    return ast.parse(source)


def test_module_calls_name_with_name_node() -> None:
    """Returns True when the target function is called as a plain Name."""
    from hasscheck.ast_utils import module_calls_name

    source = "async_set_unique_id(value)"
    tree = _make_tree(source)

    assert module_calls_name(tree, "async_set_unique_id") is True


def test_module_calls_name_with_attribute_node() -> None:
    """Returns True when the target function is called as an Attribute."""
    from hasscheck.ast_utils import module_calls_name

    source = "self._abort_if_unique_id_configured()"
    tree = _make_tree(source)

    assert module_calls_name(tree, "_abort_if_unique_id_configured") is True


def test_module_calls_name_absent() -> None:
    """Returns False when the target function is not called anywhere."""
    from hasscheck.ast_utils import module_calls_name

    source = "x = some_other_function()\ny = 42"
    tree = _make_tree(source)

    assert module_calls_name(tree, "async_set_unique_id") is False


def test_module_calls_name_nested_in_class() -> None:
    """Returns True when call is nested inside a class method."""
    from hasscheck.ast_utils import module_calls_name

    source = (
        "class ConfigFlow:\n"
        "    async def async_step_user(self, user_input):\n"
        "        await self.async_set_unique_id(device_id)\n"
    )
    tree = _make_tree(source)

    assert module_calls_name(tree, "async_set_unique_id") is True


def test_module_calls_name_empty_module() -> None:
    """Returns False for an empty module."""
    from hasscheck.ast_utils import module_calls_name

    tree = _make_tree("")

    assert module_calls_name(tree, "anything") is False
