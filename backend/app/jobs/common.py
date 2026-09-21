from __future__ import annotations

from app.core.config import get_settings
from app.data.providers import NbaApiProvider
from app.ingestion.historical import HistoricalProvider


def build_provider(season: str) -> HistoricalProvider:
    settings = get_settings()
    return HistoricalProvider(
        NbaApiProvider(
            season=season,
            raw_data_dir=settings.raw_data_dir,
            timeout_seconds=settings.api_request_timeout_seconds,
            player_limit=None,
        )
    )
