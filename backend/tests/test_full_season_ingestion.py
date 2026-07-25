from __future__ import annotations

from datetime import date
from decimal import Decimal

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
from app.ingestion.pipeline import ALL_INGESTION_STEPS, run_provider_ingestion
from app.models import Game, Player, PlayerGameStat, SyncRun, Team

SEASON = "2025-26"


class FullSeasonFixtureProvider:
    def get_teams(self) -> list[SourceTeam]:
        return [
            SourceTeam(
                nba_team_id=1610612744,
                abbreviation="GSW",
                city="Golden State",
                name="Warriors",
            ),
            SourceTeam(
                nba_team_id=1610612747,
                abbreviation="LAL",
                city="Los Angeles",
                name="Lakers",
            ),
        ]

    def get_players(self) -> list[SourcePlayer]:
        return [
            SourcePlayer(
                nba_player_id=201939,
                slug="stephen-curry-201939",
                full_name="Stephen Curry",
                first_name="Stephen",
                last_name="Curry",
                team_nba_id=1610612744,
            )
        ]

    def get_player_profiles(self) -> list[SourcePlayerProfile]:
        return [
            SourcePlayerProfile(
                nba_player_id=201939,
                height="6-2",
                weight_pounds=185,
                position="Guard",
            )
        ]

    def get_games(self) -> list[SourceGame]:
        return [
            SourceGame(
                nba_game_id="0022500001",
                season=SEASON,
                game_date=date(2025, 10, 21),
                home_team_nba_id=1610612744,
                away_team_nba_id=1610612747,
                home_score=121,
                away_score=118,
            ),
            SourceGame(
                nba_game_id="0022500002",
                season=SEASON,
                game_date=date(2025, 10, 24),
                home_team_nba_id=1610612747,
                away_team_nba_id=1610612744,
                home_score=110,
                away_score=104,
            ),
        ]

    def get_season_game_logs(self, season: str) -> list[SourcePlayerGameLog]:
        return [
            SourcePlayerGameLog(
                nba_player_id=201939,
                nba_game_id="0022500001",
                team_nba_id=1610612744,
                season=season,
                matchup="GSW vs. LAL",
                is_home=True,
                result="W",
                minutes=Decimal("31.50"),
                points=28,
                rebounds=4,
                assists=7,
                steals=1,
                blocks=0,
                turnovers=2,
                personal_fouls=3,
                field_goals_made=9,
                field_goals_attempted=18,
                three_pointers_made=5,
                three_pointers_attempted=11,
                free_throws_made=5,
                free_throws_attempted=5,
                plus_minus=Decimal("8"),
            ),
            SourcePlayerGameLog(
                nba_player_id=201939,
                nba_game_id="0022500002",
                team_nba_id=1610612744,
                season=season,
                matchup="GSW @ LAL",
                is_home=False,
                result="L",
                minutes=Decimal("29.00"),
                points=22,
                rebounds=3,
                assists=5,
                turnovers=4,
                personal_fouls=2,
                field_goals_made=8,
                field_goals_attempted=20,
                three_pointers_made=3,
                three_pointers_attempted=10,
                free_throws_made=3,
                free_throws_attempted=3,
                plus_minus=Decimal("-6"),
            ),
        ]

    def get_league_player_statistics(self, season: str) -> list[SourceLeaguePlayerStatistic]:
        return [
            SourceLeaguePlayerStatistic(
                nba_player_id=201939,
                team_nba_id=1610612744,
                season=season,
                games_played=2,
                minutes_per_game=Decimal("30.25"),
                points_per_game=Decimal("25.00"),
                rebounds_per_game=Decimal("3.50"),
                assists_per_game=Decimal("6.00"),
                true_shooting_percentage=Decimal("0.620"),
                usage_rate=Decimal("0.310"),
            )
        ]


def count_rows(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_full_season_ingestion_is_idempotent_and_calculates_rest_days(
    db_session: Session,
) -> None:
    provider = FullSeasonFixtureProvider()

    first_summary = run_provider_ingestion(
        db_session,
        provider,
        SEASON,
        source="test:full-season",
        steps=ALL_INGESTION_STEPS,
    )
    db_session.commit()
    second_summary = run_provider_ingestion(
        db_session,
        provider,
        SEASON,
        source="test:full-season",
        steps=ALL_INGESTION_STEPS,
    )
    db_session.commit()

    assert first_summary.inserted == 8
    assert first_summary.updated == 1
    assert second_summary.inserted == 0
    assert second_summary.updated == 0
    assert count_rows(db_session, Team) == 2
    assert count_rows(db_session, Player) == 1
    assert count_rows(db_session, Game) == 2
    assert count_rows(db_session, PlayerGameStat) == 2
    player = db_session.scalar(select(Player).where(Player.nba_player_id == 201939))
    assert player is not None
    assert player.position == "Guard"

    stats = db_session.scalars(select(PlayerGameStat).join(Game).order_by(Game.game_date)).all()
    assert stats[0].days_since_previous_game is None
    assert stats[1].days_since_previous_game == 3
    assert stats[0].is_home is True
    assert stats[1].is_home is False
    assert stats[0].result == "W"
    assert stats[1].result == "L"
    assert stats[0].personal_fouls == 3
    assert stats[1].personal_fouls == 2
    assert all(stat.player is not None for stat in stats)
    assert all(stat.game is not None for stat in stats)
    assert all(stat.team is not None for stat in stats)

    latest_sync = db_session.get(SyncRun, second_summary.sync_run_id)
    assert latest_sync is not None
    assert latest_sync.inserted_count == 0
    assert latest_sync.updated_count == 0
