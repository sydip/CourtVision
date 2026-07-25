from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceTeam,
)
from app.ingestion.pipeline import run_provider_ingestion
from app.models import SyncRun, Team


class FailingProvider:
    def get_teams(self) -> list[SourceTeam]:
        raise RuntimeError("nba_api unavailable")

    def get_players(self) -> list[SourcePlayer]:
        return []

    def get_player_profiles(self) -> list[SourcePlayerProfile]:
        return []

    def get_games(self) -> list[SourceGame]:
        return []

    def get_season_game_logs(self, season: str) -> list[SourcePlayerGameLog]:
        return []

    def get_league_player_statistics(self, season: str) -> list[SourceLeaguePlayerStatistic]:
        return []


def test_provider_failure_does_not_delete_existing_database_data(db_session: Session) -> None:
    db_session.add(
        Team(
            nba_team_id=1610612744,
            abbreviation="GSW",
            city="Golden State",
            name="Warriors",
        )
    )
    db_session.commit()

    with pytest.raises(RuntimeError, match="nba_api unavailable"):
        run_provider_ingestion(
            db_session,
            FailingProvider(),
            "2025-26",
            source="nba_api:test",
            steps=("teams",),
        )
    db_session.rollback()

    teams = db_session.scalars(select(Team)).all()
    assert len(teams) == 1
    assert teams[0].abbreviation == "GSW"


def test_partial_failure_records_failed_sync_and_preserves_existing_rows(
    db_session: Session,
) -> None:
    db_session.add(
        Team(
            nba_team_id=1610612744,
            abbreviation="GSW",
            city="Golden State",
            name="Warriors",
        )
    )
    db_session.commit()

    summary = run_provider_ingestion(
        db_session,
        FailingProvider(),
        "2025-26",
        source="nba_api:test-failure",
        steps=("teams",),
        raise_on_failure=False,
    )
    db_session.commit()

    teams = db_session.scalars(select(Team)).all()
    failed_sync = db_session.get(SyncRun, summary.sync_run_id)
    assert len(teams) == 1
    assert teams[0].abbreviation == "GSW"
    assert summary.status == "failed"
    assert failed_sync is not None
    assert failed_sync.status == "failed"
    assert failed_sync.error_message == "nba_api unavailable"


def test_application_routes_do_not_import_live_nba_provider() -> None:
    route_root = Path("app/api/routes")
    route_text = "\n".join(path.read_text(encoding="utf-8") for path in route_root.glob("*.py"))

    assert "NbaApiProvider" not in route_text
    assert "nba_api" not in route_text
