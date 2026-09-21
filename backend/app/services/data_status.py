from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Game, Player, PlayerGameStat, StandingsSnapshot, SyncRun, Team, TeamGameStat

SUCCESS_STATUSES = ("completed", "completed_with_rejections")


@dataclass(frozen=True)
class SyncRunStatus:
    id: int
    source: str
    status: str
    finished_at: datetime | None
    fetched_count: int
    inserted_count: int
    updated_count: int
    rejected_count: int
    failed_count: int
    error_message: str | None


@dataclass(frozen=True)
class DataStatus:
    current_season: str
    player_count: int
    game_count: int
    player_game_record_count: int
    team_count: int
    team_game_record_count: int
    standings_available: bool
    last_successful_sync: SyncRunStatus | None
    last_failed_sync: SyncRunStatus | None


def get_data_status(session: Session, season: str) -> DataStatus:
    player_count = session.scalar(select(func.count()).select_from(Player)) or 0
    game_count = (
        session.scalar(select(func.count()).select_from(Game).where(Game.season == season)) or 0
    )
    player_game_record_count = (
        session.scalar(
            select(func.count()).select_from(PlayerGameStat).where(PlayerGameStat.season == season)
        )
        or 0
    )
    team_count = session.scalar(select(func.count()).select_from(Team)) or 0
    team_game_record_count = (
        session.scalar(
            select(func.count()).select_from(TeamGameStat).where(TeamGameStat.season == season)
        )
        or 0
    )
    standings_available = bool(
        session.scalar(
            select(func.count())
            .select_from(StandingsSnapshot)
            .where(StandingsSnapshot.season == season)
        )
    )
    return DataStatus(
        current_season=season,
        player_count=player_count,
        game_count=game_count,
        player_game_record_count=player_game_record_count,
        team_count=team_count,
        team_game_record_count=team_game_record_count,
        standings_available=standings_available,
        last_successful_sync=_latest_sync(session, season, SUCCESS_STATUSES),
        last_failed_sync=_latest_sync(session, season, ("failed",)),
    )


def _latest_sync(
    session: Session,
    season: str,
    statuses: tuple[str, ...],
) -> SyncRunStatus | None:
    sync_run = session.scalar(
        select(SyncRun)
        .where(SyncRun.season == season, SyncRun.status.in_(statuses))
        .order_by(SyncRun.finished_at.desc().nullslast(), SyncRun.id.desc())
        .limit(1)
    )
    if sync_run is None:
        return None
    return SyncRunStatus(
        id=sync_run.id,
        source=sync_run.source,
        status=sync_run.status,
        finished_at=sync_run.finished_at,
        fetched_count=sync_run.fetched_count,
        inserted_count=sync_run.inserted_count,
        updated_count=sync_run.updated_count,
        rejected_count=sync_run.rejected_count,
        failed_count=sync_run.failed_count,
        error_message=sync_run.error_message,
    )
