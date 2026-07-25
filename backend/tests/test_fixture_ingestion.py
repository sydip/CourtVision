from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.providers import FixtureProvider
from app.ingestion import run_fixture_ingestion
from app.models import Game, Player, PlayerGameStat, PlayerSeasonSummary, SyncRun, Team


def fixture_root() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "2025-26"


def count_rows(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_fixture_ingestion_populates_clean_database_and_records_rejections(
    db_session: Session,
    caplog,
) -> None:
    provider = FixtureProvider(fixture_root=fixture_root(), season="2025-26")

    summary = run_fixture_ingestion(db_session, provider, "2025-26")
    db_session.commit()

    assert summary.fetched == 24
    assert summary.inserted == 18
    assert summary.updated == 4
    assert summary.rejected == 2
    assert count_rows(db_session, Team) == 4
    assert count_rows(db_session, Player) == 4
    assert count_rows(db_session, Game) == 2
    assert count_rows(db_session, PlayerGameStat) == 4
    assert count_rows(db_session, PlayerSeasonSummary) == 4
    assert "Rejected player_game_log record 201939:0022500001" in caplog.text
    assert "Rejected league_player_statistic record 2544:2025-26" in caplog.text

    sync_run = db_session.get(SyncRun, summary.sync_run_id)
    assert sync_run is not None
    assert sync_run.status == "completed_with_rejections"
    assert sync_run.fetched_count == 24
    assert sync_run.inserted_count == 18
    assert sync_run.updated_count == 4
    assert sync_run.rejected_count == 2


def test_fixture_ingestion_is_idempotent(db_session: Session) -> None:
    provider = FixtureProvider(fixture_root=fixture_root(), season="2025-26")

    first_summary = run_fixture_ingestion(db_session, provider, "2025-26")
    db_session.commit()
    second_summary = run_fixture_ingestion(db_session, provider, "2025-26")
    db_session.commit()

    assert first_summary.inserted == 18
    assert second_summary.inserted == 0
    assert second_summary.updated == 0
    assert second_summary.rejected == 2
    assert count_rows(db_session, Team) == 4
    assert count_rows(db_session, Player) == 4
    assert count_rows(db_session, Game) == 2
    assert count_rows(db_session, PlayerGameStat) == 4
    assert count_rows(db_session, PlayerSeasonSummary) == 4
    assert count_rows(db_session, SyncRun) == 2

    latest_sync_run = db_session.get(SyncRun, second_summary.sync_run_id)
    assert latest_sync_run is not None
    assert latest_sync_run.fetched_count == 24
    assert latest_sync_run.inserted_count == 0
    assert latest_sync_run.updated_count == 0
    assert latest_sync_run.rejected_count == 2
