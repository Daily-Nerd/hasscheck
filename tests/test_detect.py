import warnings

import pytest

from hasscheck.detect import detect_project


def test_single_integration_no_warning(tmp_path):
    (tmp_path / "custom_components" / "my_integration").mkdir(parents=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ctx = detect_project(tmp_path)
    assert ctx.domain == "my_integration"


def test_no_integrations_no_warning(tmp_path):
    (tmp_path / "custom_components").mkdir()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ctx = detect_project(tmp_path)
    assert ctx.domain is None


def test_multiple_integrations_emits_warning(tmp_path):
    (tmp_path / "custom_components" / "alpha").mkdir(parents=True)
    (tmp_path / "custom_components" / "beta").mkdir(parents=True)
    with pytest.warns(UserWarning, match="Multiple integrations found"):
        ctx = detect_project(tmp_path)
    assert ctx.domain == "alpha"


def test_multiple_integrations_picks_first_alphabetically(tmp_path):
    for name in ("zebra", "alpha", "mango"):
        (tmp_path / "custom_components" / name).mkdir(parents=True)
    with pytest.warns(UserWarning):
        ctx = detect_project(tmp_path)
    assert ctx.domain == "alpha"


def test_multiple_integrations_warning_lists_all_names(tmp_path):
    (tmp_path / "custom_components" / "alpha").mkdir(parents=True)
    (tmp_path / "custom_components" / "beta").mkdir(parents=True)
    with pytest.warns(UserWarning, match="alpha") as record:
        detect_project(tmp_path)
    assert "beta" in str(record[0].message)
