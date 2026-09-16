from datetime import date as Date
from datetime import datetime as DateTime
from typing import Literal, NewType, Optional, TypedDict
from decimal import Decimal

from typing_extensions import ReadOnly, TypeAlias

UserId = NewType("UserId", int)
CompetitionId = NewType("CompetitionId", int)
CompetitionName = NewType("CompetitionName", str)
RoundId = NewType("RoundId", int)
LeaderboardId = NewType("LeaderboardId", int)
LeaderboardDefinitionId = NewType("LeaderboardDefinitionId", int)
PayoutId = NewType("PayoutId", int)
PhaseId = NewType("PhaseId", int)
PayoutRecipientId = NewType("PayoutRecipientId", int)
CrunchTargetId = NewType("CrunchTargetId", int)
TargetId = NewType("TargetId", int)
CrunchId = NewType("CrunchId", int)
TeamId = NewType("TeamId", int)


class User(TypedDict):
    id: ReadOnly[UserId]
    login: str


CompetitionMode: TypeAlias = Literal["OFFLINE", "REAL_TIME"]
CompetitionStatus: TypeAlias = Literal["PENDING", "OPEN", "CLOSED"]


class Competition(TypedDict):
    id: ReadOnly[CompetitionId]
    name: CompetitionName
    mode: CompetitionMode
    status: CompetitionStatus
    continuous: bool
    start: DateTime
    prize_pool_usd: int
    team_based: bool


class LeaderboardDefinition(TypedDict):
    id: ReadOnly[LeaderboardDefinitionId]
    competition_id: CompetitionId


class Target(TypedDict):
    id: ReadOnly[TargetId]
    competition_id: CompetitionId
    name: str
    virtual: bool


class Round(TypedDict):
    id: ReadOnly[RoundId]
    number: int
    competition_id: CompetitionId
    end: DateTime


PhaseType: TypeAlias = Literal["SUBMISSION", "OUT_OF_SAMPLE"]


class Phase(TypedDict):
    id: ReadOnly[PhaseId]
    round_id: RoundId
    type: PhaseType
    per_crunch_weight: float


class Crunch(TypedDict):
    id: ReadOnly[CrunchId]
    phase_id: PhaseId
    number: int
    end: DateTime


class CrunchTarget(TypedDict):
    id: ReadOnly[CrunchTargetId]
    target_id: TargetId
    crunch_id: CrunchId


class Leaderboard(TypedDict):
    id: ReadOnly[LeaderboardId]
    crunch_target_id: CrunchTargetId
    definition_id: LeaderboardDefinitionId
    size: int


class Position(TypedDict):
    leaderboard_id: LeaderboardId
    user_id: UserId
    team_id: Optional[TeamId]
    reward_rank: Optional[Decimal]


class Payout(TypedDict):
    competition_id: CompetitionId
    id: ReadOnly[PayoutId]
    granted: Decimal
    date: Date
    size: int


class PayoutRecipient(TypedDict):
    id: ReadOnly[PayoutRecipientId]
    payout_id: PayoutId
    user_id: UserId
    rank: int


Medal = Literal["NONE", "TOP_20_PERCENT", "TOP_10_PERCENT", "BRONZE", "SILVER", "GOLD"]


class TitlePositionBody(TypedDict):
    competition_id: CompetitionId
    year: int  # Not null, use zero
    user_id: UserId
    rank: int
    medal: Medal


class TitlePosition(TitlePositionBody):
    id: ReadOnly[int]


Title = Literal["NOVICE", "CRUNCHER", "CONTRIBUTOR", "RANKED", "EXPERT", "MASTER", "GRANDMASTER"]
