from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

TrendClassification = Literal["improving", "stable", "declining", "insufficient_sample"]
RestCategory = Literal[
    "first_game",
    "back_to_back",
    "one_day_rest",
    "two_or_more_days_rest",
]


@dataclass(frozen=True)
class SampleSizeWarning:
    code: str
    message: str
    player_id: int | None = None
    metric: str | None = None


@dataclass(frozen=True)
class GameLog:
    player_id: int
    game_id: int
    game_date: date
    position: str | None = None
    team_id: int | None = None
    matchup: str | None = None
    is_home: bool | None = None
    days_since_previous_game: int | None = None
    minutes: float | None = None
    points: int = 0
    rebounds: int = 0
    assists: int = 0
    steals: int = 0
    blocks: int = 0
    turnovers: int = 0
    personal_fouls: int = 0
    field_goals_made: int = 0
    field_goal_attempts: int = 0
    three_pointers_made: int = 0
    three_point_attempts: int = 0
    free_throws_made: int = 0
    free_throw_attempts: int = 0
    plus_minus: float | None = None


@dataclass(frozen=True)
class RollingGameLog:
    game_log: GameLog
    values: dict[str, float | None]


@dataclass(frozen=True)
class SplitSummary:
    games: int
    minutes: float
    points: int
    rebounds: int
    assists: int
    true_shooting_percentage: float | None


@dataclass(frozen=True)
class MetricTrendDetail:
    metric: str
    recent_5_average: float | None
    previous_5_average: float | None
    difference: float | None
    standardized_change: float | None


@dataclass(frozen=True)
class TrendResult:
    group: str
    classification: TrendClassification
    composite_standardized_change: float | None
    details: list[MetricTrendDetail]
    warnings: list[SampleSizeWarning] = field(default_factory=list)


@dataclass(frozen=True)
class SeasonSummaryInput:
    player_id: int
    season: str
    position: str | None
    team_id: int | None
    games_played: int
    minutes_per_game: float | None
    points_per_game: float | None
    rebounds_per_game: float | None
    assists_per_game: float | None
    turnovers_per_game: float | None
    plus_minus_per_game: float | None
    true_shooting_percentage: float | None
    points_per_36: float | None = None
    rebounds_per_36: float | None = None
    assists_per_36: float | None = None
    turnovers_per_36: float | None = None
    steals_per_game: float | None = None
    blocks_per_game: float | None = None
    field_goal_percentage: float | None = None
    three_point_percentage: float | None = None
    effective_field_goal_percentage: float | None = None


@dataclass(frozen=True)
class BenchmarkConfig:
    minimum_games: int = 15
    minimum_minutes_per_game: float = 10.0
    similar_minutes_tolerance: float = 3.0


@dataclass(frozen=True)
class BenchmarkResult:
    player_id: int
    metric: str
    value: float | None
    league_average: float | None
    league_percentile: float | None
    position_average: float | None
    position_percentile: float | None
    minutes_tier_average: float | None
    minutes_tier_percentile: float | None
    warnings: list[SampleSizeWarning] = field(default_factory=list)
