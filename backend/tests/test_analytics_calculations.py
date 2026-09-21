from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.analytics.benchmarks import calculate_benchmarks
from app.analytics.efficiency import (
    CALCULATED_TRUE_SHOOTING_LABEL,
    calculate_field_goal_percentage,
    calculate_true_shooting,
    calculate_turnover_rate,
)
from app.analytics.per36 import calculate_per_36, calculate_per_36_line
from app.analytics.rolling import calculate_rolling_averages
from app.analytics.season import calculate_season_summary
from app.analytics.splits import (
    add_rest_days,
    calculate_home_away_splits,
    categorize_rest_days,
    parse_home_status,
)
from app.analytics.trends import calculate_efficiency_trend, calculate_production_trend
from app.analytics.types import BenchmarkConfig, GameLog, SeasonSummaryInput


def make_log(
    game_number: int,
    *,
    player_id: int = 1,
    points: int | None = None,
    rebounds: int = 5,
    assists: int = 4,
    minutes: float = 30.0,
    turnovers: int = 2,
    fgm: int = 5,
    fga: int = 10,
    fta: int = 4,
    plus_minus: float | None = 1.0,
    matchup: str = "GSW vs. LAL",
) -> GameLog:
    return GameLog(
        player_id=player_id,
        game_id=game_number,
        game_date=date(2025, 10, 1) + timedelta(days=game_number),
        position="G",
        matchup=matchup,
        minutes=minutes,
        points=points if points is not None else game_number,
        rebounds=rebounds,
        assists=assists,
        turnovers=turnovers,
        field_goals_made=fgm,
        field_goal_attempts=fga,
        free_throw_attempts=fta,
        plus_minus=plus_minus,
    )


def test_true_shooting_is_calculated_and_handles_zero_attempts() -> None:
    assert CALCULATED_TRUE_SHOOTING_LABEL == "calculated_true_shooting_percentage"
    assert calculate_true_shooting(20, 10, 5) == pytest.approx(20 / (2 * (10 + 0.44 * 5)))
    assert calculate_true_shooting(0, 0, 0) is None


def test_efficiency_supporting_rates_handle_missing_denominators() -> None:
    assert calculate_field_goal_percentage(5, 10) == pytest.approx(0.5)
    assert calculate_field_goal_percentage(0, 0) is None
    assert calculate_turnover_rate(2, 10, 5) == pytest.approx(2 / (10 + 0.44 * 5 + 2))
    assert calculate_turnover_rate(0, 0, 0) is None


def test_per_36_calculations_handle_zero_minutes() -> None:
    assert calculate_per_36(18, 24) == pytest.approx(27)
    assert calculate_per_36(18, 0) is None
    line = calculate_per_36_line(points=18, rebounds=6, assists=4, turnovers=2, minutes=24)
    assert line.points == pytest.approx(27)
    assert line.rebounds == pytest.approx(9)
    assert line.assists == pytest.approx(6)
    assert line.turnovers == pytest.approx(3)


def test_rolling_averages_are_chronological_and_include_five_and_ten_game_windows() -> None:
    logs = [make_log(game_number) for game_number in range(10, 0, -1)]

    rolling = calculate_rolling_averages(logs)

    assert [row.game_log.game_id for row in rolling] == list(range(1, 11))
    assert rolling[4].values["points_rolling_5"] == pytest.approx(3)
    assert rolling[9].values["points_rolling_5"] == pytest.approx(8)
    assert rolling[9].values["points_rolling_10"] == pytest.approx(5.5)
    assert rolling[9].values["true_shooting_percentage_rolling_5"] is not None


def test_home_away_splits_and_rest_categories() -> None:
    logs = [
        make_log(1, points=20, matchup="GSW vs. LAL"),
        make_log(2, points=10, matchup="GSW @ LAL"),
        make_log(5, points=30, matchup="GSW @ DEN"),
    ]

    with_rest = add_rest_days(logs)
    splits = calculate_home_away_splits(with_rest)

    assert parse_home_status("GSW vs. LAL") is True
    assert parse_home_status("GSW @ LAL") is False
    assert categorize_rest_days(with_rest[0].days_since_previous_game) == "first_game"
    assert categorize_rest_days(with_rest[1].days_since_previous_game) == "back_to_back"
    assert categorize_rest_days(with_rest[2].days_since_previous_game) == "two_or_more_days_rest"
    assert splits["home"].games == 1
    assert splits["away"].games == 2
    assert splits["away"].points == 40


def test_trends_use_composite_groups_and_warn_on_small_samples() -> None:
    logs = [
        make_log(game_number, points=game_number, rebounds=game_number, assists=game_number)
        for game_number in range(1, 11)
    ]

    production = calculate_production_trend(logs)
    efficiency = calculate_efficiency_trend(logs)
    small_sample = calculate_production_trend(logs[:5])

    assert production.classification == "improving"
    assert production.composite_standardized_change is not None
    assert {detail.metric for detail in production.details} == {
        "points",
        "rebounds",
        "assists",
        "minutes",
    }
    assert efficiency.classification in {"improving", "stable", "declining"}
    assert small_sample.classification == "insufficient_sample"
    assert small_sample.warnings[0].code == "trend_small_sample"


def test_benchmarks_apply_thresholds_and_percentiles() -> None:
    summaries = [
        SeasonSummaryInput(1, "2025-26", "G", 1, 20, 30, 30, 5, 6, 2, 3, 0.60, 36, 6, 7, 2),
        SeasonSummaryInput(2, "2025-26", "G", 1, 20, 31, 20, 4, 4, 3, 1, 0.55, 24, 5, 5, 3),
        SeasonSummaryInput(3, "2025-26", "F", 1, 20, 34, 10, 8, 2, 1, 0, 0.50, 18, 9, 3, 1),
        SeasonSummaryInput(4, "2025-26", "G", 1, 5, 8, 40, 2, 2, 4, 0, 0.70, 40, 2, 2, 4),
    ]

    results = calculate_benchmarks(
        summaries,
        BenchmarkConfig(minimum_games=15, minimum_minutes_per_game=10),
    )

    assert results[1]["points_per_game"].league_percentile == pytest.approx(83.333333)
    assert results[1]["points_per_game"].position_percentile == pytest.approx(75)
    assert results[1]["points_per_game"].minutes_tier_percentile == pytest.approx(75)
    assert results[1]["plus_minus_per_game"].league_percentile == pytest.approx(83.333333)
    assert results[1]["points_per_36"].league_percentile == pytest.approx(83.333333)
    assert results[4]["points_per_game"].warnings[0].code == "minimum_games_not_met"


def test_season_summary_uses_aggregate_true_shooting() -> None:
    logs = [
        make_log(1, points=20, rebounds=6, assists=4, minutes=30, fga=10, fta=5),
        make_log(2, points=10, rebounds=4, assists=8, minutes=20, fga=5, fta=0),
    ]

    summary = calculate_season_summary(1, "2025-26", logs)

    assert summary.games_played == 2
    assert summary.minutes_per_game == pytest.approx(25)
    assert summary.points_per_game == pytest.approx(15)
    assert summary.rebounds_per_game == pytest.approx(5)
    assert summary.assists_per_game == pytest.approx(6)
    assert summary.true_shooting_percentage == pytest.approx(30 / (2 * (15 + 0.44 * 5)))
    assert summary.points_per_36 == pytest.approx(21.6)
    assert summary.rebounds_per_36 == pytest.approx(7.2)
    assert summary.assists_per_36 == pytest.approx(8.64)
    assert summary.effective_field_goal_percentage == pytest.approx(10 / 15)


def test_season_summary_aggregates_defense_and_shooting_rates() -> None:
    logs = [
        GameLog(
            player_id=1,
            game_id=1,
            game_date=date(2025, 10, 2),
            steals=2,
            blocks=1,
            field_goals_made=8,
            field_goal_attempts=16,
            three_pointers_made=3,
            three_point_attempts=6,
        ),
        GameLog(
            player_id=1,
            game_id=2,
            game_date=date(2025, 10, 4),
            steals=0,
            blocks=3,
            field_goals_made=4,
            field_goal_attempts=4,
            three_pointers_made=1,
            three_point_attempts=4,
        ),
    ]

    summary = calculate_season_summary(1, "2025-26", logs)

    assert summary.steals_per_game == pytest.approx(1.0)
    assert summary.blocks_per_game == pytest.approx(2.0)
    assert summary.field_goal_percentage == pytest.approx(12 / 20)
    assert summary.three_point_percentage == pytest.approx(4 / 10)


def test_benchmarks_include_defense_and_shooting_percentiles() -> None:
    summaries = [
        SeasonSummaryInput(
            player_id=1,
            season="2025-26",
            position="G",
            team_id=1,
            games_played=20,
            minutes_per_game=30,
            points_per_game=28,
            rebounds_per_game=5,
            assists_per_game=6,
            turnovers_per_game=2,
            plus_minus_per_game=3,
            true_shooting_percentage=0.60,
            field_goal_percentage=0.50,
            three_point_percentage=0.40,
            steals_per_game=1.5,
            blocks_per_game=0.8,
        ),
        SeasonSummaryInput(
            player_id=2,
            season="2025-26",
            position="G",
            team_id=1,
            games_played=20,
            minutes_per_game=30,
            points_per_game=18,
            rebounds_per_game=4,
            assists_per_game=4,
            turnovers_per_game=3,
            plus_minus_per_game=-1,
            true_shooting_percentage=0.52,
            field_goal_percentage=0.44,
            three_point_percentage=0.33,
            steals_per_game=0.6,
            blocks_per_game=0.2,
        ),
    ]

    results = calculate_benchmarks(summaries, BenchmarkConfig(minimum_games=1))

    assert results[1]["field_goal_percentage"].league_percentile == pytest.approx(75)
    assert results[1]["three_point_percentage"].league_percentile == pytest.approx(75)
    assert results[1]["steals_per_game"].league_percentile == pytest.approx(75)
    assert results[1]["blocks_per_game"].league_percentile == pytest.approx(75)
