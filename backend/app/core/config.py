from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_DATABASE_URL = "postgresql://courtvision:courtvision_dev_password@localhost:5432/courtvision"
DEFAULT_NBA_SEASON = "2025-26"
DEFAULT_RAW_DATA_DIR = "../data/raw"
DEFAULT_API_REQUEST_TIMEOUT_SECONDS = 20.0
DEFAULT_BENCHMARK_MINIMUM_GAMES = 15
DEFAULT_BENCHMARK_MINIMUM_MINUTES_PER_GAME = 10.0
DEFAULT_BENCHMARK_SIMILAR_MINUTES_TOLERANCE = 3.0
DEFAULT_SIMILARITY_MINIMUM_GAMES = 15
DEFAULT_SIMILARITY_MINIMUM_MINUTES_PER_GAME = 10.0
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    nba_season: str
    raw_data_dir: str
    api_request_timeout_seconds: float
    benchmark_minimum_games: int
    benchmark_minimum_minutes_per_game: float
    benchmark_similar_minutes_tolerance: float
    similarity_minimum_games: int
    similarity_minimum_minutes_per_game: float
    anthropic_api_key: str | None
    anthropic_model: str


def _float_from_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return float(raw_value)


def _int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return int(raw_value)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        nba_season=os.getenv("NBA_SEASON", DEFAULT_NBA_SEASON),
        raw_data_dir=os.getenv("RAW_DATA_DIR", DEFAULT_RAW_DATA_DIR),
        api_request_timeout_seconds=_float_from_env(
            "API_REQUEST_TIMEOUT_SECONDS",
            DEFAULT_API_REQUEST_TIMEOUT_SECONDS,
        ),
        benchmark_minimum_games=_int_from_env(
            "BENCHMARK_MINIMUM_GAMES",
            DEFAULT_BENCHMARK_MINIMUM_GAMES,
        ),
        benchmark_minimum_minutes_per_game=_float_from_env(
            "BENCHMARK_MINIMUM_MINUTES_PER_GAME",
            DEFAULT_BENCHMARK_MINIMUM_MINUTES_PER_GAME,
        ),
        benchmark_similar_minutes_tolerance=_float_from_env(
            "BENCHMARK_SIMILAR_MINUTES_TOLERANCE",
            DEFAULT_BENCHMARK_SIMILAR_MINUTES_TOLERANCE,
        ),
        similarity_minimum_games=_int_from_env(
            "SIMILARITY_MINIMUM_GAMES",
            DEFAULT_SIMILARITY_MINIMUM_GAMES,
        ),
        similarity_minimum_minutes_per_game=_float_from_env(
            "SIMILARITY_MINIMUM_MINUTES_PER_GAME",
            DEFAULT_SIMILARITY_MINIMUM_MINUTES_PER_GAME,
        ),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL),
    )
