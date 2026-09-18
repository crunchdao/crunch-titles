from logging import Logger
from math import ceil
from typing import List, Optional, Tuple, TypedDict

from tqdm import tqdm

from crunch_titles._constants import TitlesParameters
from crunch_titles._database import Database
from crunch_titles._debug import print_competition_positions_count, print_medal_counts, print_user_ranks
from crunch_titles._medal import count_medals_per_user, distribute_medals
from crunch_titles._model import Competition, CompetitionName, Medal, TitleLeaderboard, User
from crunch_titles._position import LeaderboardPosition, determine_positions
from crunch_titles._repository import LoadEverythingRepository, Repository
from crunch_titles._title import compute_all_titles
from crunch_titles._utility import best_rank, group_by, merge, nunique, to_dict


def _find_competition_and_depedencies(
    *,
    repository: Repository,
    competition_name: CompetitionName,
) -> List[Competition]:
    competition = repository.find_competition_by_name(competition_name)
    if competition["name"] in TitlesParameters.MERGED_COMPETITION_CANDIDATES:
        return []

    competitions = [competition]
    for other_competition_name in TitlesParameters.MERGED_COMPETITIONS.get(competition["name"]) or []:
        other_competition = repository.find_competition_by_name(other_competition_name)
        competitions.append(other_competition)

    return competitions


class LocalTitlePosition(TypedDict):
    competition: Competition
    year: int
    user: User
    average: float
    rank: int
    participation_count: int
    medal: Medal


def dense_rerank(
    *,
    positions: List[LocalTitlePosition],
):
    rank = 0
    previous_value = None

    positions.sort(key=lambda x: x["average"])

    for position in positions:
        position["average"] = ceil(position["average"])

    for position in positions:
        if position["average"] != previous_value:
            rank += 1
            previous_value = position["average"]

        position["rank"] = rank

    return rank


def get_minimum_participation_requirement(
    *,
    competition: Competition,
    week_count: int,
) -> Optional[int]:
    if competition["mode"] == "OFFLINE":
        if competition["continuous"]:
            return ceil(week_count * TitlesParameters.MINIMUM_PARTICIPATION_PERCENTAGE)
        else:
            return None

    elif competition["mode"] == "REAL_TIME":
        return None

    else:
        raise ValueError(f"unsupported competition mode: {competition['mode']}")


def filter_minimum_participation(
    *,
    positions: List[LocalTitlePosition],
    minimum_participation_requirement: int,
) -> List[LocalTitlePosition]:
    return [
        position
        for position in positions
        if position["participation_count"] >= minimum_participation_requirement
    ]


def average_leaderboards(
    *,
    competition: Competition,
    year: int,
    positions: List[LeaderboardPosition],
) -> Tuple[List[LocalTitlePosition], int]:
    week_count = nunique(positions, key=lambda x: x["week_key"]["id"])
    if not week_count:
        return [], 0

    minimum_participation_requirement = get_minimum_participation_requirement(
        competition=competition,
        week_count=week_count,
    )

    rows_per_user = group_by(positions, key=lambda x: x["user"]["id"])
    user_count = len(rows_per_user)

    averaged: List[LocalTitlePosition] = []
    for user_rows in rows_per_user.values():
        count = len(user_rows)

        averaged.append({
            "competition": competition,
            "year": year,
            "user": user_rows[0]["user"],
            "average": sum(row["rank"] for row in user_rows) / count,
            "rank": 0,
            "participation_count": count,
            "medal": "NONE",
        })

    if minimum_participation_requirement is not None:
        averaged = filter_minimum_participation(
            positions=averaged,
            minimum_participation_requirement=minimum_participation_requirement,
        )

    dense_rerank(
        positions=averaged,
    )

    return averaged, user_count


LocalTitlePositionPerCompetitionYearItem = Tuple[Tuple[Competition, int], List[LocalTitlePosition], int]
LocalTitlePositionPerCompetitionYearList = List[LocalTitlePositionPerCompetitionYearItem]


def merge_leaderboards(
    *,
    repository: Repository,
    averaged_leaderboards: LocalTitlePositionPerCompetitionYearList,
) -> LocalTitlePositionPerCompetitionYearList:
    all_positions: LocalTitlePositionPerCompetitionYearList = []

    leaderboard_rows_per_competition_name_and_year = to_dict(
        averaged_leaderboards,
        key=lambda x: (x[0][0]["name"], x[0][1]),  # TODO Bad data structure
        value=lambda x: x[1:]
    )

    for (competition, year), leaderboard_rows, user_count in averaged_leaderboards:
        if competition["name"] in TitlesParameters.MERGED_COMPETITION_CANDIDATES:
            continue

        leaderboard_rows_per_user_id = to_dict(
            leaderboard_rows,
            key=lambda x: x["user"]["id"],
        )

        modified = False

        other_competition_names = TitlesParameters.MERGED_COMPETITIONS.get(competition["name"]) or []
        for other_competition_name in other_competition_names:
            other_competition = repository.find_competition_by_name(other_competition_name)
            if not other_competition:
                continue

            other_leaderboard_rows, _ = leaderboard_rows_per_competition_name_and_year.get((other_competition_name, year)) or ([], 0)
            if not other_leaderboard_rows:
                continue

            modified = True
            leaderboard_rows_per_user_id = merge(
                leaderboard_rows_per_user_id,
                to_dict(
                    other_leaderboard_rows,
                    key=lambda x: x["user"]["id"],
                ),
                lambda left, right: {
                    "competition": competition,
                    "year": year,
                    "user": left["user"],  # NOTE: grouped on user, both are the same
                    "average": (left["average"] + right["average"]) / 2,  # NOTE: only works when merging two, at three, average is wrong
                    "rank": best_rank(left["rank"], right["rank"]),
                    "participation_count": left["participation_count"] + right["participation_count"],
                    "medal": "NONE",
                }
            )

        if modified:
            user_count = len(leaderboard_rows_per_user_id)
            leaderboard_rows = list(leaderboard_rows_per_user_id.values())

        all_positions.append(((competition, year), leaderboard_rows, user_count))

    return all_positions


def _restore_competition(
    *,
    repository: LoadEverythingRepository,
    leaderboard: TitleLeaderboard,
) -> LocalTitlePositionPerCompetitionYearItem:
    competition = repository.find_competition_by_id(leaderboard["competition_id"])
    positions = repository.find_all_title_positions_by_leaderboard(leaderboard)

    local_positions: List[LocalTitlePosition] = [
        {
            "competition": competition,
            "year": leaderboard["year"],
            "user": repository.find_user_by_id(position["user_id"]),
            "average": position["averaged_rank"],
            "rank": position["meta_rank"],
            "participation_count": position["participation_count"],
            "medal": position["medal"],
        }
        for position in positions
    ]

    return (
        (
            competition,
            leaderboard["year"]
        ),
        local_positions,
        len(local_positions),
    )


def compute(
    *,
    database: Database,
    competition_name: CompetitionName,
    logger: Logger,
):
    repository = LoadEverythingRepository(
        database=database,
        logger=logger,
    )

    if True:
        competitions = _find_competition_and_depedencies(
            repository=repository,
            competition_name=competition_name,
        )

        if not competitions:
            logger.warning(f"competition not found: {competition_name}")
            return

    if True:
        grouped_positions: List[Tuple[Tuple[Competition, int], List[LeaderboardPosition]]] = []
        for competition in tqdm(competitions, unit="competition"):
            grouped_positions.extend(determine_positions(
                competition=competition,
                repository=repository,
            ))

        print_competition_positions_count(logger.info, grouped_positions)

    if True:
        averaged_leaderboards: LocalTitlePositionPerCompetitionYearList = []
        for (competition, year), positions in grouped_positions:
            title_positions, user_count = average_leaderboards(
                competition=competition,
                year=year,
                positions=positions,
            )

            if len(title_positions):
                averaged_leaderboards.append(((competition, year), title_positions, user_count))

    if True:
        merged_leaderboards = merge_leaderboards(
            repository=repository,
            averaged_leaderboards=averaged_leaderboards,
        )

        print_user_ranks(logger.info, merged_leaderboards, "tarandros")

    if True:
        for (competition, year), positions, user_count in merged_leaderboards:
            distribute_medals(
                positions=positions,
                user_count=user_count,
            )

    if True:
        for (competition, year), _ in grouped_positions:
            repository.delete_title_leaderboard_by_competition_and_year(competition, year)

        for (competition, year), title_positions, user_count in merged_leaderboards:
            title_leaderboard = repository.create_title_leaderboard({
                "competition_id": competition["id"],
                "year": year,
                "week_count": 0,  # TODO!
                "original_size": user_count,
                "size": len(title_positions),
            })

            for position in title_positions:
                repository.create_title_position({
                    "leaderboard_id": title_leaderboard["id"],
                    "user_id": position["user"]["id"],
                    "averaged_rank": position["average"],
                    "participation_count": position["participation_count"],
                    "meta_rank": position["rank"],
                    "medal": position["medal"],
                })

    if True:
        restored_all_leaderboards: LocalTitlePositionPerCompetitionYearList = [
            _restore_competition(repository=repository, leaderboard=leaderboard)
            for leaderboard in repository.find_all_title_leaderboards()
        ]

    if True:
        for (competition, year), positions, user_count in restored_all_leaderboards:
            distribute_medals(
                positions=positions,
                user_count=user_count,
            )

        all_medal_counts = count_medals_per_user(
            merged_leaderboards=restored_all_leaderboards,
        )

        print_medal_counts(logger.info, all_medal_counts)

    if True:
        (
            grandmaster_user_ids,
            master_user_ids,
            expert_user_ids,
            ranked_user_ids,
        ) = compute_all_titles(
            medal_counts=all_medal_counts,
        )

        assert len(grandmaster_user_ids) + len(master_user_ids) + len(expert_user_ids) + len(ranked_user_ids) == len(all_medal_counts)

    if True:
        repository.set_title_for_users("GRANDMASTER", grandmaster_user_ids)
        repository.set_title_for_users("MASTER", master_user_ids)
        repository.set_title_for_users("EXPERT", expert_user_ids)
        repository.set_title_for_users("RANKED", ranked_user_ids)
