from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.benchmarks import calculate_benchmarks
from app.analytics.efficiency import CALCULATED_TRUE_SHOOTING_LABEL
from app.analytics.per36 import calculate_per_36_line
from app.analytics.season import calculate_season_summary
from app.analytics.trends import calculate_efficiency_trend, calculate_production_trend
from app.analytics.types import BenchmarkConfig, GameLog, SampleSizeWarning, SeasonSummaryInput
from app.models import Game, Player, PlayerGameStat, PlayerSeasonSummary


@dataclass(frozen=True)
class RebuildAnalyticsSummary:
    season: str
    players_processed: int
    summaries_created: int
    summaries_updated: int
    warnings: list[dict[str, object]]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def rebuild_season_analytics(
    session: Session,
    season: str,
    config: BenchmarkConfig,
) -> RebuildAnalyticsSummary:
    logs_by_player = _load_game_logs(session, season)
    summary_inputs = [
        calculate_season_summary(player_id, season, game_logs)
        for player_id, game_logs in logs_by_player.items()
    ]
    benchmarks_by_player = calculate_benchmarks(summary_inputs, config)
    existing_summaries = {
        summary.player_id: summary
        for summary in session.scalars(
            select(PlayerSeasonSummary).where(PlayerSeasonSummary.season == season)
        )
    }

    created = 0
    updated = 0
    warning_payloads: list[dict[str, object]] = []
    rebuilt_at = datetime.now(UTC)

    for summary_input in summary_inputs:
        game_logs = logs_by_player[summary_input.player_id]
        production_trend = calculate_production_trend(game_logs)
        efficiency_trend = calculate_efficiency_trend(game_logs)
        benchmark_results = benchmarks_by_player[summary_input.player_id]
        warnings = _collect_warnings(
            summary_input.player_id, benchmark_results, production_trend, efficiency_trend
        )
        warning_payloads.extend(asdict(warning) for warning in warnings)

        summary = existing_summaries.get(summary_input.player_id)
        if summary is None:
            summary = PlayerSeasonSummary(
                player_id=summary_input.player_id,
                season=season,
            )
            session.add(summary)
            created += 1

        values = _summary_values(
            summary_input,
            game_logs,
            benchmark_results,
            production_trend,
            efficiency_trend,
            warnings,
            rebuilt_at,
        )
        if _apply_changes(summary, values):
            updated += 1

    if created or updated:
        session.flush()

    return RebuildAnalyticsSummary(
        season=season,
        players_processed=len(summary_inputs),
        summaries_created=created,
        summaries_updated=updated,
        warnings=warning_payloads,
    )


def _load_game_logs(session: Session, season: str) -> dict[int, list[GameLog]]:
    rows = session.execute(
        select(PlayerGameStat, Game, Player)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .join(Player, PlayerGameStat.player_id == Player.id)
        .where(PlayerGameStat.season == season)
        .order_by(PlayerGameStat.player_id, Game.game_date, Game.nba_game_id)
    ).all()
    logs_by_player: dict[int, list[GameLog]] = {}
    for stat, game, player in rows:
        logs_by_player.setdefault(player.id, []).append(
            GameLog(
                player_id=player.id,
                game_id=game.id,
                game_date=game.game_date,
                position=player.position,
                team_id=stat.team_id or player.team_id,
                matchup=stat.matchup,
                is_home=stat.is_home,
                days_since_previous_game=stat.days_since_previous_game,
                minutes=_float_or_none(stat.minutes),
                points=stat.points,
                rebounds=stat.rebounds,
                assists=stat.assists,
                steals=stat.steals,
                blocks=stat.blocks,
                turnovers=stat.turnovers,
                personal_fouls=stat.personal_fouls,
                field_goals_made=stat.field_goals_made,
                field_goal_attempts=stat.field_goals_attempted,
                three_pointers_made=stat.three_pointers_made,
                three_point_attempts=stat.three_pointers_attempted,
                free_throws_made=stat.free_throws_made,
                free_throw_attempts=stat.free_throws_attempted,
                plus_minus=_float_or_none(stat.plus_minus),
            )
        )
    return logs_by_player


def _summary_values(
    summary: SeasonSummaryInput,
    game_logs: list[GameLog],
    benchmark_results: dict[str, Any],
    production_trend: Any,
    efficiency_trend: Any,
    warnings: list[SampleSizeWarning],
    rebuilt_at: datetime,
) -> dict[str, object]:
    total_minutes = sum(log.minutes or 0 for log in game_logs)
    total_points = sum(log.points for log in game_logs)
    total_rebounds = sum(log.rebounds for log in game_logs)
    total_assists = sum(log.assists for log in game_logs)
    total_turnovers = sum(log.turnovers for log in game_logs)
    per_36 = calculate_per_36_line(
        points=total_points,
        rebounds=total_rebounds,
        assists=total_assists,
        turnovers=total_turnovers,
        minutes=total_minutes,
    )
    return {
        "team_id": summary.team_id,
        "games_played": summary.games_played,
        "minutes_per_game": _decimal_or_none(summary.minutes_per_game, "0.01"),
        "points_per_game": _decimal_or_none(summary.points_per_game, "0.01"),
        "rebounds_per_game": _decimal_or_none(summary.rebounds_per_game, "0.01"),
        "assists_per_game": _decimal_or_none(summary.assists_per_game, "0.01"),
        "turnovers_per_game": _decimal_or_none(summary.turnovers_per_game, "0.01"),
        "plus_minus_per_game": _decimal_or_none(summary.plus_minus_per_game, "0.01"),
        "true_shooting_percentage": _decimal_or_none(summary.true_shooting_percentage, "0.001"),
        "true_shooting_source": CALCULATED_TRUE_SHOOTING_LABEL,
        "points_per_36": _decimal_or_none(per_36.points, "0.01"),
        "rebounds_per_36": _decimal_or_none(per_36.rebounds, "0.01"),
        "assists_per_36": _decimal_or_none(per_36.assists, "0.01"),
        "turnovers_per_36": _decimal_or_none(per_36.turnovers, "0.01"),
        "league_percentiles": _percentile_payload(benchmark_results, "league_percentile"),
        "position_percentiles": _percentile_payload(benchmark_results, "position_percentile"),
        "minutes_tier_percentiles": _percentile_payload(
            benchmark_results,
            "minutes_tier_percentile",
        ),
        "production_trend": production_trend.classification,
        "production_trend_value": _decimal_or_none(
            production_trend.composite_standardized_change,
            "0.0001",
        ),
        "efficiency_trend": efficiency_trend.classification,
        "efficiency_trend_value": _decimal_or_none(
            efficiency_trend.composite_standardized_change,
            "0.0001",
        ),
        "trend_payload": {
            "production": _trend_payload(production_trend),
            "efficiency": _trend_payload(efficiency_trend),
        },
        "analytics_warnings": [asdict(warning) for warning in warnings],
        "analytics_rebuilt_at": rebuilt_at,
    }


def _collect_warnings(
    player_id: int,
    benchmark_results: dict[str, Any],
    production_trend: Any,
    efficiency_trend: Any,
) -> list[SampleSizeWarning]:
    warnings: list[SampleSizeWarning] = []
    seen: set[tuple[str, str, int | None, str | None]] = set()
    for result in benchmark_results.values():
        for warning in result.warnings:
            key = (warning.code, warning.message, warning.player_id, warning.metric)
            if key not in seen:
                warnings.append(warning)
                seen.add(key)
    for trend in (production_trend, efficiency_trend):
        for warning in trend.warnings:
            warning_with_player = (
                warning
                if warning.player_id is not None
                else SampleSizeWarning(
                    code=warning.code,
                    message=warning.message,
                    player_id=player_id,
                    metric=warning.metric,
                )
            )
            key = (
                warning_with_player.code,
                warning_with_player.message,
                warning_with_player.player_id,
                warning_with_player.metric,
            )
            if key not in seen:
                warnings.append(warning_with_player)
                seen.add(key)
    return warnings


def _percentile_payload(benchmark_results: dict[str, Any], field_name: str) -> dict[str, object]:
    return {
        metric: getattr(result, field_name)
        for metric, result in benchmark_results.items()
        if getattr(result, field_name) is not None
    }


def _trend_payload(trend: Any) -> dict[str, object]:
    return {
        "classification": trend.classification,
        "composite_standardized_change": trend.composite_standardized_change,
        "details": [asdict(detail) for detail in trend.details],
        "warnings": [asdict(warning) for warning in trend.warnings],
    }


def _float_or_none(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _decimal_or_none(value: float | None, quantum: str) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal(quantum), rounding=ROUND_HALF_UP)


def _apply_changes(instance: object, values: dict[str, object]) -> bool:
    changed = False
    for field_name, value in values.items():
        if getattr(instance, field_name) != value:
            setattr(instance, field_name, value)
            changed = True
    return changed
