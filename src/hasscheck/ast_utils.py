"""AST helpers shared across rule modules."""

from __future__ import annotations

import ast
from pathlib import Path


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
