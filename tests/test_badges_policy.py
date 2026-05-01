import pytest

from hasscheck.badges.policy import (
    ALLOWED_SUFFIXES,
    CATEGORY_LABELS,
    FORBIDDEN_LABEL_TOKENS,
    BadgePolicyError,
    assert_label_is_clean,
)


def test_category_labels_are_clean():
    for label in CATEGORY_LABELS.values():
        assert_label_is_clean(label)  # must not raise


def test_allowed_suffixes_are_clean():
    for suffix in ALLOWED_SUFFIXES:
        assert_label_is_clean(suffix)  # must not raise


@pytest.mark.parametrize("token", sorted(FORBIDDEN_LABEL_TOKENS))
def test_forbidden_tokens_rejected(token):
    with pytest.raises(BadgePolicyError):
        assert_label_is_clean(token)


@pytest.mark.parametrize("token", sorted(FORBIDDEN_LABEL_TOKENS))
def test_forbidden_tokens_rejected_case_insensitive(token):
    with pytest.raises(BadgePolicyError):
        assert_label_is_clean(token.upper())


def test_clean_label_passes():
    assert_label_is_clean("HACS Structure")
    assert_label_is_clean("Passing")
    assert_label_is_clean("Partial")
