from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    PlayerSeasonSummary,
    PredictionResult,
    PredictionRun,
    RosterMembership,
    StandingsSnapshot,
    Team,
)
from tests.test_models import make_player, make_team


def test_player_can_have_stats_in_multiple_seasons(db_session: Session) -> None:
    team = make_team()
    player = make_player(team)
    db_session.add_all(
        [
            PlayerSeasonSummary(player=player, team=team, season="2024-25", games_played=70),
            PlayerSeasonSummary(player=player, team=team, season="2025-26", games_played=72),
        ]
    )
    db_session.commit()

    summaries = db_session.scalars(
        select(PlayerSeasonSummary).where(PlayerSeasonSummary.player_id == player.id)
    ).all()
    assert {summary.season for summary in summaries} == {"2024-25", "2025-26"}


def test_team_can_have_standings_in_multiple_seasons(db_session: Session) -> None:
    team = make_team()
    db_session.add_all(
        [
            _standing(team, "2024-25", 48, 34),
            _standing(team, "2025-26", 51, 31),
        ]
    )
    db_session.commit()

    rows = db_session.scalars(
        select(StandingsSnapshot).where(StandingsSnapshot.team_id == team.id)
    ).all()
    assert [(row.season, row.wins) for row in rows] == [("2024-25", 48), ("2025-26", 51)]


def test_roster_membership_changes_by_season_and_team(db_session: Session) -> None:
    warriors = make_team()
    wolves = make_team(1610612750, "MIN")
    player = make_player(warriors)
    db_session.add_all(
        [
            RosterMembership(
                player=player,
                team=warriors,
                season="2024-25",
                roster_status="active",
                source="nba_api",
            ),
            RosterMembership(
                player=player,
                team=wolves,
                season="2025-26",
                roster_status="traded",
                start_date=date(2026, 2, 5),
                source="nba_api",
            ),
        ]
    )
    db_session.commit()

    rows = db_session.scalars(
        select(RosterMembership)
        .where(RosterMembership.player_id == player.id)
        .order_by(RosterMembership.season)
    ).all()
    assert [(row.season, row.team.abbreviation) for row in rows] == [
        ("2024-25", "GSW"),
        ("2025-26", "MIN"),
    ]


def test_prediction_results_are_isolated_from_historical_analytics(db_session: Session) -> None:
    team = make_team()
    player = make_player(team)
    historical = PlayerSeasonSummary(
        player=player,
        team=team,
        season="2025-26",
        games_played=72,
        points_per_game=Decimal("24.80"),
    )
    run = PredictionRun(
        season="2026-27",
        prediction_type="all_nba",
        model_name="courtvision-all-nba",
        model_version="1.0",
        training_seasons=["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"],
        feature_set_version="1.0",
        status="completed",
    )
    result = PredictionResult(
        prediction_run=run,
        season="2026-27",
        prediction_type="all_nba",
        entity_type="player",
        entity_id=1,
        predicted_rank=1,
        probability=Decimal("0.240000"),
        explanation_json={"label": "model estimate"},
    )
    db_session.add_all([historical, result])
    db_session.commit()

    assert result.prediction_run.season == "2026-27"
    assert historical.season == "2025-26"
    assert historical.points_per_game == Decimal("24.80")


def _standing(team: Team, season: str, wins: int, losses: int) -> StandingsSnapshot:
    return StandingsSnapshot(
        team=team,
        season=season,
        snapshot_type="final_regular_season",
        conference="West",
        rank=3,
        wins=wins,
        losses=losses,
        win_pct=Decimal(wins) / Decimal(wins + losses),
        source="nba_api",
    )
