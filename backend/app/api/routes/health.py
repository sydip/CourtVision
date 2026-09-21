from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "courtvision-api"
    nba_season: str
    database_configured: bool
    raw_data_dir: str
    request_timeout_seconds: float
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        nba_season=settings.nba_season,
        database_configured=bool(settings.database_url),
        raw_data_dir=settings.raw_data_dir,
        request_timeout_seconds=settings.api_request_timeout_seconds,
    )
