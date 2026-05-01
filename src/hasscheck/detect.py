from __future__ import annotations

from pathlib import Path

from hasscheck.rules.base import ProjectContext


def detect_project(root: Path) -> ProjectContext:
    root = root.resolve()
    custom_components = root / "custom_components"
    integration_path: Path | None = None
    domain: str | None = None

    if custom_components.is_dir():
        integrations = sorted(
            path for path in custom_components.iterdir() if path.is_dir() and not path.name.startswith(".")
        )
        if integrations:
            integration_path = integrations[0]
            domain = integration_path.name

    return ProjectContext(root=root, integration_path=integration_path, domain=domain)
