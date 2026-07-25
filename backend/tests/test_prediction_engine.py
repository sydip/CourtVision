from __future__ import annotations

import pytest

from app.analytics.awards_predictor import score_award_candidates
from app.analytics.prediction_types import (
    PlayerProjectionFeatures,
    TeamProjectionFeatures,
)
from app.analytics.rookie_predictor import RookieProjectionFeatures, score_rookie_candidates
from app.analytics.standings_predictor import score_standings


def test_mvp_projection_is_deterministic_and_explainable() -> None:
    candidates = [
        _player("Alpha Guard", 1, points=31, assists=9, plus_minus=7, team_strength=5),
        _player("Beta Wing", 2, points=27, rebounds=9, plus_minus=4, team_strength=3),
        _player("Gamma Center", 3, points=24, rebounds=13, plus_minus=2, team_strength=1),
    ]

    first = score_award_candidates(
        candidates,
        "MVP",
        target_season="2026-27",
        source_season="2025-26",
        limit=3,
    )
    second = score_award_candidates(
        candidates,
        "MVP",
        target_season="2026-27",
        source_season="2025-26",
        limit=3,
    )

    assert first.as_dict() == second.as_dict()
    assert first.candidates[0].name == "Alpha Guard"
    assert sum(candidate.probability for candidate in first.candidates) == pytest.approx(1)
    assert first.candidates[0].feature_attributions
    assert "not guarantees" in first.methodology


def test_sixth_man_filters_starters() -> None:
    starter = _player("Starter", 1, points=30, is_starter=True)
    reserve = _player("Reserve", 2, points=18, is_starter=False)

    result = score_award_candidates(
        [starter, reserve],
        "SIXTH_MAN",
        target_season="2025-26",
        source_season="2025-26",
    )

    assert [candidate.name for candidate in result.candidates] == ["Reserve"]
    assert result.candidates[0].probability == 1


def test_preseason_roy_projection_uses_draft_position_and_team_opportunity() -> None:
    result = score_rookie_candidates(
        [
            RookieProjectionFeatures(
                draft_pick_id=1,
                player_name="First Pick",
                school_country="College A",
                team_id=1,
                team_name="Open Roster",
                team_abbreviation="OPN",
                overall_pick=1,
                draft_position_value=1,
                roster_opportunity=0.9,
                same_team_opportunity=1,
            ),
            RookieProjectionFeatures(
                draft_pick_id=2,
                player_name="Second Pick",
                school_country="College B",
                team_id=2,
                team_name="Crowded Roster",
                team_abbreviation="CRD",
                overall_pick=2,
                draft_position_value=2**-0.5,
                roster_opportunity=0.1,
                same_team_opportunity=0.5,
            ),
            RookieProjectionFeatures(
                draft_pick_id=8,
                player_name="Eighth Pick",
                school_country="College C",
                team_id=3,
                team_name="Team Three",
                team_abbreviation="THR",
                overall_pick=8,
                draft_position_value=8**-0.5,
                roster_opportunity=1,
                same_team_opportunity=1,
            ),
        ],
        target_season="2026-27",
        source_season="2025-26",
        limit=3,
    )

    assert result.candidates[0].name == "First Pick"
    assert result.candidates[0].features["overall_pick"] == 1
    assert result.candidates[0].feature_attributions[0]["feature"] == "overall_pick"
    assert sum(candidate.probability for candidate in result.candidates) == pytest.approx(
        1,
        abs=0.000002,
    )
    assert "preseason roy estimate" in result.methodology.lower()


def test_standings_projection_maps_features_to_records() -> None:
    strong = _team("Strong Team", 1, plus_minus=6, production=27, true_shooting=0.62)
    average = _team("Average Team", 2, plus_minus=1, production=22, true_shooting=0.57)
    weak = _team("Weak Team", 3, plus_minus=-4, production=18, true_shooting=0.52)

    result = score_standings(
        [strong, average, weak],
        target_season="2026-27",
        source_season="2025-26",
        conference="West",
    )

    assert [team.team_name for team in result.teams] == [
        "Strong Team",
        "Average Team",
        "Weak Team",
    ]
    assert result.teams[0].projected_wins > result.teams[-1].projected_wins
    assert result.teams[0].projected_wins + result.teams[0].projected_losses == 82
    assert result.teams[0].factors[0]["feature"] == "weighted_plus_minus"


def _player(
    name: str,
    identifier: int,
    *,
    points: float,
    rebounds: float = 5,
    assists: float = 5,
    plus_minus: float = 1,
    team_strength: float = 1,
    is_starter: bool = True,
) -> PlayerProjectionFeatures:
    return PlayerProjectionFeatures(
        player_id=identifier,
        nba_player_id=identifier,
        player_name=name,
        team_id=identifier,
        team_name=f"Team {identifier}",
        team_abbreviation=f"T{identifier}",
        conference="West",
        position="G",
        source_season="2025-26",
        games_played=70,
        games_started=60 if is_starter else 5,
        minutes_per_game=34 if is_starter else 25,
        points_per_game=points,
        rebounds_per_game=rebounds,
        assists_per_game=assists,
        steals_per_game=1.2,
        blocks_per_game=0.5,
        turnovers_per_game=2.4,
        field_goal_percentage=0.48,
        three_point_percentage=0.39,
        free_throw_percentage=0.86,
        true_shooting_percentage=0.62,
        usage_rate=0.29,
        plus_minus_per_game=plus_minus,
        points_per_36=points * 36 / 34,
        rebounds_per_36=rebounds * 36 / 34,
        assists_per_36=assists * 36 / 34,
        minutes_trend=1.0,
        year_over_year_points_delta=2.0,
        year_over_year_minutes_delta=1.0,
        team_strength=team_strength,
        age=27,
        years_pro=6,
        health_factor=0.95,
        is_starter=is_starter,
        is_synthetic=False,
        data_source="test",
    )


def _team(
    name: str,
    identifier: int,
    *,
    plus_minus: float,
    production: float,
    true_shooting: float,
) -> TeamProjectionFeatures:
    return TeamProjectionFeatures(
        team_id=identifier,
        nba_team_id=identifier,
        team_name=name,
        abbreviation=f"T{identifier}",
        conference="West",
        division="Test",
        source_season="2025-26",
        roster_size=15,
        rotation_size=10,
        weighted_plus_minus=plus_minus,
        weighted_true_shooting=true_shooting,
        weighted_production=production,
        continuity=0.85,
        health_factor=0.95,
        is_synthetic=False,
        data_sources=["test"],
    )
