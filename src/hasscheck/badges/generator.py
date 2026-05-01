from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from hasscheck.badges.endpoint import to_shields_endpoint
from hasscheck.badges.policy import BADGE_MANIFEST_SCHEMA_VERSION, assert_label_is_clean
from hasscheck.badges.status import category_to_status, umbrella_status
from hasscheck.models import HassCheckReport


class BadgeArtifact(BaseModel):
    category_id: str
    filename: str
    label_left: str
    label_right: str
    color: str
    points_awarded: int
    points_possible: int


def generate_badges(
    report: HassCheckReport,
    *,
    out_dir: Path,
    include: set[str] | None = None,
    emit_umbrella: bool = True,
) -> list[BadgeArtifact]:
    """
    Write shields.io endpoint JSON files to out_dir.
    Returns list of BadgeArtifact for each file written.
    include=None means all categories.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[BadgeArtifact] = []

    for cat in report.summary.categories:
        if include is not None and cat.id not in include:
            continue

        status = category_to_status(cat)
        if status is None:
            continue  # fully N/A — omit

        assert_label_is_clean(status.label_left)
        assert_label_is_clean(status.label_right)

        filename = f"{cat.id}.json"
        payload = to_shields_endpoint(status)
        (out_dir / filename).write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        artifacts.append(
            BadgeArtifact(
                category_id=cat.id,
                filename=filename,
                label_left=status.label_left,
                label_right=status.label_right,
                color=status.color,
                points_awarded=cat.points_awarded,
                points_possible=cat.points_possible,
            )
        )

    if emit_umbrella:
        umb = umbrella_status()
        assert_label_is_clean(umb.label_left)
        assert_label_is_clean(umb.label_right)
        filename = "hasscheck.json"
        payload = to_shields_endpoint(umb)
        (out_dir / filename).write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        artifacts.append(
            BadgeArtifact(
                category_id="umbrella",
                filename=filename,
                label_left=umb.label_left,
                label_right=umb.label_right,
                color=umb.color,
                points_awarded=0,
                points_possible=0,
            )
        )

    # Write manifest
    manifest = {
        "schema_version": BADGE_MANIFEST_SCHEMA_VERSION,
        "artifacts": [a.model_dump() for a in artifacts],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    return artifacts
