"""Scaffold CLI subapp — registered in main hasscheck CLI as 'scaffold'.

No subcommands are defined here yet; they are added in Tasks 3-5.
"""

from __future__ import annotations

import typer

scaffold_app = typer.Typer(
    name="scaffold",
    help="Generate conservative starter files for common integration patterns.",
    no_args_is_help=True,
)
