from hasscheck.badges.status import category_to_status, umbrella_status
from hasscheck.models import CategorySignal


def make_cat(cat_id: str, awarded: int, possible: int) -> CategorySignal:
    return CategorySignal(
        id=cat_id, label=cat_id, points_awarded=awarded, points_possible=possible
    )


def test_passing_returns_brightgreen():
    status = category_to_status(make_cat("hacs_structure", 10, 10))
    assert status is not None
    assert status.label_right == "Passing"
    assert status.color == "brightgreen"


def test_partial_returns_yellow():
    status = category_to_status(make_cat("hacs_structure", 5, 10))
    assert status is not None
    assert status.label_right == "Partial"
    assert status.color == "yellow"


def test_issues_returns_red():
    status = category_to_status(make_cat("hacs_structure", 0, 10))
    assert status is not None
    assert status.label_right == "Issues"
    assert status.color == "red"


def test_fully_na_returns_none():
    status = category_to_status(make_cat("hacs_structure", 0, 0))
    assert status is None


def test_diagnostics_passing_uses_present():
    status = category_to_status(make_cat("diagnostics_repairs", 5, 5))
    assert status is not None
    assert status.label_right == "Present"


def test_diagnostics_zero_uses_missing():
    status = category_to_status(make_cat("diagnostics_repairs", 0, 5))
    assert status is not None
    assert status.label_right == "Missing"


def test_config_flow_passing_uses_present():
    status = category_to_status(make_cat("modern_ha_patterns", 10, 10))
    assert status is not None
    assert status.label_right == "Present"


def test_umbrella_always_lightgrey():
    umb = umbrella_status()
    assert umb.color == "lightgrey"
    assert umb.label_right == "Signals Available"
