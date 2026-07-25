import { z } from "zod";

export const healthSchema = z.object({
  status: z.string(),
  service: z.string(),
  nba_season: z.string(),
  database_configured: z.boolean(),
  raw_data_dir: z.string(),
  request_timeout_seconds: z.number(),
  checked_at: z.string(),
});

export const pageMetaSchema = z.object({
  limit: z.number(),
  offset: z.number(),
  total: z.number(),
  next_offset: z.number().nullable(),
  previous_offset: z.number().nullable(),
});

export const teamSchema = z.object({
  id: z.number(),
  nba_team_id: z.number(),
  abbreviation: z.string(),
  city: z.string(),
  name: z.string(),
  conference: z.string().nullable(),
  division: z.string().nullable(),
});

export const teamsResponseSchema = z.object({
  teams: z.array(teamSchema),
});

export const draftPickSchema = z.object({
  id: z.number(),
  draft_year: z.number(),
  round: z.number(),
  overall_pick: z.number(),
  player_name: z.string(),
  school_country: z.string(),
  team: teamSchema,
  transaction_note: z.string().nullable(),
});

export const draftResponseSchema = z.object({
  draft_year: z.number(),
  event_dates: z.string(),
  venue: z.string(),
  location: z.string(),
  total_picks: z.number(),
  picks: z.array(draftPickSchema),
  data_source: z.string(),
});

export const playoffPlayerBoxScoreSchema = z.object({
  player_id: z.number().nullable(),
  player_name: z.string(),
  points: z.number(),
  rebounds: z.number(),
  assists: z.number(),
  steals: z.number(),
  blocks: z.number(),
  turnovers: z.number(),
  field_goals_made: z.number(),
  field_goals_attempted: z.number(),
  three_pointers_made: z.number(),
  three_pointers_attempted: z.number(),
  free_throws_made: z.number(),
  free_throws_attempted: z.number(),
  plus_minus: z.number().nullable(),
});

export const playoffTeamBoxScoreSchema = z.object({
  team: teamSchema,
  points: z.number(),
  rebounds: z.number(),
  assists: z.number(),
  steals: z.number(),
  blocks: z.number(),
  turnovers: z.number(),
  field_goals_made: z.number(),
  field_goals_attempted: z.number(),
  three_pointers_made: z.number(),
  three_pointers_attempted: z.number(),
  free_throws_made: z.number(),
  free_throws_attempted: z.number(),
  players: z.array(playoffPlayerBoxScoreSchema),
});

export const playoffGameSchema = z.object({
  id: z.number(),
  game_number: z.number(),
  home_team: teamSchema,
  away_team: teamSchema,
  home_score: z.number(),
  away_score: z.number(),
  overtime: z.boolean(),
  data_note: z.string().nullable(),
  team_box_scores: z.array(playoffTeamBoxScoreSchema),
});

export const playoffRoundResponseSchema = z.object({
  season: z.string(),
  round: z.string(),
  stored_series: z.number(),
  stored_games: z.number(),
  expected_games: z.number(),
  coverage_complete: z.boolean(),
  data_source: z.string(),
  series: z.array(
    z.object({
      id: z.number(),
      conference: z.string(),
      winner: teamSchema,
      loser: teamSchema,
      winner_wins: z.number(),
      loser_wins: z.number(),
      games: z.array(playoffGameSchema),
    }),
  ),
});

export const playerListItemSchema = z.object({
  id: z.number(),
  nba_player_id: z.number(),
  slug: z.string(),
  full_name: z.string(),
  first_name: z.string().nullable(),
  last_name: z.string().nullable(),
  position: z.string().nullable(),
  jersey_number: z.string().nullable(),
  active: z.boolean(),
  team: teamSchema.nullable(),
});

export const playerDetailSchema = playerListItemSchema.extend({
  height: z.string().nullable(),
  weight_pounds: z.number().nullable(),
  birthdate: z.string().nullable(),
});

export const playersResponseSchema = z.object({
  items: z.array(playerListItemSchema),
  meta: pageMetaSchema,
});

export const seasonsResponseSchema = z.object({
  seasons: z.array(z.string()),
});

export const syncRunStatusSchema = z.object({
  id: z.number(),
  source: z.string(),
  status: z.string(),
  finished_at: z.string().nullable(),
  fetched_count: z.number(),
  inserted_count: z.number(),
  updated_count: z.number(),
  rejected_count: z.number(),
  error_message: z.string().nullable(),
});

export const dataStatusSchema = z.object({
  current_season: z.string(),
  player_count: z.number(),
  game_count: z.number(),
  player_game_record_count: z.number(),
  last_successful_sync: syncRunStatusSchema.nullable(),
  last_failed_sync: syncRunStatusSchema.nullable(),
});

export const playerSeasonSummarySchema = z.object({
  player_id: z.number(),
  nba_player_id: z.number(),
  season: z.string(),
  games_played: z.number(),
  minutes_per_game: z.number().nullable(),
  points_per_game: z.number().nullable(),
  rebounds_per_game: z.number().nullable(),
  assists_per_game: z.number().nullable(),
  turnovers_per_game: z.number().nullable(),
  plus_minus_per_game: z.number().nullable(),
  true_shooting_percentage: z.number().nullable(),
  true_shooting_source: z.string().nullable(),
  usage_rate: z.number().nullable(),
  points_per_36: z.number().nullable(),
  rebounds_per_36: z.number().nullable(),
  assists_per_36: z.number().nullable(),
  turnovers_per_36: z.number().nullable(),
  analytics_rebuilt_at: z.string().nullable(),
  analytics_warnings: z.array(z.record(z.string(), z.unknown())),
});

export const playerSeasonSummariesResponseSchema = z.object({
  items: z.array(playerSeasonSummarySchema),
});

export const gameLogItemSchema = z.object({
  id: z.number(),
  game_id: z.number(),
  nba_game_id: z.string(),
  game_date: z.string(),
  season: z.string(),
  matchup: z.string().nullable(),
  location: z.enum(["home", "away"]).nullable(),
  opponent: teamSchema.nullable(),
  result: z.enum(["W", "L"]).nullable(),
  days_since_previous_game: z.number().nullable(),
  minutes: z.number().nullable(),
  points: z.number(),
  rebounds: z.number(),
  assists: z.number(),
  steals: z.number(),
  blocks: z.number(),
  turnovers: z.number(),
  personal_fouls: z.number(),
  field_goals_made: z.number(),
  field_goals_attempted: z.number(),
  three_pointers_made: z.number(),
  three_pointers_attempted: z.number(),
  free_throws_made: z.number(),
  free_throws_attempted: z.number(),
  plus_minus: z.number().nullable(),
  calculated_true_shooting_percentage: z.number().nullable(),
});

export const playerGamesResponseSchema = z.object({
  items: z.array(gameLogItemSchema),
  meta: pageMetaSchema,
});

export const trendsResponseSchema = z.object({
  player_id: z.number(),
  nba_player_id: z.number(),
  season: z.string(),
  production_trend: z.string().nullable(),
  production_trend_value: z.number().nullable(),
  efficiency_trend: z.string().nullable(),
  efficiency_trend_value: z.number().nullable(),
  payload: z.record(z.string(), z.unknown()),
});

export const splitSchema = z.object({
  games: z.number(),
  minutes: z.number(),
  points: z.number(),
  rebounds: z.number(),
  assists: z.number(),
  true_shooting_percentage: z.number().nullable(),
});

export const splitsResponseSchema = z.object({
  player_id: z.number(),
  nba_player_id: z.number(),
  season: z.string(),
  home: splitSchema.nullable(),
  away: splitSchema.nullable(),
});

export const benchmarksResponseSchema = z.object({
  player_id: z.number(),
  nba_player_id: z.number(),
  season: z.string(),
  league_percentiles: z.record(z.string(), z.unknown()),
  position_percentiles: z.record(z.string(), z.unknown()),
  minutes_tier_percentiles: z.record(z.string(), z.unknown()),
  analytics_warnings: z.array(z.record(z.string(), z.unknown())),
});

export const similarPlayerSchema = z.object({
  player: playerListItemSchema,
  summary: playerSeasonSummarySchema,
  similarity_score: z.number(),
  shared_position: z.boolean(),
  minutes_difference: z.number().nullable(),
});

export const similarPlayersResponseSchema = z.object({
  player_id: z.number(),
  nba_player_id: z.number(),
  season: z.string(),
  players: z.array(similarPlayerSchema),
});

export const recentWindowSchema = z.object({
  window: z.number(),
  games: z.number(),
  points: z.number().nullable(),
  rebounds: z.number().nullable(),
  assists: z.number().nullable(),
  minutes: z.number().nullable(),
  true_shooting_percentage: z.number().nullable(),
  turnovers: z.number().nullable(),
  plus_minus: z.number().nullable(),
});

export const restSplitsSchema = z.object({
  first_game: splitSchema.nullable(),
  back_to_back: splitSchema.nullable(),
  one_day_rest: splitSchema.nullable(),
  two_or_more_days_rest: splitSchema.nullable(),
});

export const rollingTrendPointSchema = z.object({
  player_id: z.number(),
  nba_player_id: z.number(),
  game_id: z.number(),
  game_date: z.string(),
  points_rolling_5: z.number().nullable(),
  points_rolling_10: z.number().nullable(),
  assists_rolling_5: z.number().nullable(),
  assists_rolling_10: z.number().nullable(),
  true_shooting_percentage_rolling_5: z.number().nullable(),
  true_shooting_percentage_rolling_10: z.number().nullable(),
});

export const compareMetricSchema = z.object({
  key: z.string(),
  label: z.string(),
  category: z.string(),
  higher_is_better: z.boolean(),
  player_a_value: z.number().nullable(),
  player_b_value: z.number().nullable(),
  winner: z.enum(["player_a", "player_b", "tie"]).nullable(),
});

export const comparePlayerSchema = z.object({
  player: playerListItemSchema,
  summary: playerSeasonSummarySchema,
  trends: trendsResponseSchema,
  splits: splitsResponseSchema,
  benchmarks: benchmarksResponseSchema,
  rest_splits: restSplitsSchema,
  recent_5: recentWindowSchema,
  recent_10: recentWindowSchema,
  rolling_trend: z.array(rollingTrendPointSchema),
});

export const compareResponseSchema = z.object({
  season: z.string(),
  player_a: comparePlayerSchema,
  player_b: comparePlayerSchema,
  position_match: z.boolean(),
  position_context: z.string(),
  category_winners: z.array(compareMetricSchema),
});

export const reportSentenceSchema = z.object({
  text: z.string(),
  fields: z.array(z.string()),
});

export const reportSectionSchema = z.object({
  key: z.string(),
  title: z.string(),
  sentences: z.array(reportSentenceSchema),
});

export const playerReportResponseSchema = z.object({
  player: playerListItemSchema,
  season: z.string(),
  summary: playerSeasonSummarySchema,
  trends: trendsResponseSchema,
  splits: splitsResponseSchema,
  benchmarks: benchmarksResponseSchema,
  sample_size_warnings: z.array(z.record(z.string(), z.unknown())),
  sections: z.array(reportSectionSchema),
});

export const assistantSourceSchema = z.object({
  tool: z.string(),
  arguments: z.record(z.string(), z.unknown()),
});

export const assistantChatResponseSchema = z.object({
  session_id: z.string(),
  message: z.string(),
  mode: z.string(),
  sources: z.array(assistantSourceSchema),
  context: z.object({
    last_entity_type: z.string().nullable(),
    last_entity_name: z.string().nullable(),
  }),
  data: z.record(z.string(), z.unknown()).nullable(),
});

export const awardCandidateSchema = z.object({
  rank: z.number(),
  entity_id: z.number(),
  name: z.string(),
  team: z.string().nullable(),
  position: z.string().nullable(),
  probability: z.number(),
  score: z.number(),
  features: z.record(z.string(), z.number()),
  feature_attributions: z.array(
    z.object({
      feature: z.string(),
      raw_value: z.number(),
      normalized_value: z.number(),
      weight: z.number(),
      contribution: z.number(),
    }),
  ),
  warnings: z.array(z.string()),
});

export const awardPredictionSchema = z.object({
  prediction_id: z.number().nullable(),
  award_type: z.string(),
  target_season: z.string(),
  source_season: z.string(),
  model_version: z.string(),
  candidates: z.array(awardCandidateSchema),
  warnings: z.array(z.string()),
  methodology: z.string(),
});

export const projectedTeamSchema = z.object({
  rank: z.number(),
  conference_rank: z.number().nullable(),
  team_id: z.number(),
  nba_team_id: z.number(),
  team_name: z.string(),
  abbreviation: z.string(),
  conference: z.string().nullable(),
  division: z.string().nullable(),
  projected_wins: z.number(),
  projected_losses: z.number(),
  projected_point_differential: z.number(),
  confidence: z.number(),
  factors: z.array(
    z.object({
      feature: z.string(),
      raw_value: z.number(),
      contribution: z.number(),
    }),
  ),
  warnings: z.array(z.string()),
});

export const standingsPredictionSchema = z.object({
  prediction_id: z.number().nullable(),
  target_season: z.string(),
  source_season: z.string(),
  conference: z.string().nullable(),
  model_version: z.string(),
  teams: z.array(projectedTeamSchema),
  warnings: z.array(z.string()),
  methodology: z.string(),
});

export const predictionLogSchema = z.object({
  predictions: z.array(
    z.object({
      id: z.number(),
      created_at: z.string(),
      target_season: z.string(),
      prediction_type: z.string(),
      model_version: z.string(),
      notes: z.string().nullable(),
      payload: z.record(z.string(), z.unknown()),
    }),
  ),
});

export type BackendHealth = z.infer<typeof healthSchema>;
export type AssistantChatResponse = z.infer<typeof assistantChatResponseSchema>;
export type AssistantSource = z.infer<typeof assistantSourceSchema>;
export type AwardCandidate = z.infer<typeof awardCandidateSchema>;
export type AwardPrediction = z.infer<typeof awardPredictionSchema>;
export type CompareMetric = z.infer<typeof compareMetricSchema>;
export type ComparePlayer = z.infer<typeof comparePlayerSchema>;
export type CompareResponse = z.infer<typeof compareResponseSchema>;
export type DataStatus = z.infer<typeof dataStatusSchema>;
export type DraftPick = z.infer<typeof draftPickSchema>;
export type DraftResponse = z.infer<typeof draftResponseSchema>;
export type PlayoffRoundResponse = z.infer<typeof playoffRoundResponseSchema>;
export type GameLogItem = z.infer<typeof gameLogItemSchema>;
export type PageMeta = z.infer<typeof pageMetaSchema>;
export type PlayerBenchmarks = z.infer<typeof benchmarksResponseSchema>;
export type PlayerDetail = z.infer<typeof playerDetailSchema>;
export type PlayerGamesResponse = z.infer<typeof playerGamesResponseSchema>;
export type PlayerReportResponse = z.infer<typeof playerReportResponseSchema>;
export type PlayerListItem = z.infer<typeof playerListItemSchema>;
export type PlayersResponse = z.infer<typeof playersResponseSchema>;
export type PlayerSeasonSummary = z.infer<typeof playerSeasonSummarySchema>;
export type PlayerSeasonSummariesResponse = z.infer<typeof playerSeasonSummariesResponseSchema>;
export type RecentWindow = z.infer<typeof recentWindowSchema>;
export type ReportSection = z.infer<typeof reportSectionSchema>;
export type RestSplits = z.infer<typeof restSplitsSchema>;
export type RollingTrendPoint = z.infer<typeof rollingTrendPointSchema>;
export type SimilarPlayer = z.infer<typeof similarPlayerSchema>;
export type SimilarPlayersResponse = z.infer<typeof similarPlayersResponseSchema>;
export type PlayerSplits = z.infer<typeof splitsResponseSchema>;
export type PlayerTrends = z.infer<typeof trendsResponseSchema>;
export type SeasonsResponse = z.infer<typeof seasonsResponseSchema>;
export type SplitSummary = z.infer<typeof splitSchema>;
export type Team = z.infer<typeof teamSchema>;
export type TeamsResponse = z.infer<typeof teamsResponseSchema>;
export type PredictionLog = z.infer<typeof predictionLogSchema>;
export type ProjectedTeam = z.infer<typeof projectedTeamSchema>;
export type StandingsPrediction = z.infer<typeof standingsPredictionSchema>;
