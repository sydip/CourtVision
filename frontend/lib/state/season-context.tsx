"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getSeasons } from "@/lib/api/courtvision";

const DEFAULT_SEASON = "2025-26";
const STORAGE_KEY = "courtvision:selected-season";
const FALLBACK_SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23", "2021-22"];

type SeasonContextValue = {
  season: string;
  seasons: string[];
  setSeason: (season: string) => void;
  isLoading: boolean;
  isSupported: boolean;
};

const fallbackContext: SeasonContextValue = {
  season: DEFAULT_SEASON,
  seasons: FALLBACK_SEASONS,
  setSeason: () => undefined,
  isLoading: false,
  isSupported: true,
};
const SeasonContext = createContext<SeasonContextValue>(fallbackContext);

export function SeasonProvider({ children }: { children: React.ReactNode }) {
  const [seasons, setSeasons] = useState<string[]>(FALLBACK_SEASONS);
  const [season, setSeasonState] = useState(DEFAULT_SEASON);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("season");
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const initial = requested || stored || DEFAULT_SEASON;
    setSeasonState(initial);
    getSeasons()
      .then((response) => {
        setSeasons(response.seasons.length > 0 ? response.seasons : FALLBACK_SEASONS);
      })
      .catch(() => setSeasons(FALLBACK_SEASONS))
      .finally(() => setIsLoading(false));

    function syncSeasonFromUrl() {
      const nextSeason = new URLSearchParams(window.location.search).get("season");
      if (nextSeason) {
        setSeasonState(nextSeason);
      }
    }

    window.addEventListener("popstate", syncSeasonFromUrl);
    return () => window.removeEventListener("popstate", syncSeasonFromUrl);
  }, []);

  function setSeason(nextSeason: string) {
    setSeasonState(nextSeason);
    window.localStorage.setItem(STORAGE_KEY, nextSeason);
    const url = new URL(window.location.href);
    url.searchParams.set("season", nextSeason);
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }

  useEffect(() => {
    if (!isLoading && seasons.includes(season)) {
      window.localStorage.setItem(STORAGE_KEY, season);
      const url = new URL(window.location.href);
      if (url.searchParams.get("season") !== season) {
        url.searchParams.set("season", season);
        window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
      }
    }
  }, [isLoading, season, seasons]);

  const value = useMemo(
    () => ({ season, seasons, setSeason, isLoading, isSupported: seasons.includes(season) }),
    [isLoading, season, seasons],
  );
  return <SeasonContext.Provider value={value}>{children}</SeasonContext.Provider>;
}

export function useSeason(): SeasonContextValue {
  return useContext(SeasonContext);
}
