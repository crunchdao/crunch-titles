from typing import Dict, List

from crunch_titles._model import CompetitionName


class TitlesParameters:
    MERGED_COMPETITIONS: Dict[CompetitionName, List[CompetitionName]] = {}

    MINIMUM_PARTICIPATION_PERCENTAGE: float = 0.25

    MERGED_COMPETITION_CANDIDATES: List[CompetitionName] = [
        item
        for items in MERGED_COMPETITIONS.values()
        for item in items
    ]
