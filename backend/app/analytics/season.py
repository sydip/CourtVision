from __future__ import annotations

from typing import TypeVar

from app.analytics.efficiency import calculate_true_shooting
from app.analytics.per36 import calculate_per_36_line
from app.analytics.types import GameLog, SeasonSummaryInput

T = TypeVar("T")


def calculate_season_summary(
    player_id: int,
    season: str,
    game_logs: list[GameLog],
) -> SeasonSummaryInput:
    ordered = sorted(game_logs, key=lambda log: (log.game_date, log.game_id))
    games_played = len(ordered)
    total_minutes = sum(log.minutes or 0 for log in ordered)
    total_points = sum(log.points for log in ordered)
    total_rebounds = sum(log.rebounds for log in ordered)
    total_assists = sum(log.assists for log in ordered)
    total_turnovers = sum(log.turnovers for log in ordered)
    total_steals = sum(log.steals for log in ordered)
    total_blocks = sum(log.blocks for log in ordered)
    plus_minus_values = [log.plus_minus for log in ordered if log.plus_minus is not None]
    total_field_goals_made = sum(log.field_goals_made for log in ordered)
    total_field_goal_attempts = sum(log.field_goal_attempts for log in ordered)
    total_three_pointers_made = sum(log.three_pointers_made for log in ordered)
    total_three_point_attempts = sum(log.three_point_attempts for log in ordered)
    total_free_throw_attempts = sum(log.free_throw_attempts for log in ordered)
    per_36 = calculate_per_36_line(
        points=total_points,
        rebounds=total_rebounds,
        assists=total_assists,
        turnovers=total_turnovers,
        minutes=total_minutes,
    )

    return SeasonSummaryInput(
        player_id=player_id,
        season=season,
        position=_latest_non_empty([log.position for log in ordered]),
        team_id=_latest_non_empty([log.team_id for log in ordered]),
        games_played=games_played,
        minutes_per_game=_per_game(total_minutes, games_played),
        points_per_game=_per_game(total_points, games_played),
        rebounds_per_game=_per_game(total_rebounds, games_played),
        assists_per_game=_per_game(total_assists, games_played),
        turnovers_per_game=_per_game(total_turnovers, games_played),
        plus_minus_per_game=_mean_or_none(plus_minus_values),
        true_shooting_percentage=calculate_true_shooting(
            total_points,
            total_field_goal_attempts,
            total_free_throw_attempts,
        ),
        steals_per_game=_per_game(total_steals, games_played),
        blocks_per_game=_per_game(total_blocks, games_played),
        field_goal_percentage=_ratio_or_none(total_field_goals_made, total_field_goal_attempts),
        three_point_percentage=_ratio_or_none(
            total_three_pointers_made, total_three_point_attempts
        ),
        effective_field_goal_percentage=_effective_field_goal_percentage(
            total_field_goals_made,
            total_three_pointers_made,
            total_field_goal_attempts,
        ),
        points_per_36=per_36.points,
        rebounds_per_36=per_36.rebounds,
        assists_per_36=per_36.assists,
        turnovers_per_36=per_36.turnovers,
    )


def _per_game(value: float, games_played: int) -> float | None:
    if games_played == 0:
        return None
    return value / games_played


def _ratio_or_none(made: int, attempted: int) -> float | None:
    if attempted <= 0:
        return None
    return made / attempted


def _effective_field_goal_percentage(
    field_goals_made: int, three_pointers_made: int, field_goal_attempts: int
) -> float | None:
    if field_goal_attempts <= 0:
        return None
    return (field_goals_made + 0.5 * three_pointers_made) / field_goal_attempts


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _latest_non_empty(values: list[T | None]) -> T | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None
