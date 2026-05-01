from __future__ import annotations

from pydantic import BaseModel

from hasscheck.badges.policy import (
    CATEGORY_LABELS,
    PRESENT_ABSENT_CATEGORIES,
    assert_label_is_clean,
)
from hasscheck.models import CategorySignal


class BadgeStatus(BaseModel):
    category_id: str
    label_left: str
    label_right: str
    color: str


def category_to_status(cat: CategorySignal) -> BadgeStatus | None:
    """Return None when all rules are N/A (points_possible == 0) — omit badge."""
    if cat.points_possible == 0:
        return None

    label_left = CATEGORY_LABELS.get(cat.id, cat.label)
    use_present = cat.id in PRESENT_ABSENT_CATEGORIES

    if cat.points_awarded == cat.points_possible:
        label_right = "Present" if use_present else "Passing"
        color = "brightgreen"
    elif cat.points_awarded == 0:
        label_right = "Missing" if use_present else "Issues"
        color = "red"
    else:
        label_right = "Partial"
        color = "yellow"

    assert_label_is_clean(label_right)
    return BadgeStatus(
        category_id=cat.id,
        label_left=label_left,
        label_right=label_right,
        color=color,
    )


def umbrella_status() -> BadgeStatus:
    return BadgeStatus(
        category_id="umbrella",
        label_left="HassCheck",
        label_right="Signals Available",
        color="lightgrey",
    )
