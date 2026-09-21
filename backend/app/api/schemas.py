from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ApiError


class ApiMetadata(BaseModel):
    season: str
    dataFreshness: datetime | None
    source: str = "database"


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int
    next_offset: int | None
    previous_offset: int | None
    season: str | None = None
    dataFreshness: datetime | None = None
    source: str = "database"


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nba_team_id: int
    abbreviation: str
    city: str
    name: str
    conference: str | None
    division: str | None


class PlayerListItem(BaseModel):
    id: int
    nba_player_id: int
    slug: str
    full_name: str
    first_name: str | None
    last_name: str | None
    position: str | None
    jersey_number: str | None
    active: bool
    team: TeamResponse | None


class PlayerDetail(PlayerListItem):
    height: str | None
    weight_pounds: int | None
    birthdate: date | None
    meta: ApiMetadata | None = None


class PaginatedPlayersResponse(BaseModel):
    items: list[PlayerListItem]
    meta: PageMeta


class SeasonItemResponse(BaseModel):
    season: str
    displayName: str
    isCompleted: bool
    isCurrent: bool
    supportsPredictions: bool
    supportsJordanPredictions: bool


class SeasonsResponse(BaseModel):
    seasons: list[str]
    data: list[SeasonItemResponse] = Field(default_factory=list)


class PositionsResponse(BaseModel):
    positions: list[str]


class TeamsResponse(BaseModel):
    teams: list[TeamResponse]
    meta: ApiMetadata | None = None


class TeamSeasonSummaryApiResponse(BaseModel):
    team: TeamResponse
    season: str
    conference: str | None
    division: str | None
    wins: int | None
    losses: int | None
    win_pct: float | None
    conference_rank: int | None
    division_rank: int | None
    points_per_game: float | None
    points_allowed_per_game: float | None
    net_rating: float | None
    offensive_rating: float | None
    defensive_rating: float | None
    pace: float | None
    playoff_result: str | None
    meta: ApiMetadata


class RosterMemberResponse(BaseModel):
    player: PlayerListItem
    jersey_number: str | None
    position: str | None
    roster_status: str
    is_projected_starter: bool
    depth_order: int | None


class TeamRosterResponse(BaseModel):
    team: TeamResponse
    members: list[RosterMemberResponse]
    meta: ApiMetadata


class TeamDetailResponse(BaseModel):
    team: TeamResponse
    summary: TeamSeasonSummaryApiResponse | None
    meta: ApiMetadata


class StandingRowResponse(BaseModel):
    team: TeamResponse
    conference: str
    rank: int
    wins: int
    losses: int
    win_pct: float
    games_back: float | None
    conference_record: str | None
    division_record: str | None
    home_record: str | None
    away_record: str | None
    last_10: str | None
    streak: str | None


class StandingsResponse(BaseModel):
    standings: list[StandingRowResponse]
    meta: ApiMetadata


class DraftPickResponse(BaseModel):
    id: int
    draft_year: int
    round: int
    overall_pick: int
    player_name: str
    school_country: str
    team: TeamResponse
    transaction_note: str | None


class DraftResponse(BaseModel):
    draft_year: int
    event_dates: str
    venue: str
    location: str
    total_picks: int
    picks: list[DraftPickResponse]
    data_source: str


class PlayoffPlayerBoxScoreResponse(BaseModel):
    player_id: int | None
    player_name: str
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    field_goals_made: int
    field_goals_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int
    plus_minus: int | None


class PlayoffTeamBoxScoreResponse(BaseModel):
    team: TeamResponse
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    field_goals_made: int
    field_goals_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int
    players: list[PlayoffPlayerBoxScoreResponse]


class PlayoffGameResponse(BaseModel):
    id: int
    game_number: int
    home_team: TeamResponse
    away_team: TeamResponse
    home_score: int
    away_score: int
    overtime: bool
    data_note: str | None
    team_box_scores: list[PlayoffTeamBoxScoreResponse]


class PlayoffSeriesResponse(BaseModel):
    id: int
    conference: str
    winner: TeamResponse
    loser: TeamResponse
    winner_wins: int
    loser_wins: int
    games: list[PlayoffGameResponse]


class PlayoffRoundResponse(BaseModel):
    season: str
    round: str
    stored_series: int
    stored_games: int
    expected_games: int
    coverage_complete: bool
    data_source: str
    series: list[PlayoffSeriesResponse]


class PlayerSeasonSummaryResponse(BaseModel):
    player_id: int
    nba_player_id: int
    season: str
    games_played: int
    minutes_per_game: float | None
    points_per_game: float | None
    rebounds_per_game: float | None
    assists_per_game: float | None
    turnovers_per_game: float | None
    plus_minus_per_game: float | None
    true_shooting_percentage: float | None = Field(
        description="Calculated true-shooting percentage when true_shooting_source is set."
    )
    true_shooting_source: str | None
    usage_rate: float | None
    points_per_36: float | None
    rebounds_per_36: float | None
    assists_per_36: float | None
    turnovers_per_36: float | None
    analytics_rebuilt_at: datetime | None
    analytics_warnings: list[dict[str, Any]]
    meta: ApiMetadata | None = None


class PlayerSeasonSummariesResponse(BaseModel):
    items: list[PlayerSeasonSummaryResponse]


class GameLogItem(BaseModel):
    id: int
    game_id: int
    nba_game_id: str
    game_date: date
    season: str
    matchup: str | None
    location: str | None
    opponent: TeamResponse | None
    result: str | None
    days_since_previous_game: int | None
    minutes: float | None
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    personal_fouls: int
    field_goals_made: int
    field_goals_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int
    plus_minus: float | None
    calculated_true_shooting_percentage: float | None


class PaginatedGameLogsResponse(BaseModel):
    items: list[GameLogItem]
    meta: PageMeta


class TrendsResponse(BaseModel):
    player_id: int
    nba_player_id: int
    season: str
    production_trend: str | None
    production_trend_value: float | None
    efficiency_trend: str | None
    efficiency_trend_value: float | None
    payload: dict[str, Any]
    meta: ApiMetadata | None = None


class SplitResponse(BaseModel):
    games: int
    minutes: float
    points: int
    rebounds: int
    assists: int
    true_shooting_percentage: float | None


class PlayerSplitsResponse(BaseModel):
    player_id: int
    nba_player_id: int
    season: str
    home: SplitResponse | None
    away: SplitResponse | None
    meta: ApiMetadata | None = None


class BenchmarksResponse(BaseModel):
    player_id: int
    nba_player_id: int
    season: str
    league_percentiles: dict[str, Any]
    position_percentiles: dict[str, Any]
    minutes_tier_percentiles: dict[str, Any]
    analytics_warnings: list[dict[str, Any]]
    meta: ApiMetadata | None = None


class SimilarFeatureComparison(BaseModel):
    feature: str
    label: str
    unit: str
    player_value: float | None
    candidate_value: float | None
    difference: float | None


class SimilarPlayerResponse(BaseModel):
    player: PlayerListItem
    summary: PlayerSeasonSummaryResponse
    similarity_score: float = Field(
        ge=0,
        le=100,
        description=(
            "Cosine similarity of the standardized statistical feature vectors, mapped to 0-100. "
            "Higher means a more similar statistical profile, not an identical play style."
        ),
    )
    shared_position: bool
    minutes_difference: float | None
    shared_strengths: list[str] = Field(
        default_factory=list,
        description="Features where both players rate well above league average.",
    )
    largest_differences: list[str] = Field(
        default_factory=list,
        description="Features where the two standardized profiles diverge the most.",
    )
    feature_comparisons: list[SimilarFeatureComparison] = Field(default_factory=list)


class SimilarPlayersResponse(BaseModel):
    player_id: int
    nba_player_id: int
    season: str
    players: list[SimilarPlayerResponse]
    meta: ApiMetadata | None = None


class RecentWindowResponse(BaseModel):
    window: int
    games: int
    points: float | None
    rebounds: float | None
    assists: float | None
    minutes: float | None
    true_shooting_percentage: float | None
    turnovers: float | None
    plus_minus: float | None


class RestSplitsResponse(BaseModel):
    first_game: SplitResponse | None
    back_to_back: SplitResponse | None
    one_day_rest: SplitResponse | None
    two_or_more_days_rest: SplitResponse | None


class RollingTrendPointResponse(BaseModel):
    player_id: int
    nba_player_id: int
    game_id: int
    game_date: date
    points_rolling_5: float | None
    points_rolling_10: float | None
    assists_rolling_5: float | None
    assists_rolling_10: float | None
    true_shooting_percentage_rolling_5: float | None
    true_shooting_percentage_rolling_10: float | None


class CompareMetricResponse(BaseModel):
    key: str
    label: str
    category: str
    higher_is_better: bool
    player_a_value: float | None
    player_b_value: float | None
    winner: str | None = Field(description="player_a, player_b, tie, or null when unavailable.")


class ComparePlayerResponse(BaseModel):
    player: PlayerListItem
    summary: PlayerSeasonSummaryResponse
    trends: TrendsResponse
    splits: PlayerSplitsResponse
    benchmarks: BenchmarksResponse
    rest_splits: RestSplitsResponse
    recent_5: RecentWindowResponse
    recent_10: RecentWindowResponse
    rolling_trend: list[RollingTrendPointResponse]


class CompareResponse(BaseModel):
    season: str
    player_a: ComparePlayerResponse
    player_b: ComparePlayerResponse
    position_match: bool
    position_context: str
    category_winners: list[CompareMetricResponse]
    meta: ApiMetadata | None = None


class ReportSentenceResponse(BaseModel):
    text: str
    fields: list[str]


class ReportSectionResponse(BaseModel):
    key: str
    title: str
    sentences: list[ReportSentenceResponse]


class PlayerReportResponse(BaseModel):
    player: PlayerListItem
    season: str
    summary: PlayerSeasonSummaryResponse
    trends: TrendsResponse
    splits: PlayerSplitsResponse
    benchmarks: BenchmarksResponse
    sample_size_warnings: list[dict[str, Any]]
    sections: list[ReportSectionResponse]
    meta: ApiMetadata | None = None
