from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.main import create_app
from app.models import Game, Player, PlayerGameStat, SyncRun, Team


def test_data_status_endpoint_returns_counts_and_sync_history(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setenv("NBA_SEASON", "2025-26")
    get_settings.cache_clear()

    warriors = Team(
        nba_team_id=1610612744,
        abbreviation="GSW",
        city="Golden State",
        name="Warriors",
    )
    lakers = Team(
        nba_team_id=1610612747,
        abbreviation="LAL",
        city="Los Angeles",
        name="Lakers",
    )
    player = Player(
        nba_player_id=201939,
        slug="stephen-curry-201939",
        full_name="Stephen Curry",
        team=warriors,
    )
    game = Game(
        nba_game_id="0022500001",
        season="2025-26",
        game_date=date(2025, 10, 21),
        home_team=warriors,
        away_team=lakers,
    )
    stat = PlayerGameStat(player=player, game=game, team=warriors, season="2025-26", points=28)
    successful_sync = SyncRun(
        source="fixture",
        season="2025-26",
        status="completed",
        finished_at=datetime(2025, 10, 22, tzinfo=UTC),
        fetched_count=1,
        inserted_count=1,
    )
    failed_sync = SyncRun(
        source="nba_api:sync-season",
        season="2025-26",
        status="failed",
        finished_at=datetime(2025, 10, 23, tzinfo=UTC),
        error_message="timeout",
    )
    db_session.add_all([warriors, lakers, player, game, stat, successful_sync, failed_sync])
    db_session.commit()

    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.get("/api/data-status")

    assert response.status_code == 200
    body = response.json()
    assert body["current_season"] == "2025-26"
    assert body["player_count"] == 1
    assert body["game_count"] == 1
    assert body["player_game_record_count"] == 1
    assert body["last_successful_sync"]["source"] == "fixture"
    assert body["last_failed_sync"]["source"] == "nba_api:sync-season"
    assert body["last_failed_sync"]["error_message"] == "timeout"
    get_settings.cache_clear()
