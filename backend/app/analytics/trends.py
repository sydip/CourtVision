from __future__ import annotations

import statistics
from collections.abc import Callable

from app.analytics.efficiency import (
    calculate_field_goal_percentage,
    calculate_true_shooting,
    calculate_turnover_rate,
)
from app.analytics.types import (
    GameLog,
    MetricTrendDetail,
    SampleSizeWarning,
    TrendClassification,
    TrendResult,
)

MetricExtractor = Callable[[GameLog], float | None]

PRODUCTION_METRICS: dict[str, tuple[MetricExtractor, int]] = {
    "points": (lambda log: float(log.points), 1),
    "rebounds": (lambda log: float(log.rebounds), 1),
    "assists": (lambda log: float(log.assists), 1),
    "minutes": (lambda log: log.minutes, 1),
}
EFFICIENCY_METRICS: dict[str, tuple[MetricExtractor, int]] = {
    "true_shooting_percentage": (
        lambda log: calculate_true_shooting(
            log.points,
            log.field_goal_attempts,
            log.free_throw_attempts,
        ),
        1,
    ),
    "turnover_rate": (
        lambda log: calculate_turnover_rate(
            log.turnovers,
            log.field_goal_attempts,
            log.free_throw_attempts,
        ),
        -1,
    ),
    "field_goal_percentage": (
        lambda log: calculate_field_goal_percentage(
            log.field_goals_made,
            log.field_goal_attempts,
        ),
        1,
    ),
}


def calculate_production_trend(game_logs: list[GameLog]) -> TrendResult:
    return _calculate_trend("production", game_logs, PRODUCTION_METRICS)


def calculate_efficiency_trend(game_logs: list[GameLog]) -> TrendResult:
    return _calculate_trend("efficiency", game_logs, EFFICIENCY_METRICS)


def _calculate_trend(
    group: str,
    game_logs: list[GameLog],
    metrics: dict[str, tuple[MetricExtractor, int]],
) -> TrendResult:
    ordered = sorted(game_logs, key=lambda log: (log.game_date, log.game_id))
    warnings: list[SampleSizeWarning] = []
    if len(ordered) < 10:
        warnings.append(
            SampleSizeWarning(
                code="trend_small_sample",
                message=(
                    "At least 10 games are required to compare recent five games to previous five."
                ),
                player_id=ordered[0].player_id if ordered else None,
            )
        )
        return TrendResult(
            group=group,
            classification="insufficient_sample",
            composite_standardized_change=None,
            details=[],
            warnings=warnings,
        )

    previous_5 = ordered[-10:-5]
    recent_5 = ordered[-5:]
    details: list[MetricTrendDetail] = []
    standardized_changes: list[float] = []

    for metric, (extractor, direction) in metrics.items():
        all_values = _clean_values([extractor(log) for log in ordered])
        previous_average = _mean_or_none(_clean_values([extractor(log) for log in previous_5]))
        recent_average = _mean_or_none(_clean_values([extractor(log) for log in recent_5]))
        difference = (
            None
            if previous_average is None or recent_average is None
            else recent_average - previous_average
        )
        standardized_change = _standardized_change(difference, all_values, direction)
        if standardized_change is not None:
            standardized_changes.append(standardized_change)
        details.append(
            MetricTrendDetail(
                metric=metric,
                recent_5_average=recent_average,
                previous_5_average=previous_average,
                difference=difference,
                standardized_change=standardized_change,
            )
        )

    if not standardized_changes:
        return TrendResult(
            group=group,
            classification="insufficient_sample",
            composite_standardized_change=None,
            details=details,
            warnings=[
                *warnings,
                SampleSizeWarning(
                    code="trend_no_metric_values",
                    message="No trend metrics had enough non-missing values.",
                    player_id=ordered[0].player_id,
                ),
            ],
        )

    composite = sum(standardized_changes) / len(standardized_changes)
    return TrendResult(
        group=group,
        classification=_classify_composite_change(composite),
        composite_standardized_change=composite,
        details=details,
        warnings=warnings,
    )


def _standardized_change(
    difference: float | None,
    values: list[float],
    direction: int,
) -> float | None:
    if difference is None or len(values) < 2:
        return None
    standard_deviation = statistics.pstdev(values)
    if standard_deviation == 0:
        return 0.0
    return (difference / standard_deviation) * direction


def _classify_composite_change(composite: float) -> TrendClassification:
    if composite >= 0.25:
        return "improving"
    if composite <= -0.25:
        return "declining"
    return "stable"


def _clean_values(values: list[float | None]) -> list[float]:
    return [value for value in values if value is not None]


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
