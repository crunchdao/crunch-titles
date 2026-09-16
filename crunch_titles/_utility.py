from crunch_global_leaderboard._utility import to_dict as to_dict
from crunch_global_leaderboard._utility import identity as identity
from crunch_global_leaderboard._utility import group_by as group_by
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, Optional, TypeVar, overload

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def merge(
    left: Dict[K, V],
    right: Dict[K, V],
    merger: Callable[[V, V], V],
) -> Dict[K, V]:
    result = left.copy()
    for key, value in right.items():
        if key in result:
            result[key] = merger(result[key], value)
        else:
            result[key] = value

    return result


def nunique(
    iterable: Iterable[T],
    key: Optional[Callable[[T], Any]] = None,
) -> int:
    if key is None:
        key = identity

    seen: set[Any] = set()
    for item in iterable:
        seen.add(key(item))

    return len(seen)


def cast_remove_null(value: Optional[T]) -> T:
    if value is None:
        raise ValueError("value is None")
    return value


def to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


if TYPE_CHECKING:
    from _typeshed import SupportsDunderLT

    ComparableType = TypeVar("ComparableType", bound=SupportsDunderLT["Any"])

    @overload
    def best_rank(left: ComparableType, right: ComparableType) -> ComparableType:
        pass

    @overload
    def best_rank(left: Optional[ComparableType], right: Optional[ComparableType]) -> Optional[ComparableType]:
        pass


def best_rank(
    left: Optional["ComparableType"],
    right: Optional["ComparableType"],
) -> Optional["ComparableType"]:
    if left is None:
        return right

    if right is None:
        return left

    return min(left, right)
