"""Scaffold CLI subapp — registered in main hasscheck CLI as 'scaffold'."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from hasscheck.scaffold.engine import load_template, render, write_or_refuse

scaffold_app = typer.Typer(
    name="scaffold",
    help="Generate conservative starter files for common integration patterns.",
    no_args_is_help=True,
)

console = Console()


@scaffold_app.command("github-action")
def github_action(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Repository path."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print to stdout, do not write."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file."),
) -> None:
    """Generate a GitHub Actions CI workflow for a Home Assistant custom integration."""
    path = path.resolve()

    if not path.exists() or not path.is_dir():
        console.print(f"[red]Error:[/] Path '{path}' is not a valid directory.")
        raise typer.Exit(code=1)

    template_content = load_template("github_action.yml.tmpl")
    content = render(template_content)

    target = path / ".github" / "workflows" / "hasscheck.yml"

    try:
        write_or_refuse(target, content, force=force, dry_run=dry_run)
    except FileExistsError as exc:
        console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(code=1) from exc

    if not dry_run:
        console.print(f"[green]Created:[/] {target}")
