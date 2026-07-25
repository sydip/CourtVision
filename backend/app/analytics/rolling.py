from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable

from app.analytics.efficiency import calculate_true_shooting
from app.analytics.types import GameLog, RollingGameLog

ROLLING_METRICS: dict[str, Callable[[GameLog], float | None]] = {
    "points": lambda log: float(log.points),
    "rebounds": lambda log: float(log.rebounds),
    "assists": lambda log: float(log.assists),
    "minutes": lambda log: log.minutes,
    "true_shooting_percentage": lambda log: calculate_true_shooting(
        log.points,
        log.field_goal_attempts,
        log.free_throw_attempts,
    ),
    "turnovers": lambda log: float(log.turnovers),
    "plus_minus": lambda log: log.plus_minus,
}


def calculate_rolling_averages(
    game_logs: list[GameLog],
    *,
    windows: tuple[int, ...] = (5, 10),
) -> list[RollingGameLog]:
    ordered = sorted(game_logs, key=lambda log: (log.player_id, log.game_date, log.game_id))
    grouped: dict[int, list[GameLog]] = defaultdict(list)
    for log in ordered:
        grouped[log.player_id].append(log)

    output: list[RollingGameLog] = []
    for player_logs in grouped.values():
        output.extend(_calculate_player_rolling_averages(player_logs, windows))
    return output


def _calculate_player_rolling_averages(
    game_logs: list[GameLog],
    windows: tuple[int, ...],
) -> list[RollingGameLog]:
    metric_windows: dict[tuple[str, int], deque[float | None]] = {
        (metric, window): deque(maxlen=window) for metric in ROLLING_METRICS for window in windows
    }
    rows: list[RollingGameLog] = []
    for log in game_logs:
        values: dict[str, float | None] = {}
        for metric, extractor in ROLLING_METRICS.items():
            value = extractor(log)
            for window in windows:
                rolling_values = metric_windows[(metric, window)]
                rolling_values.append(value)
                values[f"{metric}_rolling_{window}"] = _mean_skip_none(list(rolling_values))
        rows.append(RollingGameLog(game_log=log, values=values))
    return rows


def _mean_skip_none(values: list[float | None]) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return sum(clean_values) / len(clean_values)
