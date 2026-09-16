from datetime import date
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union

from crunch_titles._model import Competition, LeaderboardDefinition, Payout, Round, Target, TeamId, User, UserId
from crunch_titles._repository import Repository
from crunch_titles._utility import best_rank, cast_remove_null, group_by, merge, to_dict, to_float

WeekKey = Union[Round, Payout]

# Used one-shot competitions.
NO_YEAR = 0


class LeaderboardPosition(TypedDict):
    competition: Competition
    year: int
    week_key: WeekKey
    user: User
    rank: float
    leaderboard_size: int
    leaderboard_max_rank: float


def _new_position(
    *,
    competition: Competition,
    year: int,
    week_key: WeekKey,
    user: User,
    rank: float,
    leaderboard_size: int,
    leaderboard_max_rank: float,
) -> LeaderboardPosition:
    return {
        "competition": competition,
        "year": year,
        "week_key": week_key,
        "user": user,
        "rank": rank,
        "leaderboard_size": leaderboard_size,
        "leaderboard_max_rank": leaderboard_max_rank,
    }


def _determine_real_time_positions(
    repository: Repository,
    competition: Competition,
    year: int,
    payouts: List[Payout],
):
    all_positions: List[LeaderboardPosition] = []

    for payout in payouts:
        if payout["granted"] <= 0.001:
            continue  # ignore payout without any real rewards

        recipients = repository.find_all_payout_recipients(payout)
        if not recipients:
            continue

        max_rank = max(
            recipient["rank"]
            for recipient in recipients
        )

        for recipient in recipients:
            user = repository.find_user_by_id(recipient["user_id"])

            all_positions.append(_new_position(
                competition=competition,
                year=year,
                week_key=payout,
                user=user,
                rank=recipient["rank"],  # TODO rerank to account for ties?
                leaderboard_size=payout["size"],
                leaderboard_max_rank=max_rank,
            ))

    return all_positions


def _determine_offline_positions(
    repository: Repository,
    competition: Competition,
    year: int,
    rounds: List[Round],
    default_leaderboard_definition: LeaderboardDefinition,
    targets: List[Target],
):
    all_positions: List[LeaderboardPosition] = []
    for round in rounds:
        phase = repository.find_out_of_sample_phase(round)
        if phase is None:
            continue

        crunch = repository.find_published_crunch(phase)
        if crunch is None:
            continue

        best_rank_per_team_id: Dict[TeamId, float] = {}
        best_rank_per_user_id: Dict[UserId, Optional[float]] = {}
        team_id_per_user_id: Dict[UserId, TeamId] = {}

        for target in targets:
            crunch_target = repository.find_crunch_target(crunch, target)

            leaderboard = repository.find_leaderboard(crunch_target, default_leaderboard_definition)
            if leaderboard is None:
                continue  # TODO should not happen

            positions = repository.find_all_positions(leaderboard)

            if competition["team_based"]:
                best_rank_per_team_id = merge(
                    best_rank_per_team_id,
                    to_dict(
                        (
                            row
                            for row in positions
                            if row["team_id"] is not None and row["reward_rank"] is not None
                        ),
                        key=lambda row: cast_remove_null(row["team_id"]),
                        value=lambda row: float(cast_remove_null(row["reward_rank"])),
                        merge=best_rank,
                    ),
                    best_rank,
                )

                team_id_per_user_id.update({
                    row["user_id"]: row["team_id"]
                    for row in positions
                    if row["team_id"] is not None
                })

            best_rank_per_user_id = merge(
                best_rank_per_user_id,
                to_dict(
                    positions,
                    key=lambda row: row["user_id"],
                    value=lambda row: to_float(row["reward_rank"]),
                    merge=best_rank,
                ),
                best_rank,
            )

        if competition["team_based"]:
            best_rank_per_user_id = merge(
                best_rank_per_user_id,
                {
                    user_id: best_rank(rank, best_rank_per_team_id.get(team_id_per_user_id[user_id]))
                    for user_id, rank in best_rank_per_user_id.items()
                    if user_id in team_id_per_user_id
                },
                best_rank,
            )

        leaderboard_size = len(best_rank_per_user_id)
        leaderboard_max_rank = max((rank for rank in best_rank_per_user_id.values() if rank is not None))

        for user_id, reward_rank in best_rank_per_user_id.items():
            if reward_rank is None:
                # print(f"User {user_id} has no reward rank.")
                continue  # NOTE: Often happen for users in teams where leader did not submit

            all_positions.append(_new_position(
                competition=competition,
                year=year,
                week_key=round,
                user=repository.find_user_by_id(user_id),
                rank=reward_rank,
                leaderboard_size=leaderboard_size,
                leaderboard_max_rank=leaderboard_max_rank,
            ))

    return all_positions


def _delete_present_of_future_years(unit_per_year: Dict[int, Any], current_year: int):
    for year in list(unit_per_year.keys()):
        if year >= current_year:
            del unit_per_year[year]


def determine_positions(
    repository: Repository,
    competition: Competition,
) -> List[Tuple[Tuple[Competition, int], List[LeaderboardPosition]]]:
    current_year = date.today().year

    is_still_open = competition["status"] != "CLOSED"

    if competition["mode"] == "REAL_TIME":
        all_payouts = repository.find_all_paid_checkpoint_payouts(competition)
        payouts_per_year = group_by(
            all_payouts,
            key=lambda payout: payout["date"].year,
        )

        if is_still_open:
            _delete_present_of_future_years(payouts_per_year, current_year)

        return [
            (
                (competition, year),
                _determine_real_time_positions(
                    repository,
                    competition,
                    year=year,
                    payouts=payouts,
                )
            )
            for year, payouts in payouts_per_year.items()
        ]

    elif competition["mode"] == "OFFLINE":
        default_leaderboard_definition = repository.find_default_leaderboard_definition(competition)
        targets = repository.find_all_usable_targets(competition)

        all_rounds = repository.find_all_rounds(competition)

        if competition["continuous"]:
            rounds_per_year = group_by(
                all_rounds,
                key=lambda round: round["end"].year,
            )

            if is_still_open:
                _delete_present_of_future_years(rounds_per_year, current_year)

        else:
            rounds_per_year = {
                NO_YEAR: all_rounds
            }

            if is_still_open:
                _delete_present_of_future_years(rounds_per_year, NO_YEAR)

        return [
            (
                (competition, year),
                _determine_offline_positions(
                    repository,
                    competition,
                    year=year,
                    rounds=rounds,
                    default_leaderboard_definition=default_leaderboard_definition,
                    targets=targets,
                )
            )
            for year, rounds in rounds_per_year.items()
        ]

    return []
