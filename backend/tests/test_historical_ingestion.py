from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceTeam,
)
from app.db.session import get_db_session
from app.ingestion.historical import HistoricalProvider
from app.ingestion.pipeline import ALL_INGESTION_STEPS, run_provider_ingestion
from app.main import create_app
from app.models import (
    PlayerSeasonSummary,
    RosterMembership,
    StandingsSnapshot,
    TeamGameStat,
)
from app.services.data_status import get_data_status
from app.services.seasons import HISTORICAL_SEASONS


class SeasonFixtureProvider:
    def __init__(self, season: str) -> None:
        self.season = season
        self.start_year = int(season[:4])

    def get_teams(self) -> list[SourceTeam]:
        return [
            SourceTeam(
                nba_team_id=1,
                abbreviation="BOS",
                city="Boston",
                name="Celtics",
                conference="East",
            ),
            SourceTeam(
                nba_team_id=2,
                abbreviation="GSW",
                city="Golden State",
                name="Warriors",
                conference="West",
            ),
        ]

    def get_players(self) -> list[SourcePlayer]:
        return [
            SourcePlayer(
                nba_player_id=100,
                slug="historical-player-100",
                full_name="Historical Player",
                team_nba_id=1,
                position="G",
            )
        ]

    def get_player_profiles(self) -> list[SourcePlayerProfile]:
        return [SourcePlayerProfile(nba_player_id=100, position="G")]

    def get_games(self) -> list[SourceGame]:
        return [
            SourceGame(
                nba_game_id=f"{self.start_year}-game-1",
                season=self.season,
                game_date=date(self.start_year, 10, 20),
                home_team_nba_id=1,
                away_team_nba_id=2,
                home_score=100 + (self.start_year - 2021),
                away_score=95,
            )
        ]

    def get_season_game_logs(self, season: str) -> list[SourcePlayerGameLog]:
        return [
            SourcePlayerGameLog(
                nba_player_id=100,
                nba_game_id=f"{self.start_year}-game-1",
                team_nba_id=1,
                season=season,
                minutes=Decimal("30"),
                points=20 + (self.start_year - 2021),
                rebounds=5,
                assists=6,
                field_goals_made=8,
                field_goals_attempted=16,
            )
        ]

    def get_league_player_statistics(self, season: str) -> list[SourceLeaguePlayerStatistic]:
        return [
            SourceLeaguePlayerStatistic(
                nba_player_id=100,
                team_nba_id=1,
                season=season,
                games_played=1,
                points_per_game=Decimal(20 + (self.start_year - 2021)),
            )
        ]


def test_all_historical_seasons_ingest_without_cross_contamination(
    db_session: Session,
) -> None:
    for season in HISTORICAL_SEASONS:
        summary = run_provider_ingestion(
            db_session,
            HistoricalProvider(SeasonFixtureProvider(season)),
            season,
            source="fixture:historical",
            steps=ALL_INGESTION_STEPS,
        )
        assert summary.status == "completed"
        db_session.commit()

    summaries = db_session.scalars(
        select(PlayerSeasonSummary).order_by(PlayerSeasonSummary.season)
    ).all()
    assert [row.season for row in summaries] == list(HISTORICAL_SEASONS)
    assert summaries[0].points_per_game == Decimal("20.00")
    assert summaries[-1].points_per_game == Decimal("24.00")
    assert _count(db_session, StandingsSnapshot) == 10
    assert _count(db_session, TeamGameStat) == 10
    assert _count(db_session, RosterMembership) == 5

    for season in HISTORICAL_SEASONS:
        status = get_data_status(db_session, season)
        assert status.game_count == 1
        assert status.player_game_record_count == 1
        assert status.team_game_record_count == 2
        assert status.standings_available is True


def test_historical_ingestion_is_idempotent(db_session: Session) -> None:
    provider = HistoricalProvider(SeasonFixtureProvider("2021-22"))
    first = run_provider_ingestion(
        db_session, provider, "2021-22", source="fixture", steps=ALL_INGESTION_STEPS
    )
    db_session.commit()
    second = run_provider_ingestion(
        db_session, provider, "2021-22", source="fixture", steps=ALL_INGESTION_STEPS
    )
    db_session.commit()
    assert first.inserted > 0
    assert second.inserted == 0
    assert _count(db_session, TeamGameStat) == 2
    assert _count(db_session, StandingsSnapshot) == 2


def test_seasons_and_season_status_endpoints(db_session: Session) -> None:
    run_provider_ingestion(
        db_session,
        HistoricalProvider(SeasonFixtureProvider("2024-25")),
        "2024-25",
        source="fixture",
        steps=ALL_INGESTION_STEPS,
    )
    db_session.commit()
    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    seasons_response = client.get("/api/seasons")
    assert seasons_response.status_code == 200
    assert [row["season"] for row in seasons_response.json()["data"]] == list(HISTORICAL_SEASONS)
    status = client.get("/api/data-status?season=2024-25")
    assert status.status_code == 200
    assert status.json()["season"] == "2024-25"
    assert status.json()["teamGameStats"] == 2
    assert status.json()["standingsAvailable"] is True


def _count(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0
