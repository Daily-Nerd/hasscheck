"""AST helpers shared across rule modules."""

from __future__ import annotations

import ast
from pathlib import Path


def has_async_function(tree: ast.Module, name: str) -> bool:
    """Return True if tree contains any AsyncFunctionDef with the given name.

    Uses ast.walk so it finds the function at any nesting depth
    (module-level or as a class method).
    """
    return any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == name
        for node in ast.walk(tree)
    )


def parse_module(path: Path) -> tuple[ast.Module | None, str | None]:
    """Parse a Python file with the standard library AST module.

    Returns (parsed_tree, None) on success, (None, error_msg) on failure.
    Failure modes covered: file unreadable (OSError) and syntax errors.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, str(exc)
    try:
        return ast.parse(source), None
    except SyntaxError as exc:
        return None, exc.msg or "syntax error"
