from __future__ import annotations

from collections.abc import Callable

from app.analytics.types import (
    BenchmarkConfig,
    BenchmarkResult,
    SampleSizeWarning,
    SeasonSummaryInput,
)

SummaryMetric = Callable[[SeasonSummaryInput], float | None]

BENCHMARK_METRICS: dict[str, SummaryMetric] = {
    "points_per_game": lambda summary: summary.points_per_game,
    "rebounds_per_game": lambda summary: summary.rebounds_per_game,
    "assists_per_game": lambda summary: summary.assists_per_game,
    "minutes_per_game": lambda summary: summary.minutes_per_game,
    "plus_minus_per_game": lambda summary: summary.plus_minus_per_game,
    "true_shooting_percentage": lambda summary: summary.true_shooting_percentage,
    "field_goal_percentage": lambda summary: summary.field_goal_percentage,
    "three_point_percentage": lambda summary: summary.three_point_percentage,
    "effective_field_goal_percentage": lambda summary: summary.effective_field_goal_percentage,
    "steals_per_game": lambda summary: summary.steals_per_game,
    "blocks_per_game": lambda summary: summary.blocks_per_game,
    "turnovers_per_game": lambda summary: summary.turnovers_per_game,
    "points_per_36": lambda summary: summary.points_per_36,
    "rebounds_per_36": lambda summary: summary.rebounds_per_36,
    "assists_per_36": lambda summary: summary.assists_per_36,
    "turnovers_per_36": lambda summary: summary.turnovers_per_36,
}


def calculate_benchmarks(
    summaries: list[SeasonSummaryInput],
    config: BenchmarkConfig,
) -> dict[int, dict[str, BenchmarkResult]]:
    eligible = [summary for summary in summaries if _is_eligible(summary, config)]
    results: dict[int, dict[str, BenchmarkResult]] = {}
    for summary in summaries:
        player_results: dict[str, BenchmarkResult] = {}
        for metric, extractor in BENCHMARK_METRICS.items():
            value = extractor(summary)
            warnings = _warnings_for_summary(summary, config, metric)
            league_values = _metric_values(eligible, extractor)
            position_values = _metric_values(
                [
                    candidate
                    for candidate in eligible
                    if candidate.position is not None and candidate.position == summary.position
                ],
                extractor,
            )
            minutes_values = _metric_values(
                [
                    candidate
                    for candidate in eligible
                    if _same_minutes_tier(candidate, summary, config)
                ],
                extractor,
            )
            player_results[metric] = BenchmarkResult(
                player_id=summary.player_id,
                metric=metric,
                value=value,
                league_average=_mean_or_none(league_values),
                league_percentile=_percentile_rank(value, league_values),
                position_average=_mean_or_none(position_values),
                position_percentile=_percentile_rank(value, position_values),
                minutes_tier_average=_mean_or_none(minutes_values),
                minutes_tier_percentile=_percentile_rank(value, minutes_values),
                warnings=warnings,
            )
        results[summary.player_id] = player_results
    return results


def _is_eligible(summary: SeasonSummaryInput, config: BenchmarkConfig) -> bool:
    minutes_per_game = summary.minutes_per_game or 0
    return (
        summary.games_played >= config.minimum_games
        and minutes_per_game >= config.minimum_minutes_per_game
    )


def _warnings_for_summary(
    summary: SeasonSummaryInput,
    config: BenchmarkConfig,
    metric: str,
) -> list[SampleSizeWarning]:
    warnings: list[SampleSizeWarning] = []
    if summary.games_played < config.minimum_games:
        warnings.append(
            SampleSizeWarning(
                code="minimum_games_not_met",
                message=(
                    f"Player has {summary.games_played} games; "
                    f"{config.minimum_games} are required for benchmarks."
                ),
                player_id=summary.player_id,
                metric=metric,
            )
        )
    minutes_per_game = summary.minutes_per_game or 0
    if minutes_per_game < config.minimum_minutes_per_game:
        warnings.append(
            SampleSizeWarning(
                code="minimum_minutes_not_met",
                message=(
                    f"Player averages {minutes_per_game:.1f} minutes; "
                    f"{config.minimum_minutes_per_game:.1f} are required for benchmarks."
                ),
                player_id=summary.player_id,
                metric=metric,
            )
        )
    return warnings


def _same_minutes_tier(
    candidate: SeasonSummaryInput,
    selected: SeasonSummaryInput,
    config: BenchmarkConfig,
) -> bool:
    if candidate.minutes_per_game is None or selected.minutes_per_game is None:
        return False
    return (
        abs(candidate.minutes_per_game - selected.minutes_per_game)
        <= config.similar_minutes_tolerance
    )


def _metric_values(
    summaries: list[SeasonSummaryInput],
    extractor: SummaryMetric,
) -> list[float]:
    return [value for summary in summaries if (value := extractor(summary)) is not None]


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _percentile_rank(value: float | None, population: list[float]) -> float | None:
    if value is None or not population:
        return None
    below = sum(1 for candidate in population if candidate < value)
    equal = sum(1 for candidate in population if candidate == value)
    return ((below + 0.5 * equal) / len(population)) * 100
