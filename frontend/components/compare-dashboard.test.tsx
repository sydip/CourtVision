import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CompareDashboard } from "@/components/compare-dashboard";
import type { CompareResponse, DataStatus, PlayerListItem, Team } from "@/lib/api/schemas";

const getAllPlayersMock = vi.hoisted(() => vi.fn());
const getDataStatusMock = vi.hoisted(() => vi.fn());
const getPlayersMock = vi.hoisted(() => vi.fn());
const getSeasonsMock = vi.hoisted(() => vi.fn());
const getTeamsMock = vi.hoisted(() => vi.fn());
const useCompareMock = vi.hoisted(() => vi.fn());
const usePlayerGamesMock = vi.hoisted(() => vi.fn());

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.mock("@/lib/api/hoopsiq", () => ({
  getAllPlayers: getAllPlayersMock,
  getDataStatus: getDataStatusMock,
  getPlayers: getPlayersMock,
  getSeasons: getSeasonsMock,
  getTeams: getTeamsMock,
}));

vi.mock("@/lib/api/hooks", () => ({
  useCompare: useCompareMock,
  usePlayerGames: usePlayerGamesMock,
}));

const warriors: Team = {
  id: 1,
  nba_team_id: 1610612744,
  abbreviation: "GSW",
  city: "Golden State",
  name: "Warriors",
  conference: "West",
  division: "Pacific",
};

const lakers: Team = {
  id: 2,
  nba_team_id: 1610612747,
  abbreviation: "LAL",
  city: "Los Angeles",
  name: "Lakers",
  conference: "West",
  division: "Pacific",
};

const curry = player(201939, "Stephen Curry", "G", warriors);
const lebron = player(2544, "LeBron James", "F", lakers);

const dataStatus: DataStatus = {
  current_season: "2025-26",
  player_count: 2,
  game_count: 2,
  player_game_record_count: 4,
  last_successful_sync: null,
  last_failed_sync: null,
};

describe("CompareDashboard", () => {
  beforeEach(() => {
    global.ResizeObserver = ResizeObserverMock;
    getAllPlayersMock.mockResolvedValue([curry, lebron]);
    getDataStatusMock.mockResolvedValue(dataStatus);
    getSeasonsMock.mockResolvedValue({ seasons: ["2025-26"] });
    getTeamsMock.mockResolvedValue({ teams: [warriors, lakers] });
    getPlayersMock.mockResolvedValue({
      items: [],
      meta: {
        limit: 6,
        offset: 0,
        total: 0,
        next_offset: null,
        previous_offset: null,
      },
    });
    useCompareMock.mockImplementation((playerA: number | null, playerB: number | null) => {
      if (playerA === 201939 && playerB === 2544) {
        return { data: compareResponse(), isError: false };
      }
      return { data: undefined, isError: false };
    });
    usePlayerGamesMock.mockReturnValue({
      data: {
        items: [gameLog()],
        meta: { limit: 100, offset: 0, total: 1, next_offset: null, previous_offset: null },
      },
      isLoading: false,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("requires selecting both players before showing results", async () => {
    render(<CompareDashboard />);

    expect(await screen.findByRole("heading", { name: "Select Players" })).toBeInTheDocument();

    const compareButton = screen.getByRole("button", { name: "Compare Players" });
    expect(compareButton).toBeDisabled();

    // Open the first empty slot, search, and select Player A.
    fireEvent.click(screen.getAllByRole("button", { name: /Add Player/i })[0]);
    fireEvent.change(screen.getByPlaceholderText("Search a player..."), {
      target: { value: "curry" },
    });
    fireEvent.click(await screen.findByRole("option", { name: /Stephen Curry/i }));

    expect(screen.getByRole("button", { name: "Compare Players" })).toBeDisabled();

    // Open the remaining empty slot and select Player B.
    fireEvent.click(screen.getByRole("button", { name: /Add Player/i }));
    fireEvent.change(screen.getByPlaceholderText("Search a player..."), {
      target: { value: "lebron" },
    });
    fireEvent.click(await screen.findByRole("option", { name: /LeBron James/i }));

    const readyButton = screen.getByRole("button", { name: "Compare Players" });
    expect(readyButton).toBeEnabled();
    fireEvent.click(readyButton);

    expect(await screen.findByText("Category Winners")).toBeInTheDocument();
    expect(screen.getByText("Overall Leader")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Stephen Curry is the better overall player/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Statistical Graphs")).toBeInTheDocument();
    expect(screen.getByText("Offensive")).toBeInTheDocument();
    expect(screen.getByText("Defensive")).toBeInTheDocument();
    expect(screen.getByText("Efficiency")).toBeInTheDocument();
    expect(screen.getAllByText("True Shooting").length).toBeGreaterThanOrEqual(1);
    // Each of the 4 graphs has a Recent/Season trend toggle.
    expect(screen.getAllByRole("button", { name: "Season" }).length).toBe(4);
    expect(screen.getAllByRole("button", { name: "Recent" }).length).toBe(4);
    expect(screen.getAllByText("Recent Form").length).toBe(2);
    expect(screen.getAllByText(/wins 4/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Statistical Verdict")).toBeInTheDocument();
  });
});

function player(
  nbaPlayerId: number,
  fullName: string,
  position: string,
  team: Team,
): PlayerListItem {
  const [firstName, ...restName] = fullName.split(" ");
  return {
    id: nbaPlayerId,
    nba_player_id: nbaPlayerId,
    slug: `${fullName.toLowerCase().replaceAll(" ", "-")}-${nbaPlayerId}`,
    full_name: fullName,
    first_name: firstName,
    last_name: restName.join(" "),
    position,
    jersey_number: null,
    active: true,
    team,
  };
}

function compareResponse(): CompareResponse {
  return {
    season: "2025-26",
    player_a: comparePlayer(curry, 27),
    player_b: comparePlayer(lebron, 26),
    position_match: false,
    position_context:
      "Stephen Curry is listed at G while LeBron James is listed at F; position percentile comparisons should be read in that context.",
    category_winners: [
      metric("points_per_game", "Points / Game", "season_averages", 27, 26, "player_a"),
      metric("rebounds_per_game", "Rebounds / Game", "season_averages", 4.5, 8, "player_b"),
      metric("assists_per_game", "Assists / Game", "season_averages", 6.5, 9, "player_b"),
      metric("minutes_per_game", "Minutes / Game", "season_averages", 33.3, 33.3, "tie"),
      metric("true_shooting_percentage", "True Shooting", "efficiency", 0.625, 0.61, "player_a"),
      metric("turnovers_per_game", "Turnovers / Game", "efficiency", 2.5, 3, "player_a", false),
      metric("recent_5_points", "Recent 5 PPG", "recent_form", 27, 26, "player_a"),
    ],
  };
}

function comparePlayer(playerItem: PlayerListItem, points: number): CompareResponse["player_a"] {
  return {
    player: playerItem,
    summary: {
      player_id: playerItem.id,
      nba_player_id: playerItem.nba_player_id,
      season: "2025-26",
      games_played: 2,
      minutes_per_game: 33.25,
      points_per_game: points,
      rebounds_per_game: playerItem.nba_player_id === 201939 ? 4.5 : 8,
      assists_per_game: playerItem.nba_player_id === 201939 ? 6.5 : 9,
      turnovers_per_game: 2.5,
      plus_minus_per_game: 1.5,
      true_shooting_percentage: 0.625,
      true_shooting_source: "calculated",
      usage_rate: 0.29,
      points_per_36: 29.2,
      rebounds_per_36: 4.8,
      assists_per_36: 7,
      turnovers_per_36: 2.7,
      analytics_rebuilt_at: null,
      analytics_warnings: [{ code: "small_sample", message: "2 games" }],
    },
    trends: {
      player_id: playerItem.id,
      nba_player_id: playerItem.nba_player_id,
      season: "2025-26",
      production_trend: "stable",
      production_trend_value: 0.1,
      efficiency_trend: "stable",
      efficiency_trend_value: -0.05,
      payload: {},
    },
    splits: {
      player_id: playerItem.id,
      nba_player_id: playerItem.nba_player_id,
      season: "2025-26",
      home: split(1, points),
      away: split(1, points - 1),
    },
    benchmarks: {
      player_id: playerItem.id,
      nba_player_id: playerItem.nba_player_id,
      season: "2025-26",
      league_percentiles: { points_per_game: 87 },
      position_percentiles: {
        points_per_game: 87,
        assists_per_game: 92,
        true_shooting_percentage: 71,
      },
      minutes_tier_percentiles: { true_shooting_percentage: 71 },
      analytics_warnings: [],
    },
    rest_splits: {
      first_game: split(1, points),
      back_to_back: null,
      one_day_rest: split(1, points - 1),
      two_or_more_days_rest: null,
    },
    recent_5: recent(5, points),
    recent_10: recent(10, points),
    rolling_trend: [
      {
        player_id: playerItem.id,
        nba_player_id: playerItem.nba_player_id,
        game_id: 1,
        game_date: "2025-10-21",
        points_rolling_5: points,
        points_rolling_10: points,
        assists_rolling_5: 6,
        assists_rolling_10: 6,
        true_shooting_percentage_rolling_5: 0.62,
        true_shooting_percentage_rolling_10: 0.62,
      },
    ],
  };
}

function metric(
  key: string,
  label: string,
  category: string,
  playerAValue: number,
  playerBValue: number,
  winner: "player_a" | "player_b" | "tie",
  higherIsBetter = true,
) {
  return {
    key,
    label,
    category,
    higher_is_better: higherIsBetter,
    player_a_value: playerAValue,
    player_b_value: playerBValue,
    winner,
  };
}

function split(games: number, points: number) {
  return {
    games,
    minutes: 33,
    points,
    rebounds: 5,
    assists: 6,
    true_shooting_percentage: 0.62,
  };
}

function recent(window: number, points: number) {
  return {
    window,
    games: 2,
    points,
    rebounds: 5,
    assists: 6,
    minutes: 33,
    true_shooting_percentage: 0.62,
    turnovers: 2,
    plus_minus: 1,
  };
}

function gameLog() {
  return {
    id: 1,
    game_id: 1,
    nba_game_id: "0022500001",
    game_date: "2025-10-21",
    season: "2025-26",
    matchup: "GSW vs. LAL",
    location: "home" as const,
    opponent: lakers,
    result: "W" as const,
    days_since_previous_game: null,
    minutes: 33,
    points: 28,
    rebounds: 5,
    assists: 6,
    steals: 2,
    blocks: 1,
    turnovers: 2,
    personal_fouls: 3,
    field_goals_made: 10,
    field_goals_attempted: 20,
    three_pointers_made: 4,
    three_pointers_attempted: 9,
    free_throws_made: 4,
    free_throws_attempted: 4,
    plus_minus: 8,
    calculated_true_shooting_percentage: 0.62,
  };
}
