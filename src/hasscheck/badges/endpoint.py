from __future__ import annotations

from typing import Any

from hasscheck.badges.status import BadgeStatus


def to_shields_endpoint(status: BadgeStatus) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "label": status.label_left,
        "message": status.label_right,
        "color": status.color,
        "cacheSeconds": 300,
    }
