from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics.efficiency import CALCULATED_TRUE_SHOOTING_LABEL
from app.analytics.rebuild import rebuild_season_analytics
from app.analytics.types import BenchmarkConfig
from app.models import (
    Game,
    Player,
    PlayerGameStat,
    PlayerSeasonSummary,
    Team,
    TeamGameStat,
    TeamSeasonSummary,
)


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


def test_rebuild_isolates_seasons_and_builds_team_outputs(db_session: Session) -> None:
    team = Team(
        nba_team_id=1610612744,
        abbreviation="GSW",
        city="Golden State",
        name="Warriors",
        conference="West",
        division="Pacific",
    )
    player = Player(
        nba_player_id=201939,
        slug="stephen-curry-201939",
        full_name="Stephen Curry",
        position="G",
        team=team,
    )
    games = [
        Game(
            nba_game_id="0022100001",
            season="2021-22",
            game_date=date(2021, 10, 20),
            home_team=team,
            away_team=team,
            home_score=100,
            away_score=90,
        ),
        Game(
            nba_game_id="0022500099",
            season="2025-26",
            game_date=date(2025, 10, 20),
            home_team=team,
            away_team=team,
            home_score=120,
            away_score=100,
        ),
    ]
    db_session.add_all([team, player, *games])
    db_session.flush()
    for game, season, points in zip(games, ("2021-22", "2025-26"), (10, 30), strict=True):
        db_session.add(
            PlayerGameStat(
                player=player,
                game=game,
                team=team,
                season=season,
                minutes=Decimal("30"),
                points=points,
                rebounds=5,
                assists=6,
                steals=2,
                blocks=1,
                field_goals_made=4,
                field_goals_attempted=10,
                three_pointers_made=2,
                three_pointers_attempted=5,
                free_throws_made=0,
                free_throws_attempted=0,
            )
        )
        db_session.add(
            TeamGameStat(
                team=team,
                game=game,
                season=season,
                is_home=True,
                points=game.home_score or 0,
                opponent_points=game.away_score or 0,
                result="W",
                source="fixture",
            )
        )
    db_session.commit()

    config = BenchmarkConfig(minimum_games=1, minimum_minutes_per_game=1)
    rebuild_season_analytics(db_session, "2021-22", config)
    rebuild_season_analytics(db_session, "2025-26", config)
    db_session.commit()

    summaries = {
        summary.season: summary
        for summary in db_session.query(PlayerSeasonSummary).filter_by(player_id=player.id)
    }
    assert summaries["2021-22"].points_per_game == Decimal("10.00")
    assert summaries["2025-26"].points_per_game == Decimal("30.00")
    assert summaries["2021-22"].totals["points"] == 10
    assert summaries["2025-26"].rolling_averages[0]["points_rolling_5"] == 30.0
    assert summaries["2021-22"].effective_field_goal_percentage == Decimal("0.500")
    assert summaries["2021-22"].league_percentiles["points_per_game"] == 50.0
    assert summaries["2025-26"].league_percentiles["points_per_game"] == 50.0

    team_summaries = {
        summary.season: summary
        for summary in db_session.query(TeamSeasonSummary).filter_by(team_id=team.id)
    }
    assert team_summaries["2021-22"].points_per_game == Decimal("100.00")
    assert team_summaries["2025-26"].points_per_game == Decimal("120.00")
    assert team_summaries["2025-26"].leaders["points_per_game"]["player_id"] == player.id
