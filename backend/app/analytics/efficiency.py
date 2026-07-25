from __future__ import annotations

CALCULATED_TRUE_SHOOTING_LABEL = "calculated_true_shooting_percentage"


def calculate_true_shooting(
    points: int,
    field_goal_attempts: int,
    free_throw_attempts: int,
) -> float | None:
    denominator = 2 * (field_goal_attempts + 0.44 * free_throw_attempts)
    if denominator == 0:
        return None
    return points / denominator


def calculate_field_goal_percentage(
    field_goals_made: int,
    field_goal_attempts: int,
) -> float | None:
    if field_goal_attempts == 0:
        return None
    return field_goals_made / field_goal_attempts


def calculate_turnover_rate(
    turnovers: int,
    field_goal_attempts: int,
    free_throw_attempts: int,
) -> float | None:
    denominator = field_goal_attempts + 0.44 * free_throw_attempts + turnovers
    if denominator == 0:
        return None
    return turnovers / denominator
