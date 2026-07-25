from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.data_status import get_data_status

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
    error_message: str | None


class DataStatusResponse(BaseModel):
    current_season: str
    player_count: int
    game_count: int
    player_game_record_count: int
    last_successful_sync: SyncRunStatusResponse | None
    last_failed_sync: SyncRunStatusResponse | None


@router.get("/data-status", response_model=DataStatusResponse)
async def data_status(session: Annotated[Session, Depends(get_db_session)]) -> DataStatusResponse:
    settings = get_settings()
    status = get_data_status(session, settings.nba_season)
    return DataStatusResponse.model_validate(status, from_attributes=True)
