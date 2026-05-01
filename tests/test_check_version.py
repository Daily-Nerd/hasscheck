import pytest

from scripts.check_version import check_versions, read_pyproject_version, tag_to_version


def test_versions_do_not_drift() -> None:
    assert check_versions() == []


def test_matching_release_tag_passes() -> None:
    assert check_versions(tag=f"v{read_pyproject_version()}") == []


def test_mismatched_release_tag_fails() -> None:
    errors = check_versions(tag="v9.9.9")

    assert any("release tag" in error for error in errors)


def test_release_tag_must_start_with_v() -> None:
    errors = check_versions(tag="0.3.0")

    assert "release tag must start with 'v'" in errors[0]


def test_tag_to_version_rejects_non_semver_tag() -> None:
    with pytest.raises(ValueError, match="X.Y.Z"):
        tag_to_version("vnext")
