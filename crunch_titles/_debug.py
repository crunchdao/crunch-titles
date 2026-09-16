from typing import TYPE_CHECKING, Any, Callable, List, Set, Tuple

from crunch_titles._medal import MedalCountPerUserList
from crunch_titles._model import Competition, UserId
from crunch_titles._position import LeaderboardPosition
from crunch_titles._utility import nunique

Printer = Callable[[Any], Any]

if TYPE_CHECKING:
    from crunch_titles import LocalTitlePositionPerCompetitionYearList


def print_competition_positions_count(
    printer: Printer,
    grouped_positions: List[Tuple[Tuple[Competition, int], List[LeaderboardPosition]]],
):
    printer(f"{'competition':50} {'total':6} {'unique':>8}")

    for (competition, year), positions in grouped_positions:
        tag = f"{competition['name']}:{year}"
        unique = nunique(positions, lambda x: x["week_key"]["id"])

        printer(f"{tag:50} {len(positions):6} {unique:8}")


def print_user_ranks(
    printer: Printer,
    merged_leaderboards: "LocalTitlePositionPerCompetitionYearList",
    user_login: str,
):
    printer(f"{'user':<20} {'competition:year':<50} {'rank':>6}   {'usr.cnt':>7}")

    for (competition, year), positions, user_count in merged_leaderboards:
        for position in positions:
            if position["user"]["login"] != user_login:
                continue

            tag = f"{competition['name']}:{year}"
            printer(f"{user_login:<20} {tag:<50} {float(position['rank']):>6.3}   {user_count:>7}")

            break


def print_medals(
    printer: Printer,
    merged_leaderboards: "LocalTitlePositionPerCompetitionYearList",
    competition_name: str,
    year: int,
):
    printer(f"{'login':<40}  {'rank':>6}  {'medal':<6}")

    for (competition, _), positions, _ in merged_leaderboards:
        if competition["name"] != competition_name or year != year:
            continue

        positions = list(positions)
        positions.sort(key=lambda x: x["rank"])

        for position in positions:
            printer(f"{position['user']['login']:<40}  {position['rank']:6}  {position.get('medal', ''):<6}")

        break


def print_medal_counts(
    printer: Printer,
    medal_counts: MedalCountPerUserList,
):
    _sorted_medal_counts = list(medal_counts)
    _sorted_medal_counts.sort(key=lambda item: (
        item[1].get("GOLD", 0),
        item[1].get("SILVER", 0),
        item[1].get("BRONZE", 0)
    ), reverse=True)

    printer(f"{'user':<30} {'gold':>6} {'silver':>6} {'bronze':>6} {'top 10%':>6} {'top 20%':>6}")

    for user, medals in _sorted_medal_counts:
        gold_count = medals.get("GOLD", "-")
        silver_count = medals.get("SILVER", "-")
        bronze_count = medals.get("BRONZE", "-")
        top_10_percent_rank = medals.get("TOP_10_PERCENT", "-")
        top_20_percent_count = medals.get("TOP_20_PERCENT", "-")

        printer(f"{user['login']:<30} {gold_count:>6} {silver_count:>6} {bronze_count:>6} {top_10_percent_rank:>6} {top_20_percent_count:>6}")


def print_titles_count(
    printer: Printer,
    grandmaster_user_ids: Set[UserId],
    master_user_ids: Set[UserId],
    expert_user_ids: Set[UserId],
    ranked_user_ids: Set[UserId],
):
    printer("Titles count:")

    printer(f"- grandmasters {len(grandmaster_user_ids)}")
    printer(f"- masters {len(master_user_ids)}")
    printer(f"- experts {len(expert_user_ids)}")
    printer(f"- ranked {len(ranked_user_ids)}")

    printer(f"- total {len(grandmaster_user_ids) + len(master_user_ids) + len(expert_user_ids) + len(ranked_user_ids)}")
