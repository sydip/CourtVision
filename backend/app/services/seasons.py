from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    PlayerGameStat,
    PlayerSeasonSummary,
    RosterMembership,
    Season,
    StandingsSnapshot,
    TeamGameStat,
    TeamSeasonSummary,
)

HISTORICAL_SEASONS = ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26")
PREDICTION_SEASON = "2026-27"


@dataclass(frozen=True)
class SeasonInfo:
    season: str
    display_name: str
    is_completed: bool
    is_current: bool
    supports_predictions: bool
    supports_jordan_predictions: bool


def validate_season_slug(season: str, *, include_prediction: bool = False) -> str:
    allowed = HISTORICAL_SEASONS + ((PREDICTION_SEASON,) if include_prediction else ())
    if season not in allowed:
        raise ValueError(f"Unsupported season '{season}'. Expected one of: {', '.join(allowed)}")
    return season


def get_available_seasons() -> tuple[str, ...]:
    return HISTORICAL_SEASONS


def get_default_season() -> str:
    configured = get_settings().nba_season
    return configured if configured in HISTORICAL_SEASONS else "2025-26"


def validate_season(season: str | None) -> str:
    return validate_season_slug(season or get_default_season())


def player_has_season(session: Session, player_id: int, season: str) -> bool:
    summary = session.scalar(
        select(PlayerSeasonSummary.id).where(
            PlayerSeasonSummary.player_id == player_id,
            PlayerSeasonSummary.season == season,
        )
    )
    if summary is not None:
        return True
    return (
        session.scalar(
            select(PlayerGameStat.id).where(
                PlayerGameStat.player_id == player_id, PlayerGameStat.season == season
            )
        )
        is not None
        or session.scalar(
            select(RosterMembership.id).where(
                RosterMembership.player_id == player_id,
                RosterMembership.season == season,
            )
        )
        is not None
    )


def team_has_season(session: Session, team_id: int, season: str) -> bool:
    checks = (
        select(TeamSeasonSummary.id).where(
            TeamSeasonSummary.team_id == team_id, TeamSeasonSummary.season == season
        ),
        select(StandingsSnapshot.id).where(
            StandingsSnapshot.team_id == team_id, StandingsSnapshot.season == season
        ),
        select(TeamGameStat.id).where(
            TeamGameStat.team_id == team_id, TeamGameStat.season == season
        ),
        select(RosterMembership.id).where(
            RosterMembership.team_id == team_id, RosterMembership.season == season
        ),
    )
    return any(session.scalar(statement) is not None for statement in checks)


def season_range(from_season: str, to_season: str) -> tuple[str, ...]:
    validate_season_slug(from_season)
    validate_season_slug(to_season)
    start = HISTORICAL_SEASONS.index(from_season)
    end = HISTORICAL_SEASONS.index(to_season)
    if start > end:
        raise ValueError("from-season must not be later than to-season")
    return HISTORICAL_SEASONS[start : end + 1]


def list_seasons(session: Session) -> list[SeasonInfo]:
    rows = session.scalars(select(Season).order_by(Season.start_year)).all()
    stored = {
        row.slug: SeasonInfo(
                season=row.slug,
                display_name=row.display_name,
                is_completed=row.is_completed,
                is_current=row.is_current,
                supports_predictions=row.supports_predictions,
                supports_jordan_predictions=row.supports_jordan_predictions,
            )
        for row in rows
    }
    canonical = (*HISTORICAL_SEASONS, PREDICTION_SEASON)
    return [stored.get(season, _fallback_info(season)) for season in canonical]


def _fallback_info(season: str) -> SeasonInfo:
    return SeasonInfo(
        season=season,
        display_name=f"{season[:4]}\u2013{season[-2:]} Season",
        is_completed=season in HISTORICAL_SEASONS and season != "2025-26",
        is_current=season == "2025-26",
        supports_predictions=season == PREDICTION_SEASON,
        supports_jordan_predictions=season == "2025-26",
    )
