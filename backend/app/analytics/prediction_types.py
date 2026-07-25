from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlayerProjectionFeatures:
    player_id: int
    nba_player_id: int
    player_name: str
    team_id: int | None
    team_name: str | None
    team_abbreviation: str | None
    conference: str | None
    position: str | None
    source_season: str
    games_played: int
    games_started: int
    minutes_per_game: float
    points_per_game: float
    rebounds_per_game: float
    assists_per_game: float
    steals_per_game: float
    blocks_per_game: float
    turnovers_per_game: float
    field_goal_percentage: float
    three_point_percentage: float
    free_throw_percentage: float
    true_shooting_percentage: float
    usage_rate: float
    plus_minus_per_game: float
    points_per_36: float
    rebounds_per_36: float
    assists_per_36: float
    minutes_trend: float
    year_over_year_points_delta: float
    year_over_year_minutes_delta: float
    team_strength: float
    age: float | None
    years_pro: int | None
    health_factor: float
    is_starter: bool
    is_synthetic: bool
    data_source: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TeamProjectionFeatures:
    team_id: int
    nba_team_id: int
    team_name: str
    abbreviation: str
    conference: str | None
    division: str | None
    source_season: str
    roster_size: int
    rotation_size: int
    weighted_plus_minus: float
    weighted_true_shooting: float
    weighted_production: float
    continuity: float
    health_factor: float
    is_synthetic: bool
    data_sources: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RankedCandidate:
    rank: int
    entity_id: int
    name: str
    team: str | None
    position: str | None
    probability: float
    score: float
    features: dict[str, float]
    feature_attributions: list[dict[str, float | str]]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AwardPredictionResult:
    prediction_id: int | None
    award_type: str
    target_season: str
    source_season: str
    model_version: str
    candidates: list[RankedCandidate]
    warnings: list[str]
    methodology: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "award_type": self.award_type,
            "target_season": self.target_season,
            "source_season": self.source_season,
            "model_version": self.model_version,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "warnings": self.warnings,
            "methodology": self.methodology,
        }


@dataclass(frozen=True)
class ProjectedTeam:
    rank: int
    conference_rank: int | None
    team_id: int
    nba_team_id: int
    team_name: str
    abbreviation: str
    conference: str | None
    division: str | None
    projected_wins: int
    projected_losses: int
    projected_point_differential: float
    confidence: float
    factors: list[dict[str, float | str]]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StandingsPredictionResult:
    prediction_id: int | None
    target_season: str
    source_season: str
    conference: str | None
    model_version: str
    teams: list[ProjectedTeam]
    warnings: list[str]
    methodology: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "target_season": self.target_season,
            "source_season": self.source_season,
            "conference": self.conference,
            "model_version": self.model_version,
            "teams": [team.as_dict() for team in self.teams],
            "warnings": self.warnings,
            "methodology": self.methodology,
        }
