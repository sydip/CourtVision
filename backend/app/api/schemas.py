from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ApiError


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int
    next_offset: int | None
    previous_offset: int | None


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


class PaginatedPlayersResponse(BaseModel):
    items: list[PlayerListItem]
    meta: PageMeta


class SeasonsResponse(BaseModel):
    seasons: list[str]


class PositionsResponse(BaseModel):
    positions: list[str]


class TeamsResponse(BaseModel):
    teams: list[TeamResponse]


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


class BenchmarksResponse(BaseModel):
    player_id: int
    nba_player_id: int
    season: str
    league_percentiles: dict[str, Any]
    position_percentiles: dict[str, Any]
    minutes_tier_percentiles: dict[str, Any]
    analytics_warnings: list[dict[str, Any]]


class SimilarPlayerResponse(BaseModel):
    player: PlayerListItem
    summary: PlayerSeasonSummaryResponse
    similarity_score: float = Field(
        ge=0,
        le=100,
        description="Higher score means the player's stored season-summary stats are more similar.",
    )
    shared_position: bool
    minutes_difference: float | None


class SimilarPlayersResponse(BaseModel):
    player_id: int
    nba_player_id: int
    season: str
    players: list[SimilarPlayerResponse]


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
