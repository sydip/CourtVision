import { fetchApi, toQueryString } from "@/lib/api/client";
import {
  assistantChatResponseSchema,
  awardPredictionSchema,
  benchmarksResponseSchema,
  compareResponseSchema,
  dataStatusSchema,
  draftResponseSchema,
  playerReportResponseSchema,
  playoffRoundResponseSchema,
  playerDetailSchema,
  playerGamesResponseSchema,
  playerSeasonSummariesResponseSchema,
  playerSeasonSummarySchema,
  similarPlayersResponseSchema,
  playersResponseSchema,
  seasonsResponseSchema,
  splitsResponseSchema,
  teamsResponseSchema,
  trendsResponseSchema,
  predictionLogSchema,
  standingsPredictionSchema,
  type AssistantChatResponse,
  type AwardPrediction,
  type CompareResponse,
  type DataStatus,
  type DraftResponse,
  type PlayerBenchmarks,
  type PlayerDetail,
  type PlayerGamesResponse,
  type PlayerReportResponse,
  type PlayoffRoundResponse,
  type PlayerListItem,
  type PlayersResponse,
  type PlayerSeasonSummariesResponse,
  type PlayerSeasonSummary,
  type SimilarPlayersResponse,
  type PlayerSplits,
  type PlayerTrends,
  type SeasonsResponse,
  type TeamsResponse,
  type PredictionLog,
  type StandingsPrediction,
} from "@/lib/api/schemas";

export type PlayerSearchParams = {
  q?: string;
  limit?: number;
  offset?: number;
};

export type PlayerGamesParams = {
  limit?: number;
  offset?: number;
  location?: "home" | "away";
  opponent?: string;
  result?: "W" | "L";
  sort?: "asc" | "desc";
};

export function getDataStatus(): Promise<DataStatus> {
  return fetchApi("/api/data-status", dataStatusSchema);
}

export function getCompare(
  playerA: number,
  playerB: number,
  season: string,
): Promise<CompareResponse> {
  return fetchApi(
    `/api/compare${toQueryString({ player_a: playerA, player_b: playerB, season })}`,
    compareResponseSchema,
  );
}

export function getSeasons(): Promise<SeasonsResponse> {
  return fetchApi("/api/seasons", seasonsResponseSchema);
}

export function getTeams(): Promise<TeamsResponse> {
  return fetchApi("/api/teams", teamsResponseSchema);
}

export function getDraft(draftYear = 2026): Promise<DraftResponse> {
  return fetchApi(`/api/drafts/${draftYear}`, draftResponseSchema);
}

export function getPlayoffRound(
  season = "2025-26",
  roundSlug = "first-round",
): Promise<PlayoffRoundResponse> {
  return fetchApi(`/api/playoffs/${season}/rounds/${roundSlug}`, playoffRoundResponseSchema);
}

export function getPlayers(params: PlayerSearchParams = {}): Promise<PlayersResponse> {
  return fetchApi(
    `/api/players${toQueryString({
      q: params.q,
      limit: params.limit ?? 8,
      offset: params.offset ?? 0,
    })}`,
    playersResponseSchema,
  );
}

export async function getAllPlayers(): Promise<PlayerListItem[]> {
  const limit = 100;
  const players: PlayerListItem[] = [];
  let offset = 0;

  for (let page = 0; page < 20; page += 1) {
    const response = await getPlayers({ limit, offset });
    players.push(...response.items);

    if (response.meta.next_offset === null) {
      break;
    }
    offset = response.meta.next_offset;
  }

  return players;
}

export function getPlayer(playerId: number): Promise<PlayerDetail> {
  return fetchApi(`/api/players/${playerId}`, playerDetailSchema);
}

export function getPlayerSummary(playerId: number, season: string): Promise<PlayerSeasonSummary> {
  return fetchApi(`/api/players/${playerId}/seasons/${season}/summary`, playerSeasonSummarySchema);
}

export function getSeasonSummaries(season: string): Promise<PlayerSeasonSummariesResponse> {
  return fetchApi(`/api/seasons/${season}/summaries`, playerSeasonSummariesResponseSchema);
}

export function getPlayerGames(
  playerId: number,
  season: string,
  params: PlayerGamesParams = {},
): Promise<PlayerGamesResponse> {
  return fetchApi(
    `/api/players/${playerId}/seasons/${season}/games${toQueryString({
      limit: params.limit ?? 100,
      offset: params.offset ?? 0,
      location: params.location,
      opponent: params.opponent,
      result: params.result,
      sort: params.sort ?? "asc",
    })}`,
    playerGamesResponseSchema,
  );
}

export function getPlayerTrends(playerId: number, season: string): Promise<PlayerTrends> {
  return fetchApi(`/api/players/${playerId}/seasons/${season}/trends`, trendsResponseSchema);
}

export function getPlayerSplits(playerId: number, season: string): Promise<PlayerSplits> {
  return fetchApi(`/api/players/${playerId}/seasons/${season}/splits`, splitsResponseSchema);
}

export function getPlayerBenchmarks(playerId: number, season: string): Promise<PlayerBenchmarks> {
  return fetchApi(
    `/api/players/${playerId}/seasons/${season}/benchmarks`,
    benchmarksResponseSchema,
  );
}

export function getPlayerReport(playerId: number, season: string): Promise<PlayerReportResponse> {
  return fetchApi(`/api/players/${playerId}/seasons/${season}/report`, playerReportResponseSchema);
}

export function getSimilarPlayers(
  playerId: number,
  season: string,
  limit = 5,
): Promise<SimilarPlayersResponse> {
  return fetchApi(
    `/api/players/${playerId}/seasons/${season}/similar${toQueryString({ limit })}`,
    similarPlayersResponseSchema,
  );
}

export function sendAssistantMessage(
  message: string,
  sessionId?: string,
): Promise<AssistantChatResponse> {
  return fetchApi("/api/assistant/chat", assistantChatResponseSchema, undefined, {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export function getAwardPrediction(
  awardType: string,
  season: string,
  limit = 5,
): Promise<AwardPrediction> {
  return fetchApi(
    `/api/predictions/awards/${awardType}${toQueryString({ season, limit })}`,
    awardPredictionSchema,
  );
}

export function getStandingsPrediction(
  season: string,
  conference?: "East" | "West",
): Promise<StandingsPrediction> {
  return fetchApi(
    `/api/predictions/standings${toQueryString({ season, conference })}`,
    standingsPredictionSchema,
  );
}

export function getPredictionLog(limit = 20): Promise<PredictionLog> {
  return fetchApi(`/api/predictions${toQueryString({ limit })}`, predictionLogSchema);
}
