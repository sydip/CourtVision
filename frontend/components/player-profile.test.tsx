import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen, within } from "@testing-library/react";
import React from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { getTeamTheme, PlayerProfileView } from "@/components/player-profile";
import type {
  GameLogItem,
  PlayerBenchmarks,
  PlayerDetail,
  PlayerSeasonSummary,
  PlayerSplits,
  PlayerTrends,
  SimilarPlayer,
} from "@/lib/api/schemas";

beforeAll(() => {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  vi.stubGlobal("ResizeObserver", ResizeObserverMock);
});

const player: PlayerDetail = {
  id: 1,
  nba_player_id: 201939,
  slug: "stephen-curry",
  full_name: "Stephen Curry",
  first_name: "Stephen",
  last_name: "Curry",
  position: "PG",
  jersey_number: "30",
  height: "6-2",
  weight_pounds: 185,
  birthdate: "1988-03-14",
  active: true,
  team: {
    id: 1,
    nba_team_id: 1610612744,
    abbreviation: "GSW",
    city: "Golden State",
    name: "Warriors",
    conference: "West",
    division: "Pacific",
  },
};

const summary: PlayerSeasonSummary = {
  player_id: 1,
  nba_player_id: 201939,
  season: "2025-26",
  games_played: 2,
  minutes_per_game: 33.2,
  points_per_game: 27,
  rebounds_per_game: 4.5,
  assists_per_game: 6.5,
  turnovers_per_game: 2.5,
  plus_minus_per_game: 1.5,
  true_shooting_percentage: 0.625,
  true_shooting_source: "calculated",
  usage_rate: 0.29,
  points_per_36: 29.2,
  rebounds_per_36: 4.8,
  assists_per_36: 7,
  turnovers_per_36: 2.7,
  analytics_rebuilt_at: "2026-06-30T18:36:17.000Z",
  analytics_warnings: [],
};

const games: GameLogItem[] = [
  buildGame({ id: 1, date: "2025-10-21", points: 30, isHome: true, result: "W", days: null }),
  buildGame({ id: 2, date: "2025-10-23", points: 24, isHome: false, result: "L", days: 2 }),
];

const splits: PlayerSplits = {
  player_id: 1,
  nba_player_id: 201939,
  season: "2025-26",
  home: {
    games: 1,
    minutes: 32.5,
    points: 30,
    rebounds: 4,
    assists: 7,
    true_shooting_percentage: 0.67,
  },
  away: {
    games: 1,
    minutes: 34,
    points: 24,
    rebounds: 5,
    assists: 6,
    true_shooting_percentage: 0.58,
  },
};

const trends: PlayerTrends = {
  player_id: 1,
  nba_player_id: 201939,
  season: "2025-26",
  production_trend: "stable",
  production_trend_value: 0.1,
  efficiency_trend: "improving",
  efficiency_trend_value: 0.3,
  payload: {},
};

const benchmarks: PlayerBenchmarks = {
  player_id: 1,
  nba_player_id: 201939,
  season: "2025-26",
  league_percentiles: {},
  position_percentiles: {
    points_per_game: 87,
    rebounds_per_game: 48,
    assists_per_game: 92,
    minutes_per_game: 71,
    plus_minus_per_game: 69,
    true_shooting_percentage: 88,
    field_goal_percentage: 63,
    three_point_percentage: 55,
    steals_per_game: 50,
    blocks_per_game: 40,
    turnovers_per_game: 38,
    points_per_36: 89,
    rebounds_per_36: 45,
    assists_per_36: 91,
    turnovers_per_36: 41,
  },
  minutes_tier_percentiles: {},
  analytics_warnings: [],
};

const similarPlayers: SimilarPlayer[] = [
  {
    player: {
      id: 2,
      nba_player_id: 2544,
      slug: "lebron-james-2544",
      full_name: "LeBron James",
      first_name: "LeBron",
      last_name: "James",
      position: "F",
      jersey_number: "23",
      active: true,
      team: {
        id: 2,
        nba_team_id: 1610612747,
        abbreviation: "LAL",
        city: "Los Angeles",
        name: "Lakers",
        conference: "West",
        division: "Pacific",
      },
    },
    summary: {
      ...summary,
      player_id: 2,
      nba_player_id: 2544,
      points_per_game: 26,
      rebounds_per_game: 8,
      assists_per_game: 9,
    },
    similarity_score: 74.2,
    shared_position: false,
    minutes_difference: 0.4,
  },
];

describe("PlayerProfileView", () => {
  it("uses logo-aware third graph colors", () => {
    expect(
      getTeamTheme({ nba_team_id: 1610612760, city: "Oklahoma City", name: "Thunder" }).graphThird,
    ).toBe("#ffffff");
    expect(
      getTeamTheme({ nba_team_id: 1610612752, city: "New York", name: "Knicks" }).graphThird,
    ).toBe("#ffffff");
    expect(
      getTeamTheme({ nba_team_id: 1610612756, city: "Phoenix", name: "Suns" }).graphThird,
    ).toBe("#ffffff");
    expect(
      getTeamTheme({ nba_team_id: 1610612761, city: "Toronto", name: "Raptors" }).graphThird,
    ).toBe("#753bbd");
    expect(getTeamTheme({ nba_team_id: 1610612762, city: "Utah", name: "Jazz" })).toMatchObject({
      primary: "#753bbd",
      accent: "#9bd8ff",
      graphThird: "#ffffff",
    });
  });

  it("renders player profile data from backend-shaped props", () => {
    const { container } = render(
      <PlayerProfileView
        benchmarks={benchmarks}
        games={games}
        hasProfileError={false}
        isLoading={false}
        player={player}
        selectedSeason="2025-26"
        similarPlayers={similarPlayers}
        splits={splits}
        summary={summary}
        trends={trends}
      />,
    );

    expect(screen.getByRole("heading", { name: "Stephen Curry" })).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: "Golden State Warriors logo" }),
    ).not.toBeInTheDocument();
    const profileGrid = container.querySelector(".profile-grid") as HTMLElement;
    expect(profileGrid).toHaveStyle({
      "--team-accent": "#ffc72c",
    });
    expect(screen.getByText("27.0")).toBeInTheDocument();
    expect(screen.getByLabelText(/offensive game log chart/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/defensive game log chart/i)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /recent player game log/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "FG%" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "3P%" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "FT" })).toBeInTheDocument();
    expect(screen.getAllByText("50.0%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("40.0%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("4-4").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("B2B")).toBeInTheDocument();
    expect(screen.getByText("Steals")).toBeInTheDocument();
    expect(screen.getByText("Blocks")).toBeInTheDocument();
    expect(screen.getByText("3PT%")).toBeInTheDocument();
    expect(screen.queryByText("GP")).not.toBeInTheDocument();
    expect(screen.getAllByText("Production").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Efficiency").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByLabelText(/Points 87th/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Plus \/ Minus 69th/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/FG% 63rd/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Steals 50th/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Minutes/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Similar Players" })).toBeInTheDocument();
    expect(screen.getByText("LeBron James")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Data Freshness" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Trend Overview" })).not.toBeInTheDocument();
    expect(screen.getByText("74.2")).toBeInTheDocument();
    const similarLink = screen.getByText("LeBron James").closest("a") as HTMLElement;
    expect(similarLink.getAttribute("style")).toContain("#552583");

    const offensiveControls = screen.getByRole("group", { name: "Offensive graph range" });
    const defensiveControls = screen.getByRole("group", { name: "Defensive graph range" });
    fireEvent.click(within(offensiveControls).getByRole("button", { name: "Last 5" }));
    expect(within(offensiveControls).getByRole("button", { name: "Last 5" })).toHaveClass("active");
    expect(within(defensiveControls).getByRole("button", { name: "Last 10" })).toHaveClass(
      "active",
    );
    fireEvent.click(within(defensiveControls).getByRole("button", { name: "Full Season" }));
    expect(
      screen.getByRole("dialog", { name: /full season defensive game log graph/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/season-to-date averages/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /close full season graph/i }));

    fireEvent.click(screen.getByRole("button", { name: /view full season game log/i }));
    expect(screen.getByRole("dialog", { name: /full season game log/i })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /full season player game log/i })).toBeInTheDocument();
  });

  it("shows an empty game-log state", () => {
    render(
      <PlayerProfileView
        benchmarks={benchmarks}
        games={[]}
        hasProfileError={false}
        isLoading={false}
        player={player}
        selectedSeason="2025-26"
        similarPlayers={[]}
        splits={undefined}
        summary={summary}
        trends={trends}
      />,
    );

    expect(screen.getByText("No game logs")).toBeInTheDocument();
    expect(screen.getByText("No recent games")).toBeInTheDocument();
    expect(screen.getByText("No similar players")).toBeInTheDocument();
  });
});

function buildGame({
  id,
  date,
  points,
  isHome,
  result,
  days,
}: {
  id: number;
  date: string;
  points: number;
  isHome: boolean;
  result: "W" | "L";
  days: number | null;
}): GameLogItem {
  return {
    id,
    game_id: id,
    nba_game_id: `002250000${id}`,
    game_date: date,
    season: "2025-26",
    matchup: isHome ? "GSW vs. LAL" : "GSW @ LAL",
    location: isHome ? "home" : "away",
    opponent: {
      id: 2,
      nba_team_id: 1610612747,
      abbreviation: "LAL",
      city: "Los Angeles",
      name: "Lakers",
      conference: "West",
      division: "Pacific",
    },
    result,
    days_since_previous_game: days,
    minutes: 32 + id,
    points,
    rebounds: 4,
    assists: 7,
    steals: 1,
    blocks: 0,
    turnovers: 2,
    personal_fouls: 1,
    field_goals_made: 9,
    field_goals_attempted: 18,
    three_pointers_made: 4,
    three_pointers_attempted: 10,
    free_throws_made: 4,
    free_throws_attempted: 4,
    plus_minus: 8,
    calculated_true_shooting_percentage: 0.62,
  };
}
