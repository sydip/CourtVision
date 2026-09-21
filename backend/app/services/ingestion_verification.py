from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Game,
    PlayerGameStat,
    PlayerSeasonSummary,
    RosterMembership,
    StandingsSnapshot,
    TeamGameStat,
    TeamSeasonSummary,
)
from app.services.seasons import validate_season_slug


@dataclass(frozen=True)
class SeasonVerification:
    season: str
    complete: bool
    counts: dict[str, int]
    missing: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def verify_season(session: Session, season: str) -> SeasonVerification:
    validate_season_slug(season)
    models = {
        "games": Game,
        "player_game_stats": PlayerGameStat,
        "team_game_stats": TeamGameStat,
        "player_season_summaries": PlayerSeasonSummary,
        "team_season_summaries": TeamSeasonSummary,
        "standings": StandingsSnapshot,
        "rosters": RosterMembership,
    }
    counts = {name: _season_count(session, model, season) for name, model in models.items()}
    missing = [name for name, count in counts.items() if count == 0]
    return SeasonVerification(season=season, complete=not missing, counts=counts, missing=missing)


def _season_count(session: Session, model: Any, season: str) -> int:
    return (
        session.scalar(select(func.count()).select_from(model).where(model.season == season)) or 0
    )
