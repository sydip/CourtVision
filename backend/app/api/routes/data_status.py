from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.data_status import get_data_status
from app.services.seasons import get_available_seasons, get_default_season, validate_season

router = APIRouter(tags=["data"])


class SyncRunStatusResponse(BaseModel):
    id: int
    source: str
    status: str
    finished_at: datetime | None
    fetched_count: int
    inserted_count: int
    updated_count: int
    rejected_count: int
    failed_count: int = 0
    error_message: str | None


class DataStatusResponse(BaseModel):
    current_season: str
    player_count: int
    game_count: int
    player_game_record_count: int
    season: str
    players: int
    teams: int
    games: int
    playerGameStats: int
    teamGameStats: int
    standingsAvailable: bool
    last_successful_sync: SyncRunStatusResponse | None
    last_failed_sync: SyncRunStatusResponse | None


@router.get("/data-status", response_model=DataStatusResponse)
async def data_status(
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> DataStatusResponse:
    settings = get_settings()
    try:
        selected = validate_season(season or settings.nba_season)
    except ValueError as exc:
        requested = season or get_default_season()
        raise HTTPException(
            status_code=400,
            detail=(
                f"Season {requested} is not available. Available seasons: "
                f"{', '.join(get_available_seasons())}."
            ),
        ) from exc
    status = get_data_status(session, selected)
    return DataStatusResponse(
        current_season=selected,
        player_count=status.player_count,
        game_count=status.game_count,
        player_game_record_count=status.player_game_record_count,
        season=selected,
        players=status.player_count,
        teams=status.team_count,
        games=status.game_count,
        playerGameStats=status.player_game_record_count,
        teamGameStats=status.team_game_record_count,
        standingsAvailable=status.standings_available,
        last_successful_sync=(
            SyncRunStatusResponse.model_validate(status.last_successful_sync, from_attributes=True)
            if status.last_successful_sync
            else None
        ),
        last_failed_sync=(
            SyncRunStatusResponse.model_validate(status.last_failed_sync, from_attributes=True)
            if status.last_failed_sync
            else None
        ),
    )
