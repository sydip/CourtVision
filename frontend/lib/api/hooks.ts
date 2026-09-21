"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getCompare,
  getDataStatus,
  getPlayer,
  getPlayerBenchmarks,
  getPlayerGames,
  getPlayerReport,
  getPlayers,
  getPlayerSplits,
  getPlayerSummary,
  getPlayerTrends,
  getSeasons,
  getSimilarPlayers,
  type PlayerGamesParams,
} from "@/lib/api/courtvision";

export const queryKeys = {
  compare: (playerA: number, playerB: number, season: string) =>
    ["compare", playerA, playerB, season] as const,
  dataStatus: (season: string) => ["data-status", season] as const,
  seasons: ["seasons"] as const,
  players: (season: string, q: string, limit: number) => ["players", season, q, limit] as const,
  player: (playerId: number, season: string) => ["player", playerId, season] as const,
  summary: (playerId: number, season: string) => ["summary", playerId, season] as const,
  games: (playerId: number, season: string, params: PlayerGamesParams) =>
    ["games", playerId, season, params] as const,
  trends: (playerId: number, season: string) => ["trends", playerId, season] as const,
  splits: (playerId: number, season: string) => ["splits", playerId, season] as const,
  benchmarks: (playerId: number, season: string) => ["benchmarks", playerId, season] as const,
  report: (playerId: number, season: string) => ["report", playerId, season] as const,
  similarPlayers: (playerId: number, season: string, limit: number, samePositionOnly: boolean) =>
    ["similar-players", playerId, season, limit, samePositionOnly] as const,
};

export function useCompare(playerA: number | null, playerB: number | null, season: string) {
  return useQuery({
    queryKey: queryKeys.compare(playerA ?? 0, playerB ?? 0, season),
    queryFn: () => getCompare(playerA ?? 0, playerB ?? 0, season),
    enabled:
      typeof playerA === "number" &&
      playerA > 0 &&
      typeof playerB === "number" &&
      playerB > 0 &&
      playerA !== playerB &&
      season.length > 0,
    retry: false,
  });
}

export function useDataStatus(season = "2025-26") {
  return useQuery({
    queryKey: queryKeys.dataStatus(season),
    queryFn: () => getDataStatus(season),
    staleTime: 30_000,
  });
}

export function useSeasons() {
  return useQuery({
    queryKey: queryKeys.seasons,
    queryFn: getSeasons,
    staleTime: 300_000,
  });
}

export function usePlayers(q: string, limit = 8, season = "2025-26") {
  const normalizedQuery = q.trim();
  return useQuery({
    queryKey: queryKeys.players(season, normalizedQuery, limit),
    queryFn: () => getPlayers({ q: normalizedQuery || undefined, limit, season }),
    staleTime: 30_000,
  });
}

export function usePlayer(playerId: number, season = "2025-26") {
  return useQuery({
    queryKey: queryKeys.player(playerId, season),
    queryFn: () => getPlayer(playerId, season),
    enabled: Number.isFinite(playerId) && playerId > 0,
    retry: false,
  });
}

export function usePlayerSummary(playerId: number, season: string) {
  return useQuery({
    queryKey: queryKeys.summary(playerId, season),
    queryFn: () => getPlayerSummary(playerId, season),
    enabled: Number.isFinite(playerId) && playerId > 0 && season.length > 0,
    retry: false,
  });
}

export function usePlayerGames(playerId: number, season: string, params: PlayerGamesParams = {}) {
  return useQuery({
    queryKey: queryKeys.games(playerId, season, params),
    queryFn: () => getPlayerGames(playerId, season, params),
    enabled: Number.isFinite(playerId) && playerId > 0 && season.length > 0,
    retry: false,
  });
}

export function usePlayerTrends(playerId: number, season: string) {
  return useQuery({
    queryKey: queryKeys.trends(playerId, season),
    queryFn: () => getPlayerTrends(playerId, season),
    enabled: Number.isFinite(playerId) && playerId > 0 && season.length > 0,
    retry: false,
  });
}

export function usePlayerSplits(playerId: number, season: string) {
  return useQuery({
    queryKey: queryKeys.splits(playerId, season),
    queryFn: () => getPlayerSplits(playerId, season),
    enabled: Number.isFinite(playerId) && playerId > 0 && season.length > 0,
    retry: false,
  });
}

export function usePlayerBenchmarks(playerId: number, season: string) {
  return useQuery({
    queryKey: queryKeys.benchmarks(playerId, season),
    queryFn: () => getPlayerBenchmarks(playerId, season),
    enabled: Number.isFinite(playerId) && playerId > 0 && season.length > 0,
    retry: false,
  });
}

export function usePlayerReport(playerId: number, season: string) {
  return useQuery({
    queryKey: queryKeys.report(playerId, season),
    queryFn: () => getPlayerReport(playerId, season),
    enabled: Number.isFinite(playerId) && playerId > 0 && season.length > 0,
    retry: false,
  });
}

export function useSimilarPlayers(
  playerId: number,
  season: string,
  limit = 5,
  samePositionOnly = false,
) {
  return useQuery({
    queryKey: queryKeys.similarPlayers(playerId, season, limit, samePositionOnly),
    queryFn: () => getSimilarPlayers(playerId, season, limit, samePositionOnly),
    enabled: Number.isFinite(playerId) && playerId > 0 && season.length > 0,
    retry: false,
  });
}
