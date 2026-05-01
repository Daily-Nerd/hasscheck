"""Scaffold engine — template loading, rendering, and safe file writing.

Architecture decisions implemented here:
- A: Static .tmpl files loaded via importlib.resources.files(); substitution
     via stdlib string.Template ($variable syntax). No Jinja2.
- C: check_applicability_gate() returns a warning string when the relevant
     applicability flag is explicitly False, None when generation is allowed.
- D: write_or_refuse() raises FileExistsError if path exists and force=False;
     writes (or overwrites) otherwise; dry_run prints to stdout instead.
"""

from __future__ import annotations

import string
from importlib.resources import files
from pathlib import Path

from hasscheck.config import HassCheckConfig

# Mapping scaffold_type -> ProjectApplicability field name.
# scaffold types without an entry have no applicability gate.
_GATE_FLAGS: dict[str, str] = {
    "diagnostics": "supports_diagnostics",
    "repairs": "has_user_fixable_repairs",
}


def load_template(name: str) -> str:
    """Load a .tmpl file from the hasscheck.scaffold.templates package.

    Args:
        name: Filename inside the templates directory, e.g. "diagnostics.tmpl".

    Returns:
        The raw template text (UTF-8).

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    return (
        files("hasscheck.scaffold.templates").joinpath(name).read_text(encoding="utf-8")
    )


def render(template: str, **variables: str) -> str:
    """Substitute $-style variables in *template* using *variables*.

    Uses stdlib string.Template (safe_substitute is NOT used — missing keys
    raise KeyError intentionally so callers get explicit errors).

    Args:
        template: Raw template string with $variable placeholders.
        **variables: Variable name and substitution value pairs.

    Returns:
        Rendered string.

    Raises:
        KeyError: If a placeholder in the template is not in *variables*.
        ValueError: If the template contains an invalid $-placeholder (e.g. $1 or a bare $).
    """
    return string.Template(template).substitute(variables)


def write_or_refuse(
    path: Path,
    content: str,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Write *content* to *path*, with safeguards.

    Args:
        path: Destination file path.
        content: Text to write (UTF-8).
        force: If True, overwrite an existing file. Default False.
        dry_run: If True, print content to stdout instead of writing.
                 Bypasses both the FileExistsError check and any disk writes.

    Raises:
        FileExistsError: If *path* exists, *force* is False, and *dry_run* is False.
    """
    if dry_run:
        print(content)
        return

    if path.exists() and not force:
        raise FileExistsError(
            f"File already exists: {path}\n"
            "Use --force to overwrite, or --dry-run to preview."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def check_applicability_gate(
    config: HassCheckConfig | None,
    scaffold_type: str,
) -> str | None:
    """Return a warning message if *scaffold_type* should be refused, else None.

    Refusal happens only when the relevant applicability flag is **explicitly
    False** in hasscheck.yaml. Absent config, absent applicability block, or a
    None/True flag all allow generation.

    Args:
        config: Loaded HassCheckConfig, or None when no config file exists.
        scaffold_type: One of "diagnostics", "repairs", "github-action", or
                       any future type string.

    Returns:
        A human-readable warning string if generation should be refused,
        None if generation is allowed.
    """
    flag_name = _GATE_FLAGS.get(scaffold_type)
    if flag_name is None:
        # No gate defined for this scaffold type — always allow.
        return None

    if config is None or config.applicability is None:
        return None

    flag_value = getattr(config.applicability, flag_name, None)
    if flag_value is False:
        return (
            f"Refused: hasscheck.yaml sets {flag_name}: false, "
            f"indicating this project does not support {scaffold_type}. "
            f"Pass --force to generate anyway, or remove the flag from hasscheck.yaml."
        )

    return None
