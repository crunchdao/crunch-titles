from typing import Dict, List, cast

from crunch_titles._model import CompetitionName


def _name(value: str):
    return cast(CompetitionName, value)


class TitlesParameters:
    MERGED_COMPETITIONS: Dict[CompetitionName, List[CompetitionName]] = {
        _name("structural-break"): [
            _name("structural-break-open-benchmark"),
        ],
    }

    MINIMUM_PARTICIPATION_PERCENTAGE: float = 0.25

    MERGED_COMPETITION_CANDIDATES: List[CompetitionName] = [
        item
        for items in MERGED_COMPETITIONS.values()
        for item in items
    ]
