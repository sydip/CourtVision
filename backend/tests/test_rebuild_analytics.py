from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics.efficiency import CALCULATED_TRUE_SHOOTING_LABEL
from app.analytics.rebuild import rebuild_season_analytics
from app.analytics.types import BenchmarkConfig
from app.models import Game, Player, PlayerGameStat, PlayerSeasonSummary, Team


def test_rebuild_analytics_updates_season_summaries_without_downloads(
    db_session: Session,
) -> None:
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
    curry = Player(
        nba_player_id=201939,
        slug="stephen-curry-201939",
        full_name="Stephen Curry",
        position="G",
        team=warriors,
    )
    james = Player(
        nba_player_id=2544,
        slug="lebron-james-2544",
        full_name="LeBron James",
        position="F",
        team=lakers,
    )
    game_one = Game(
        nba_game_id="0022500001",
        season="2025-26",
        game_date=date(2025, 10, 21),
        home_team=warriors,
        away_team=lakers,
    )
    game_two = Game(
        nba_game_id="0022500002",
        season="2025-26",
        game_date=date(2025, 10, 23),
        home_team=lakers,
        away_team=warriors,
    )
    db_session.add_all([warriors, lakers, curry, james, game_one, game_two])
    db_session.flush()
    db_session.add_all(
        [
            PlayerGameStat(
                player=curry,
                game=game_one,
                team=warriors,
                season="2025-26",
                minutes=Decimal("30"),
                points=20,
                rebounds=5,
                assists=8,
                turnovers=2,
                field_goals_made=7,
                field_goals_attempted=14,
                free_throws_made=4,
                free_throws_attempted=4,
                plus_minus=Decimal("5"),
            ),
            PlayerGameStat(
                player=curry,
                game=game_two,
                team=warriors,
                season="2025-26",
                minutes=Decimal("34"),
                points=30,
                rebounds=6,
                assists=7,
                turnovers=3,
                field_goals_made=10,
                field_goals_attempted=20,
                free_throws_made=6,
                free_throws_attempted=6,
                plus_minus=Decimal("8"),
            ),
            PlayerGameStat(
                player=james,
                game=game_one,
                team=lakers,
                season="2025-26",
                minutes=Decimal("32"),
                points=18,
                rebounds=7,
                assists=6,
                turnovers=2,
                field_goals_made=8,
                field_goals_attempted=16,
                free_throws_made=2,
                free_throws_attempted=2,
                plus_minus=Decimal("-5"),
            ),
        ]
    )
    db_session.commit()

    summary = rebuild_season_analytics(
        db_session,
        "2025-26",
        BenchmarkConfig(minimum_games=2, minimum_minutes_per_game=10),
    )
    db_session.commit()

    curry_summary = (
        db_session.query(PlayerSeasonSummary)
        .filter(PlayerSeasonSummary.player_id == curry.id)
        .one()
    )
    james_summary = (
        db_session.query(PlayerSeasonSummary)
        .filter(PlayerSeasonSummary.player_id == james.id)
        .one()
    )

    assert summary.players_processed == 2
    assert summary.summaries_created == 2
    assert curry_summary.games_played == 2
    assert curry_summary.points_per_game == Decimal("25.00")
    assert curry_summary.rebounds_per_game == Decimal("5.50")
    assert curry_summary.assists_per_game == Decimal("7.50")
    assert curry_summary.turnovers_per_game == Decimal("2.50")
    assert curry_summary.points_per_36 == Decimal("28.13")
    assert curry_summary.true_shooting_source == CALCULATED_TRUE_SHOOTING_LABEL
    assert curry_summary.league_percentiles is not None
    assert "points_per_game" in curry_summary.league_percentiles
    assert curry_summary.production_trend == "insufficient_sample"
    assert curry_summary.analytics_warnings is not None
    assert any(
        warning["code"] == "trend_small_sample" for warning in curry_summary.analytics_warnings
    )
    assert james_summary.analytics_warnings is not None
    assert any(
        warning["code"] == "minimum_games_not_met" for warning in james_summary.analytics_warnings
    )
