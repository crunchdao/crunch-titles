from decimal import Decimal

import pytest

from crunch_titles._utility import best_rank, cast_remove_null, merge, nunique, to_float


def test_merge():
    assert merge(
        {"hello": "foo"},
        {},
        lambda a, b: a + b
    ) == {"hello": "foo"}

    assert merge(
        {},
        {"hello": "bar"},
        lambda a, b: a + b
    ) == {"hello": "bar"}

    assert merge(
        {"hello": "foo"},
        {"world": "bar"},
        lambda a, b: a + b
    ) == {"hello": "foo", "world": "bar"}

    assert merge(
        {"world": "foo"},
        {"hello": "bar"},
        lambda a, b: a + b
    ) == {"hello": "bar", "world": "foo"}

    assert merge(
        {"hello": "foo"},
        {"hello": "bar"},
        lambda a, b: a + b
    ) == {"hello": "foobar"}


def test_nunique():

    assert nunique([1, 2, 3, 4]) == 4
    assert nunique([1, 2, 2, 3, 3, 3]) == 3
    assert nunique([]) == 0
    assert nunique([1, 1, 1, 1]) == 1

    assert nunique(["a", "b", "c"], key=len) == 1


def test_cast_remove_null():

    assert cast_remove_null(42) == 42

    with pytest.raises(ValueError):
        cast_remove_null(None)


def test_to_float():
    assert to_float(None) is None
    assert to_float(Decimal("4.2")) == 4.2


def test_best_rank():
    assert best_rank(1, None) == 1
    assert best_rank(None, 2) == 2
    assert best_rank(1, 2) == 1
    assert best_rank(None, None) is None

    assert best_rank(Decimal("1"), None) == Decimal("1")
    assert best_rank(None, Decimal("2")) == Decimal("2")
    assert best_rank(Decimal("1"), Decimal("2")) == Decimal("1")
    assert best_rank(None, None) is None
