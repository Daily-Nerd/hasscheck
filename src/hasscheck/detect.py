from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from hasscheck.rules.base import ProjectContext

if TYPE_CHECKING:
    from hasscheck.config import ProjectApplicability


def detect_project(
    root: Path, applicability: ProjectApplicability | None = None
) -> ProjectContext:
    root = root.resolve()
    custom_components = root / "custom_components"
    integration_path: Path | None = None
    domain: str | None = None

    if custom_components.is_dir():
        integrations = sorted(
            path
            for path in custom_components.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        if len(integrations) > 1:
            names = [p.name for p in integrations]
            warnings.warn(
                f"Multiple integrations found in custom_components/: {names}. "
                f"Using '{integrations[0].name}'. "
                "Configure a single integration or use hasscheck.yaml to disambiguate.",
                stacklevel=2,
            )
        if integrations:
            integration_path = integrations[0]
            domain = integration_path.name

    return ProjectContext(
        root=root,
        integration_path=integration_path,
        domain=domain,
        applicability=applicability,
    )
