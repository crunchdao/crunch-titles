from abc import ABC, abstractmethod
from logging import Logger
from textwrap import dedent
from typing import Callable, Dict, List, Optional, Set, Tuple, cast, get_args

from tqdm.auto import tqdm

from crunch_titles._database import Database, to_column_names, to_table_name
from crunch_titles._model import (
    Competition,
    CompetitionId,
    CompetitionName,
    Crunch,
    CrunchId,
    CrunchTarget,
    CrunchTargetId,
    Leaderboard,
    LeaderboardDefinition,
    LeaderboardDefinitionId,
    LeaderboardId,
    Payout,
    PayoutId,
    PayoutRecipient,
    Phase,
    PhaseId,
    Position,
    Round,
    RoundId,
    Target,
    TargetId,
    Team,
    TeamId,
    TeamMember,
    Title,
    TitleLeaderboard,
    TitleLeaderboardBody,
    TitleLeaderboardId,
    TitlePosition,
    TitlePositionBody,
    TitlePositionId,
    User,
    UserId
)
from crunch_titles._utility import group_by, to_dict


class Repository(ABC):

    @abstractmethod
    def find_all_competitions(self) -> List[Competition]:
        ...
    
    @abstractmethod
    def find_competition_by_id(self, id: CompetitionId) -> Competition:
        ...

    @abstractmethod
    def find_competition_by_name(self, name: CompetitionName) -> Competition:
        ...
        
    @abstractmethod
    def find_user_by_id(self, id: UserId) -> User:
        ...

    @abstractmethod
    def find_user_by_login(self, login: str) -> User:
        ...

    @abstractmethod
    def find_default_leaderboard_definition(self, competition: Competition) -> LeaderboardDefinition:
        ...

    @abstractmethod
    def find_all_usable_targets(self, competition: Competition) -> List[Target]:
        ...

    @abstractmethod
    def find_all_rounds(self, competition: Competition) -> List[Round]:
        ...

    @abstractmethod
    def find_out_of_sample_phase(self, round: Round) -> Optional[Phase]:
        ...

    @abstractmethod
    def find_published_crunch(self, phase: Phase) -> Optional[Crunch]:
        ...

    @abstractmethod
    def find_crunch_target(self, crunch: Crunch, target: Target) -> CrunchTarget:
        ...

    @abstractmethod
    def find_leaderboard(self, crunch_target: CrunchTarget, leaderboard_definition: LeaderboardDefinition) -> Optional[Leaderboard]:
        ...

    @abstractmethod
    def find_all_positions(self, leaderboard: Leaderboard) -> List[Position]:
        ...

    @abstractmethod
    def find_all_paid_checkpoint_payouts(self, competition: Competition) -> List[Payout]:
        ...

    @abstractmethod
    def find_all_payout_recipients(self, payout: Payout) -> List[PayoutRecipient]:
        ...

    @abstractmethod
    def find_all_teams(self, competition: Competition) -> List[Team]:
        ...

    @abstractmethod
    def find_all_team_members(self, team: Team) -> List[TeamMember]:
        ...

    @abstractmethod
    def create_title_leaderboard(self, body: TitleLeaderboardBody) -> TitleLeaderboard:
        ...

    @abstractmethod
    def find_all_title_leaderboards(self) -> List[TitleLeaderboard]:
        ...

    @abstractmethod
    def delete_title_leaderboard_by_competition_and_year(self, competition: Competition, year: int):
        ...

    @abstractmethod
    def find_all_title_positions_by_leaderboard(self, leaderboard: TitleLeaderboard) -> List[TitlePosition]:
        ...

    @abstractmethod
    def create_title_position(self, body: TitlePositionBody) -> TitlePosition:
        ...

    @abstractmethod
    def set_title_for_users(self, title: Title, user_ids: Set[UserId]) -> None:
        ...


class LoadEverythingRepository(Repository):

    _competitions: List[Competition]
    _competition_by_id: Dict[CompetitionId, Competition]
    _competition_by_name: Dict[CompetitionName, Competition]
    _user_by_id: Dict[UserId, User]
    _user_by_login: Dict[str, User]
    _default_leaderboard_definition_by_competition_id: Dict[CompetitionId, LeaderboardDefinition]
    _usable_targets_by_competition_id: Dict[CompetitionId, List[Target]]
    _rounds_by_competition_id: Dict[CompetitionId, List[Round]]
    _out_of_sample_phase_by_round_id: Dict[RoundId, Phase]
    _published_crunch_by_phase_id: Dict[PhaseId, Crunch]
    _crunch_target_by_crunch_id_and_target_id: Dict[Tuple[CrunchId, TargetId], CrunchTarget]
    _leaderboard_by_crunch_target_id_and_leaderboard_definition_id: Dict[Tuple[CrunchTargetId, LeaderboardDefinitionId], Leaderboard]
    _position_by_leaderboard_id: Dict[LeaderboardId, List[Position]]
    _payouts_by_competition_id: Dict[CompetitionId, List[Payout]]
    _payout_recipients_by_payout_id: Dict[PayoutId, List[PayoutRecipient]]
    _teams_by_competition_id: Dict[CompetitionId, List[Team]]
    _team_members_by_team_id: Dict[TeamId, List[TeamMember]]
    _title_leaderboard_by_competition_id_and_year: Dict[Tuple[CompetitionId, int], TitleLeaderboard]
    _title_positions_by_leaderboard_id: Dict[TitleLeaderboardId, List[TitlePosition]]

    def __init__(
        self,
        *,
        database: Database,
        logger: Logger,
    ):
        self._database = database
        self._logger = logger

        self.load()

    def load(
        self,
        *,
        only: Optional[List[str]] = None,
    ):

        def _load_competitions():
            self._competitions = self._database.competition.query_many_objects(
                Competition,
                where="`visibility` = 'PUBLIC' AND NOT `external`",
            )

            self._competition_by_id = to_dict(
                self._competitions,
                key=lambda row: row["id"],
            )

            self._competition_by_name = to_dict(
                self._competitions,
                key=lambda row: row["name"],
            )

        def _load_users():
            users = self._database.competition.query_many_objects(
                User,
                where="""
                    `id` IN (SELECT DISTINCT `user_id` FROM `positions`)
                    OR `id` IN (SELECT DISTINCT `user_id` FROM `team_members`)
                    OR `id` IN (SELECT DISTINCT `user_id` FROM `payout_recipients`)
                """
            )

            self._user_by_id = to_dict(
                users,
                key=lambda row: row["id"],
            )

            self._user_by_login = to_dict(
                users,
                key=lambda row: row["login"],
            )

        def _load_leaderboard_definitions():
            self._default_leaderboard_definition_by_competition_id = to_dict(
                self._database.competition.query_many_objects(
                    LeaderboardDefinition,
                    where="`default`",
                ),
                key=lambda row: row["competition_id"],
            )

        def _load_targets():
            self._usable_targets_by_competition_id = group_by(
                self._database.competition.query_many_objects(Target),
                key=lambda row: row["competition_id"],
            )

            for targets in self._usable_targets_by_competition_id.values():
                virtual_targets = [
                    target
                    for target in targets
                    if target["virtual"]
                ]

                if len(virtual_targets):
                    targets.clear()
                    targets.extend(virtual_targets)

        def _load_rounds():
            self._rounds_by_competition_id = group_by(
                self._database.competition.query_many_objects(Round),
                key=lambda row: row["competition_id"],
            )

        def _load_phases():
            self._out_of_sample_phase_by_round_id = to_dict(
                self._database.competition.query_many_objects(
                    Phase,
                    where="`type` = 'OUT_OF_SAMPLE'"
                ),
                key=lambda row: row["round_id"],
            )

        def _load_crunches():
            self._published_crunch_by_phase_id = to_dict(
                self._database.competition.query_many_objects(
                    Crunch,
                    where=dedent("""
                        (`phase_id`, `number`) IN (
                            SELECT
                                `phase_id`,
                                MAX(`number`)
                            FROM
                                `crunches`
                            WHERE
                                `published` = true
                            GROUP BY
                                `phase_id`
                        )
                    """),
                ),
                key=lambda row: row["phase_id"],
            )

        def _load_crunch_targets():
            self._crunch_target_by_crunch_id_and_target_id = to_dict(
                self._database.competition.query_many_objects(CrunchTarget),
                key=lambda row: (row["crunch_id"], row["target_id"]),
            )

        def _load_leaderboards():
            self._leaderboard_by_crunch_target_id_and_leaderboard_definition_id = to_dict(
                self._database.competition.query_many_objects(Leaderboard),
                key=lambda row: (row["crunch_target_id"], row["definition_id"]),
            )

        def _load_positions():
            rows = self._database.competition.query_many_objects(Position)

            self._position_by_leaderboard_id = group_by(
                rows,
                key=lambda row: row["leaderboard_id"],
            )

        def _load_paid_checkpoint_payouts():
            self._payouts_by_competition_id = group_by(
                self._database.competition.query_many_objects(
                    Payout,
                    where="`type` = 'CHECKPOINT' AND `status` = 'PAID'",
                ),
                key=lambda row: row["competition_id"],
            )

            payout_recipient_columns = to_column_names(PayoutRecipient, table_name="payout_recipients")
            self._payout_recipients_by_payout_id = group_by(
                self._database.competition.query_many(
                    f"SELECT {payout_recipient_columns} FROM `payout_recipients` LEFT JOIN `payouts` ON `payouts`.`id` = `payout_recipients`.`payout_id` WHERE `type` = 'CHECKPOINT' AND `status` = 'PAID'",
                    type=PayoutRecipient,
                ),
                key=lambda row: row["payout_id"],
            )

        def _load_teams():
            teams = self._database.competition.query_many_objects(
                Team,
                where="NOT `deleted`",
            )

            team_members = self._database.competition.query_many_objects(
                TeamMember,
                where="`team_id` NOT IN (SELECT `id` FROM `teams` WHERE `deleted`)",  # TODO Prefer join?
            )

            self._teams_by_competition_id = group_by(
                teams,
                key=lambda row: row["competition_id"],
            )

            self._team_members_by_team_id = group_by(
                team_members,
                key=lambda row: row["team_id"],
            )

        def _load_title_leaderboards():
            self._title_leaderboard_by_competition_id_and_year = to_dict(
                self._database.competition.query_many_objects(TitleLeaderboard),
                key=lambda row: (row["competition_id"], row["year"]),
            )

        def _load_title_positions():
            self._title_positions_by_leaderboard_id = group_by(
                self._database.competition.query_many_objects(TitlePosition),
                key=lambda row: row["leaderboard_id"],
            )

        methods: List[Callable[[], None]] = [
            _load_competitions,
            _load_users,
            _load_leaderboard_definitions,
            _load_targets,
            _load_rounds,
            _load_phases,
            _load_crunches,
            _load_crunch_targets,
            _load_leaderboards,
            _load_positions,
            _load_paid_checkpoint_payouts,
            _load_teams,
            _load_title_leaderboards,
            _load_title_positions,
        ]

        for method in tqdm(methods, unit="method", miniters=1):
            name = method.__name__[6:]

            if only is not None and name not in only:
                continue

            self._logger.info(f"load: {name}")
            method()

        for key, value in vars(self).items():
            if key.startswith("_") and isinstance(value, (list, dict)):
                self._logger.info(f"len: {key}={len(value)}")  # type: ignore

    def find_all_competitions(self) -> List[Competition]:
        return self._competitions

    def find_competition_by_id(self, id: CompetitionId) -> Competition:
        return self._competition_by_id[id]

    def find_competition_by_name(self, name: CompetitionName) -> Competition:
        return self._competition_by_name[name]

    def find_user_by_id(self, id: UserId) -> User:
        return self._user_by_id[id]

    def find_user_by_login(self, login: str) -> User:
        return self._user_by_login[login]

    def find_default_leaderboard_definition(self, competition: Competition):
        return self._default_leaderboard_definition_by_competition_id[competition["id"]]

    def find_all_usable_targets(self, competition: Competition) -> List[Target]:
        return self._usable_targets_by_competition_id.get(competition["id"]) or []

    def find_all_rounds(self, competition: Competition) -> List[Round]:
        return self._rounds_by_competition_id.get(competition["id"]) or []

    def find_out_of_sample_phase(self, round: Round) -> Optional[Phase]:
        return self._out_of_sample_phase_by_round_id.get(round["id"])

    def find_published_crunch(self, phase: Phase) -> Optional[Crunch]:
        return self._published_crunch_by_phase_id.get(phase["id"])

    def find_crunch_target(self, crunch: Crunch, target: Target) -> CrunchTarget:
        return self._crunch_target_by_crunch_id_and_target_id[(crunch["id"], target["id"])]

    def find_leaderboard(self, crunch_target: CrunchTarget, leaderboard_definition: LeaderboardDefinition) -> Optional[Leaderboard]:
        return self._leaderboard_by_crunch_target_id_and_leaderboard_definition_id.get((crunch_target["id"], leaderboard_definition["id"]))

    def find_all_positions(self, leaderboard: Leaderboard) -> List[Position]:
        return self._position_by_leaderboard_id.get(leaderboard["id"]) or []

    def find_all_paid_checkpoint_payouts(self, competition: Competition) -> List[Payout]:
        return self._payouts_by_competition_id.get(competition["id"]) or []

    def find_all_payout_recipients(self, payout: Payout) -> List[PayoutRecipient]:
        return self._payout_recipients_by_payout_id.get(payout["id"]) or []

    def find_all_teams(self, competition: Competition) -> List[Team]:
        return self._teams_by_competition_id.get(competition["id"]) or []

    def find_all_team_members(self, team: Team) -> List[TeamMember]:
        return self._team_members_by_team_id.get(team["id"]) or []

    def find_all_title_leaderboards(self) -> List[TitleLeaderboard]:
        return list(self._title_leaderboard_by_competition_id_and_year.values())

    def create_title_leaderboard(self, body: TitleLeaderboardBody) -> TitleLeaderboard:
        id = self._database.competition.insert_object(
            to_table_name(TitleLeaderboard),
            body,
        )

        leaderboard: TitleLeaderboard = {
            "id": cast(TitleLeaderboardId, id),
            **body,
        }

        self._title_leaderboard_by_competition_id_and_year[(body["competition_id"], body["year"])] = leaderboard

        return leaderboard

    def delete_title_leaderboard_by_competition_and_year(self, competition: Competition, year: int):
        leaderboard = self._database.competition.query_first_object(
            TitleLeaderboard,
            where=f"`competition_id` = %s AND `year` = %s",
            params=(
                competition["id"],
                year,
            ),
        )

        if not leaderboard:
            return

        cache_key = (competition["id"], year)
        if cache_key in self._title_leaderboard_by_competition_id_and_year:
            del self._title_leaderboard_by_competition_id_and_year[cache_key]

        leaderboard_id = leaderboard["id"]
        if leaderboard_id in self._title_positions_by_leaderboard_id:
            del self._title_positions_by_leaderboard_id[leaderboard_id]

        self._database.competition.insert(
            f"""
                DELETE FROM
                    `{to_table_name(TitlePosition)}`
                WHERE
                    `leaderboard_id` = %s
            """,
            params=(
                leaderboard_id,
            )
        )

        self._database.competition.insert(
            f"""
                DELETE FROM
                    `{to_table_name(TitleLeaderboard)}`
                WHERE
                    `id` = %s
            """,
            params=(
                leaderboard_id,
            )
        )

    def find_all_title_positions_by_leaderboard(self, leaderboard: TitleLeaderboard) -> List[TitlePosition]:
        return self._title_positions_by_leaderboard_id.get(leaderboard["id"]) or []

    def create_title_position(self, body: TitlePositionBody) -> TitlePosition:
        id = self._database.competition.insert_object(
            to_table_name(TitlePosition),
            body,
        )

        position: TitlePosition = {
            "id": cast(TitlePositionId, id),
            **body,
        }

        leaderboard_id = position["leaderboard_id"]
        if leaderboard_id not in self._title_positions_by_leaderboard_id:
            self._title_positions_by_leaderboard_id[leaderboard_id] = []

        self._title_positions_by_leaderboard_id[leaderboard_id].append(position)

        return position

    def set_title_for_users(self, title: Title, user_ids: Set[UserId]) -> None:
        if not len(user_ids):
            return

        user_id_placeholders = ", ".join(["%s"] * len(user_ids))
        title_ordinal = get_args(Title).index(title) + 1

        self._database.competition.insert(
            f"""
                UPDATE
                    `{to_table_name(User)}`
                SET
                    `title` = %s
                WHERE
                    `id` IN ({user_id_placeholders})
                    AND `title` + 0 <= %s
            """,
            params=(
                title,
                *user_ids,
                title_ordinal,
            )
        )
