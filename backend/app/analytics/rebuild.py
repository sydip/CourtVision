from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.benchmarks import calculate_benchmarks
from app.analytics.efficiency import CALCULATED_TRUE_SHOOTING_LABEL
from app.analytics.per36 import calculate_per_36_line
from app.analytics.rolling import calculate_rolling_averages
from app.analytics.season import calculate_season_summary
from app.analytics.splits import calculate_home_away_splits, calculate_rest_splits
from app.analytics.trends import calculate_efficiency_trend, calculate_production_trend
from app.analytics.types import (
    BenchmarkConfig,
    GameLog,
    SampleSizeWarning,
    SeasonSummaryInput,
    SplitSummary,
)
from app.models import (
    Game,
    Player,
    PlayerGameStat,
    PlayerSeasonSummary,
    StandingsSnapshot,
    Team,
    TeamGameStat,
    TeamSeasonSummary,
)


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
    team_game_counts = _load_team_game_counts(session, season)
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
        existing = existing_summaries.get(summary_input.player_id)
        warnings = _collect_warnings(
            summary_input.player_id, benchmark_results, production_trend, efficiency_trend
        )
        warnings.extend(
            _data_quality_warnings(
                summary_input.player_id,
                game_logs,
                existing,
                team_game_counts.get(summary_input.team_id or -1),
            )
        )
        warning_payloads.extend(asdict(warning) for warning in warnings)

        summary = existing
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

    _rebuild_team_analytics(session, season, summary_inputs)

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
        .where(PlayerGameStat.season == season, Game.season == season)
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


def _load_team_game_counts(session: Session, season: str) -> dict[int, int]:
    counts: dict[int, int] = {}
    for team_id in session.scalars(
        select(TeamGameStat.team_id).where(TeamGameStat.season == season)
    ):
        counts[team_id] = counts.get(team_id, 0) + 1
    return counts


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
        "steals_per_game": _decimal_or_none(summary.steals_per_game, "0.01"),
        "blocks_per_game": _decimal_or_none(summary.blocks_per_game, "0.01"),
        "plus_minus_per_game": _decimal_or_none(summary.plus_minus_per_game, "0.01"),
        "true_shooting_percentage": _decimal_or_none(summary.true_shooting_percentage, "0.001"),
        "true_shooting_source": CALCULATED_TRUE_SHOOTING_LABEL,
        "effective_field_goal_percentage": _decimal_or_none(
            summary.effective_field_goal_percentage, "0.001"
        ),
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
        "totals": _totals_payload(game_logs),
        "rolling_averages": _rolling_payload(game_logs),
        "split_payload": {
            "home_away": _split_payload(calculate_home_away_splits(game_logs)),
            "rest": _split_payload(calculate_rest_splits(game_logs)),
        },
        "similarity_vector": {
            metric: result.value
            for metric, result in benchmark_results.items()
            if result.value is not None
        },
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


def _data_quality_warnings(
    player_id: int,
    game_logs: list[GameLog],
    existing: PlayerSeasonSummary | None,
    expected_team_games: int | None,
) -> list[SampleSizeWarning]:
    warnings: list[SampleSizeWarning] = []
    if any(log.minutes is None for log in game_logs):
        warnings.append(
            SampleSizeWarning(
                "missing_minutes", "One or more games are missing minutes.", player_id
            )
        )
    if sum(log.field_goal_attempts for log in game_logs) == 0:
        warnings.append(
            SampleSizeWarning(
                "zero_shot_attempts", "No field-goal attempts are available.", player_id
            )
        )
    if existing is None or existing.usage_rate is None:
        warnings.append(SampleSizeWarning("missing_usage", "Usage rate is unavailable.", player_id))
    team_ids = {log.team_id for log in game_logs if log.team_id is not None}
    if len(team_ids) > 1:
        warnings.append(
            SampleSizeWarning("traded_mid_season", "Player represented multiple teams.", player_id)
        )
    if expected_team_games is not None and len(game_logs) < expected_team_games:
        warnings.append(
            SampleSizeWarning(
                "incomplete_game_logs",
                f"Player has {len(game_logs)} logs across {expected_team_games} stored team games.",
                player_id,
            )
        )
    return warnings


def _totals_payload(game_logs: list[GameLog]) -> dict[str, object]:
    metrics = (
        "minutes",
        "points",
        "rebounds",
        "assists",
        "steals",
        "blocks",
        "turnovers",
        "field_goals_made",
        "field_goal_attempts",
        "three_pointers_made",
        "three_point_attempts",
        "free_throws_made",
        "free_throw_attempts",
    )
    return {metric: sum((getattr(log, metric) or 0) for log in game_logs) for metric in metrics}


def _rolling_payload(game_logs: list[GameLog]) -> list[dict[str, object]]:
    return [
        {
            "game_id": row.game_log.game_id,
            "game_date": row.game_log.game_date.isoformat(),
            **row.values,
        }
        for row in calculate_rolling_averages(game_logs)
    ]


def _split_payload(splits: Mapping[str, SplitSummary]) -> dict[str, object]:
    return {name: asdict(value) for name, value in splits.items()}


def _rebuild_team_analytics(
    session: Session,
    season: str,
    player_summaries: list[SeasonSummaryInput],
) -> None:
    team_rows = session.scalars(select(Team).order_by(Team.id)).all()
    existing = {
        row.team_id: row
        for row in session.scalars(
            select(TeamSeasonSummary).where(TeamSeasonSummary.season == season)
        )
    }
    game_stats = session.scalars(select(TeamGameStat).where(TeamGameStat.season == season)).all()
    by_team: dict[int, list[TeamGameStat]] = {}
    for stat in game_stats:
        by_team.setdefault(stat.team_id, []).append(stat)
    for team in team_rows:
        stats = by_team.get(team.id, [])
        candidates = [summary for summary in player_summaries if summary.team_id == team.id]
        if not stats and not candidates and team.id not in existing:
            continue
        target = existing.get(team.id)
        if target is None:
            target = TeamSeasonSummary(
                team_id=team.id, season=season, data_source="analytics_rebuild", is_synthetic=False
            )
            session.add(target)
        wins = sum(stat.result.upper() == "W" for stat in stats)
        losses = sum(stat.result.upper() == "L" for stat in stats)
        target.conference = team.conference
        target.division = team.division
        if stats:
            target.wins = wins
            target.losses = losses
            target.win_pct = _decimal_or_none(wins / len(stats), "0.001")
            target.points_per_game = _decimal_or_none(
                sum(stat.points for stat in stats) / len(stats), "0.01"
            )
            target.points_allowed_per_game = _decimal_or_none(
                sum(stat.opponent_points for stat in stats) / len(stats), "0.01"
            )
            target.net_rating = _decimal_or_none(
                (sum(stat.points for stat in stats) - sum(stat.opponent_points for stat in stats))
                / len(stats),
                "0.01",
            )
        target.leaders = _team_leaders(candidates)
    session.flush()
    _refresh_standings(session, season)


def _team_leaders(summaries: list[SeasonSummaryInput]) -> dict[str, object]:
    leaders: dict[str, object] = {}
    for metric in (
        "points_per_game",
        "rebounds_per_game",
        "assists_per_game",
        "steals_per_game",
        "blocks_per_game",
    ):
        candidates = [summary for summary in summaries if getattr(summary, metric) is not None]
        if candidates:
            leader = max(
                candidates, key=lambda summary: (getattr(summary, metric) or 0, -summary.player_id)
            )
            leaders[metric] = {"player_id": leader.player_id, "value": getattr(leader, metric)}
    return leaders


def _refresh_standings(session: Session, season: str) -> None:
    summaries = session.scalars(
        select(TeamSeasonSummary).where(TeamSeasonSummary.season == season)
    ).all()
    existing = {
        row.team_id: row
        for row in session.scalars(
            select(StandingsSnapshot).where(
                StandingsSnapshot.season == season,
                StandingsSnapshot.snapshot_type == "current",
            )
        )
    }
    for conference in ("East", "West"):
        conference_rows = [
            row for row in summaries if row.conference in {conference, f"{conference}ern"}
        ]
        conference_rows.sort(key=lambda row: (-(row.win_pct or 0), -(row.wins or 0), row.team_id))
        for rank, summary in enumerate(conference_rows, 1):
            summary.conference_rank = rank
            snapshot = existing.get(summary.team_id)
            if snapshot is None:
                snapshot = StandingsSnapshot(
                    season=season,
                    snapshot_type="current",
                    conference=conference,
                    team_id=summary.team_id,
                    source="analytics_rebuild",
                )
                session.add(snapshot)
            snapshot.rank = rank
            snapshot.wins = summary.wins or 0
            snapshot.losses = summary.losses or 0
            snapshot.win_pct = summary.win_pct or Decimal("0")


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
