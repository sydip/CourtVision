import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PlayersDashboard } from "@/components/players-dashboard";
import type { DataStatus, PlayerListItem, PlayerSeasonSummary, Team } from "@/lib/api/schemas";

const getAllPlayersMock = vi.hoisted(() => vi.fn());
const getDataStatusMock = vi.hoisted(() => vi.fn());
const getSeasonSummariesMock = vi.hoisted(() => vi.fn());
const getTeamsMock = vi.hoisted(() => vi.fn());
const getPlayersMock = vi.hoisted(() => vi.fn());
const routerPushMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/hoopsiq", () => ({
  getAllPlayers: getAllPlayersMock,
  getDataStatus: getDataStatusMock,
  getSeasonSummaries: getSeasonSummariesMock,
  getTeams: getTeamsMock,
  getPlayers: getPlayersMock,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPushMock }),
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

const players: PlayerListItem[] = [
  player(201939, "Stephen Curry", "Guard", warriors),
  player(203110, "Draymond Green", "Forward", warriors),
  player(2544, "LeBron James", "Guard-Forward", lakers),
  player(1630559, "Anthony Davis", "Center", lakers),
  freeAgent(999999, "Carmelo Anthony", "Forward"),
];

const dataStatus: DataStatus = {
  current_season: "2025-26",
  player_count: players.length,
  game_count: 10,
  player_game_record_count: 100,
  last_successful_sync: null,
  last_failed_sync: null,
};

describe("PlayersDashboard", () => {
  beforeEach(() => {
    getAllPlayersMock.mockResolvedValue(players);
    getDataStatusMock.mockResolvedValue(dataStatus);
    getSeasonSummariesMock.mockResolvedValue({
      items: players.map((item) => summary(item.nba_player_id)),
    });
    getTeamsMock.mockResolvedValue({ teams: [warriors, lakers] });
    getPlayersMock.mockResolvedValue({
      items: [],
      meta: { limit: 6, offset: 0, total: 0, next_offset: null, previous_offset: null },
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the players dashboard with stat cards and a player card grid", async () => {
    render(<PlayersDashboard />);

    expect(await screen.findByRole("heading", { name: "NBA Players" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Stephen Curry/i })).toBeInTheDocument();
    });

    expect(screen.getByText("Active Players")).toBeInTheDocument();
    expect(screen.getAllByText("5").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /Stephen Curry/i })).toHaveAttribute(
      "href",
      "/players/201939",
    );

    expect(screen.queryByText(/Trending Players/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Sort By")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View All Players" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Grid" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "List" })).not.toBeInTheDocument();
    expect(screen.queryByText(/2025-26/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Showing \d+ of \d+ players/i)).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search players")).toBeInTheDocument();
  });

  it("includes free agents in the active player list", async () => {
    render(<PlayersDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Carmelo Anthony/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/FA \/ Forward/)).toBeInTheDocument();
  });

  it("shows the raw player-profile position instead of a wing/short-code label", async () => {
    render(<PlayersDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /LeBron James/i })).toBeInTheDocument();
    });

    expect(screen.getByText(/LAL \/ Guard-Forward/)).toBeInTheDocument();
    expect(screen.queryByText(/LAL \/ W/)).not.toBeInTheDocument();
  });

  it("filters the player grid by name using the search field", async () => {
    render(<PlayersDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Stephen Curry/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Search players"), {
      target: { value: "LeBron" },
    });

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /LeBron James/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole("link", { name: /Stephen Curry/i })).not.toBeInTheDocument();
  });

  it("routes to the compare page after picking two players in quick compare", async () => {
    render(<PlayersDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Stephen Curry/i })).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Quick Compare" })).toBeInTheDocument();
    const compareButton = screen.getByRole("button", { name: "Compare Players" });
    expect(compareButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Select first player"), { target: { value: "201939" } });
    fireEvent.change(screen.getByLabelText("Select second player"), { target: { value: "2544" } });

    expect(compareButton).toBeEnabled();
    fireEvent.click(compareButton);
    expect(routerPushMock).toHaveBeenCalledWith("/compare?a=201939&b=2544");
  });

  it("keeps quick compare disabled when the same player is chosen twice", async () => {
    render(<PlayersDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Stephen Curry/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Select first player"), { target: { value: "201939" } });
    fireEvent.change(screen.getByLabelText("Select second player"), { target: { value: "201939" } });

    expect(screen.getByRole("button", { name: "Compare Players" })).toBeDisabled();
    expect(screen.getByText("Pick two different players to compare.")).toBeInTheDocument();
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

function freeAgent(nbaPlayerId: number, fullName: string, position: string): PlayerListItem {
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
    team: null,
  };
}

function summary(nbaPlayerId: number): PlayerSeasonSummary {
  return {
    player_id: nbaPlayerId,
    nba_player_id: nbaPlayerId,
    season: "2025-26",
    games_played: 10,
    minutes_per_game: 32.1,
    points_per_game: nbaPlayerId === 201939 ? 27.5 : 18.2,
    rebounds_per_game: 5.5,
    assists_per_game: nbaPlayerId === 201939 ? 6.1 : 3.2,
    turnovers_per_game: 2.1,
    plus_minus_per_game: 2.4,
    true_shooting_percentage: 0.61,
    true_shooting_source: "calculated",
    usage_rate: 0.27,
    points_per_36: null,
    rebounds_per_36: null,
    assists_per_36: null,
    turnovers_per_36: null,
    analytics_rebuilt_at: null,
    analytics_warnings: [],
  };
}
