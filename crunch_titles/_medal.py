from collections import defaultdict
from math import ceil
from typing import TYPE_CHECKING, DefaultDict, Dict, List, Tuple

from crunch_titles._model import Medal, User, UserId

if TYPE_CHECKING:
    from crunch_titles import LocalTitlePosition, LocalTitlePositionPerCompetitionYearList


def distribute_medals(
    *,
    positions: List["LocalTitlePosition"],
    user_count: int
) -> None:
    max_rank = user_count

    gold_rank = 1
    silver_rank = 2
    bronze_rank = 3
    honorable_mention_rank = max(4, ceil(0.10 * max_rank))

    for position in positions:
        rank = position["rank"]

        if rank <= gold_rank:
            position["medal"] = "GOLD"
        elif rank <= silver_rank:
            position["medal"] = "SILVER"
        elif rank <= bronze_rank:
            position["medal"] = "BRONZE"
        elif rank <= honorable_mention_rank:
            position["medal"] = "HONORABLE_MENTION"
        else:
            position["medal"] = "NONE"


MedalCountPerUserList = List[Tuple[User, Dict[Medal, int]]]


def count_medals_per_user(
    *,
    merged_leaderboards: "LocalTitlePositionPerCompetitionYearList",
) -> MedalCountPerUserList:
    medal_count_by_user_id: DefaultDict[UserId, DefaultDict[Medal, int]] = defaultdict(lambda: defaultdict(int))
    user_by_id: Dict[UserId, User] = {}

    for _, positions, _ in merged_leaderboards:
        for position in positions:
            medal = position["medal"]
            if medal == "NONE":
                continue

            user = position["user"]

            user_by_id[user["id"]] = user
            medal_count_by_user_id[user["id"]][position["medal"]] += 1

    return [
        (user_by_id[user_id], medals)
        for user_id, medals in medal_count_by_user_id.items()
    ]
