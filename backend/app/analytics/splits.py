from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date

from app.analytics.efficiency import calculate_true_shooting
from app.analytics.types import GameLog, RestCategory, SplitSummary


def parse_home_status(matchup: str) -> bool:
    normalized = f" {matchup.lower()} "
    return " vs. " in normalized or " vs " in normalized


def add_rest_days(game_logs: list[GameLog]) -> list[GameLog]:
    ordered = sorted(game_logs, key=lambda log: (log.player_id, log.game_date, log.game_id))
    previous_dates: dict[int, date] = {}
    with_rest: list[GameLog] = []
    for log in ordered:
        previous_date = previous_dates.get(log.player_id)
        rest_days = None if previous_date is None else (log.game_date - previous_date).days
        with_rest.append(replace(log, days_since_previous_game=rest_days))
        previous_dates[log.player_id] = log.game_date
    return with_rest


def categorize_rest_days(days_since_previous_game: int | None) -> RestCategory:
    if days_since_previous_game is None:
        return "first_game"
    if days_since_previous_game == 1:
        return "back_to_back"
    if days_since_previous_game == 2:
        return "one_day_rest"
    return "two_or_more_days_rest"


def calculate_home_away_splits(game_logs: list[GameLog]) -> dict[str, SplitSummary]:
    grouped: dict[str, list[GameLog]] = defaultdict(list)
    for log in game_logs:
        is_home = log.is_home
        if is_home is None and log.matchup is not None:
            is_home = parse_home_status(log.matchup)
        if is_home is None:
            continue
        grouped["home" if is_home else "away"].append(log)

    return {location: _summarize_split(logs) for location, logs in grouped.items()}


def _summarize_split(game_logs: list[GameLog]) -> SplitSummary:
    points = sum(log.points for log in game_logs)
    field_goal_attempts = sum(log.field_goal_attempts for log in game_logs)
    free_throw_attempts = sum(log.free_throw_attempts for log in game_logs)
    return SplitSummary(
        games=len(game_logs),
        minutes=sum(log.minutes or 0 for log in game_logs),
        points=points,
        rebounds=sum(log.rebounds for log in game_logs),
        assists=sum(log.assists for log in game_logs),
        true_shooting_percentage=calculate_true_shooting(
            points,
            field_goal_attempts,
            free_throw_attempts,
        ),
    )
