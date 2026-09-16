from typing import Callable, Dict, List, Set, Tuple

from crunch_titles._medal import MedalCountPerUserList
from crunch_titles._model import Medal, UserId


def _on_podium_count(medal_count: Dict[Medal, int]) -> int:
    return medal_count.get("GOLD", 0) + medal_count.get("SILVER", 0) + medal_count.get("BRONZE", 0)


def _in_top_20_count(medal_count: Dict[Medal, int]) -> int:
    return medal_count.get("TOP_10_PERCENT", 0) + medal_count.get("TOP_20_PERCENT", 0)


def compute_titles(
    *,
    medal_counts: MedalCountPerUserList,
    predicate: Callable[[Dict[Medal, int]], bool],
    other_sets: List[Set[UserId]],
) -> Set[UserId]:
    other_user_ids: Set[UserId] = set()
    for other_set in other_sets:
        other_user_ids.update(other_set)

    user_ids: Set[UserId] = set()
    for user, medal_count in medal_counts:
        if user["id"] in other_user_ids:
            continue

        granted = predicate(medal_count)
        if granted:
            user_ids.add(user["id"])

    return user_ids


def compute_grandmasters(
    *,
    medal_counts: MedalCountPerUserList,
) -> Set[UserId]:
    return compute_titles(
        medal_counts=medal_counts,
        predicate=lambda medal_count: _on_podium_count(medal_count) >= 2,
        other_sets=[],
    )


def compute_masters(
    *,
    medal_counts: MedalCountPerUserList,
    grandmasters: Set[UserId],
) -> Set[UserId]:
    return compute_titles(
        medal_counts=medal_counts,
        predicate=lambda medal_count: _on_podium_count(medal_count) >= 1 and _in_top_20_count(medal_count) >= 1,
        other_sets=[grandmasters],
    )


def compute_experts(
    *,
    medal_counts: MedalCountPerUserList,
    grandmasters: Set[UserId],
    masters: Set[UserId],
) -> Set[UserId]:
    return compute_titles(
        medal_counts=medal_counts,
        predicate=lambda medal_count: _on_podium_count(medal_count) >= 1,
        other_sets=[grandmasters, masters],
    )


def compute_ranked(
    *,
    medal_counts: MedalCountPerUserList,
    grandmasters: Set[UserId],
    masters: Set[UserId],
    experts: Set[UserId],
) -> Set[UserId]:
    return compute_titles(
        medal_counts=medal_counts,
        predicate=lambda medal_count: _in_top_20_count(medal_count) >= 1,
        other_sets=[grandmasters, masters, experts],
    )


def compute_all_titles(
    *,
    medal_counts: MedalCountPerUserList,
) -> Tuple[Set[UserId], Set[UserId], Set[UserId], Set[UserId]]:
    grandmasters = compute_grandmasters(
        medal_counts=medal_counts,
    )

    masters = compute_masters(
        medal_counts=medal_counts,
        grandmasters=grandmasters,
    )

    experts = compute_experts(
        medal_counts=medal_counts,
        grandmasters=grandmasters,
        masters=masters,
    )

    ranked = compute_ranked(
        medal_counts=medal_counts,
        grandmasters=grandmasters,
        masters=masters,
        experts=experts,
    )

    return (
        grandmasters,
        masters,
        experts,
        ranked,
    )
