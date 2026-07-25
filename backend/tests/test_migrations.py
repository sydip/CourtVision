from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from app.core.config import get_settings
from app.db.session import normalize_database_url


def make_alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_initial_migration_upgrades_and_downgrades_clean_database(
    sqlite_database_url: str,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", sqlite_database_url)
    get_settings.cache_clear()
    config = make_alembic_config(sqlite_database_url)

    command.upgrade(config, "head")

    engine = create_engine(normalize_database_url(sqlite_database_url))
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert {
        "teams",
        "players",
        "games",
        "player_game_stats",
        "player_season_summaries",
        "sync_runs",
        "performance_reports",
        "playoff_series",
        "playoff_games",
        "playoff_team_box_scores",
        "playoff_player_box_scores",
    }.issubset(tables)

    command.downgrade(config, "base")

    engine = create_engine(normalize_database_url(sqlite_database_url))
    try:
        downgraded_tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert "players" not in downgraded_tables
    assert "player_game_stats" not in downgraded_tables
    get_settings.cache_clear()
