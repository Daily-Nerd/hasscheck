"""`hasscheck init` — bootstrap a repository for HassCheck.

Generates a conservative `hasscheck.yaml` and the GitHub Actions workflow
using the existing scaffold engine. Refuses to overwrite existing files
unless `--force` is passed; supports `--dry-run` for preview.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hasscheck.scaffold.engine import load_template, render, write_or_refuse


@dataclass(frozen=True)
class InitArtifact:
    """One file produced (or that would be produced) by `hasscheck init`."""

    target: Path
    created: bool  # False when --dry-run or skipped
    skipped_reason: str | None = None


def _hasscheck_yaml_target(root: Path) -> Path:
    return root / "hasscheck.yaml"


def _github_action_target(root: Path) -> Path:
    return root / ".github" / "workflows" / "hasscheck.yml"


def init_project(
    root: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    skip_action: bool = False,
    enable_publish: bool = False,
) -> list[InitArtifact]:
    """Generate `hasscheck.yaml` (and optionally the GitHub Action) at *root*.

    Args:
        root: Repository root.
        dry_run: Print would-be content, do not write.
        force: Overwrite existing files.
        skip_action: Do not generate `.github/workflows/hasscheck.yml`.
        enable_publish: When True, use the publish-aware workflow template
            (grants id-token: write and sets emit-publish: 'true').

    Returns:
        One `InitArtifact` per file considered (whether written, skipped,
        or dry-run-printed).

    Raises:
        FileExistsError: When a target exists and `--force` is not set.
        ValueError: When *root* does not exist or is not a directory.
    """
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Root path '{root}' does not exist or is not a directory.")

    artifacts: list[InitArtifact] = []

    yaml_target = _hasscheck_yaml_target(root)
    yaml_content = load_template("hasscheck.yaml.tmpl")
    write_or_refuse(yaml_target, render(yaml_content), force=force, dry_run=dry_run)
    artifacts.append(InitArtifact(target=yaml_target, created=not dry_run))

    if skip_action:
        return artifacts

    template_name = (
        "github_action_publish.yml.tmpl" if enable_publish else "github_action.yml.tmpl"
    )
    action_target = _github_action_target(root)
    action_content = load_template(template_name)
    write_or_refuse(action_target, render(action_content), force=force, dry_run=dry_run)
    artifacts.append(InitArtifact(target=action_target, created=not dry_run))

    return artifacts
