import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RostersDashboard } from "@/components/rosters-dashboard";
import type {
  DataStatus,
  PlayerDetail,
  PlayerListItem,
  PlayerSeasonSummary,
  Team,
} from "@/lib/api/schemas";

const getAllPlayersMock = vi.hoisted(() => vi.fn());
const getDataStatusMock = vi.hoisted(() => vi.fn());
const getPlayerMock = vi.hoisted(() => vi.fn());
const getPlayersMock = vi.hoisted(() => vi.fn());
const getPlayerSummaryMock = vi.hoisted(() => vi.fn());
const getTeamsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/hoopsiq", () => ({
  getAllPlayers: getAllPlayersMock,
  getDataStatus: getDataStatusMock,
  getPlayer: getPlayerMock,
  getPlayers: getPlayersMock,
  getPlayerSummary: getPlayerSummaryMock,
  getTeams: getTeamsMock,
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
  player(1630228, "Jonathan Kuminga", "Forward", warriors),
  player(2544, "LeBron James", "Forward", lakers),
];

const dataStatus: DataStatus = {
  current_season: "2025-26",
  player_count: players.length,
  game_count: 10,
  player_game_record_count: 100,
  last_successful_sync: null,
  last_failed_sync: null,
};

describe("RostersDashboard", () => {
  beforeEach(() => {
    getTeamsMock.mockResolvedValue({ teams: [warriors, lakers] });
    getAllPlayersMock.mockResolvedValue(players);
    getPlayersMock.mockResolvedValue({
      items: players,
      meta: {
        limit: 1000,
        offset: 0,
        total: players.length,
        next_offset: null,
        previous_offset: null,
      },
    });
    getDataStatusMock.mockResolvedValue(dataStatus);
    getPlayerMock.mockImplementation((playerId: number) =>
      Promise.resolve(
        playerDetail(players.find((entry) => entry.nba_player_id === playerId) ?? players[0]),
      ),
    );
    getPlayerSummaryMock.mockImplementation((playerId: number) =>
      Promise.resolve(
        summary(playerId, playerId === 201939 ? 32.1 : playerId === 2544 ? 31.4 : 22.5),
      ),
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("does not show a hover preview and opens the Overview tab when a team card is clicked", async () => {
    render(<RostersDashboard />);

    expect(await screen.findByRole("heading", { name: "NBA Team Rosters" })).toBeInTheDocument();
    const warriorsCard = await screen.findByRole("button", { name: /GSW/i });

    fireEvent.mouseEnter(warriorsCard);
    expect(
      screen.queryByText(/franchise helped define several offensive eras/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("NBA Championships")).not.toBeInTheDocument();

    fireEvent.click(warriorsCard);

    expect(await screen.findByRole("heading", { name: "Golden State Warriors" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Overview" })).toHaveClass("active");
    expect(
      await screen.findByText(/franchise helped define several offensive eras/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Team History")).toBeInTheDocument();
    expect(screen.getByText("NBA Championships")).toBeInTheDocument();
    expect(screen.getByText("Head Coach")).toBeInTheDocument();
    expect(screen.getByText("Steve Kerr")).toBeInTheDocument();
  });

  it("opens a selected team's roster table from the Roster tab", async () => {
    render(<RostersDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: /LAL/i }));

    expect(await screen.findByRole("heading", { name: "Los Angeles Lakers" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Roster" }));

    expect(
      await screen.findByRole("table", { name: /Los Angeles Lakers roster/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("LeBron James").length).toBeGreaterThan(0);
    expect(screen.queryByText("Starting Lineup")).not.toBeInTheDocument();
    expect(screen.queryByText("Starter")).not.toBeInTheDocument();
    expect(screen.queryByText("Bench")).not.toBeInTheDocument();
    expect(screen.queryByText("All Players")).not.toBeInTheDocument();
    expect(screen.queryByText("Sort by MPG")).not.toBeInTheDocument();
    expect(screen.queryByText("Depth Chart")).not.toBeInTheDocument();
    expect(screen.queryByText("44")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /View Full Profile/i })).not.toBeInTheDocument();

    expect(screen.getByRole("link", { name: "LeBron James" })).toHaveAttribute(
      "href",
      "/players/2544",
    );

    const nameRow = screen.getByText("LeBron James").closest("tr");
    if (!nameRow) {
      throw new Error("Expected roster row for LeBron James");
    }
    fireEvent.mouseEnter(nameRow);

    expect(await screen.findByText("Games Played")).toBeInTheDocument();
    expect(screen.queryByText("Stored Games")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /View Full Profile/i })).not.toBeInTheDocument();
  });

  it("shows the head coach in the Overview tab without an avatar and has no Coaching Staff tab", async () => {
    render(<RostersDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: /LAL/i }));
    expect(await screen.findByRole("heading", { name: "Los Angeles Lakers" })).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Coaching Staff" })).not.toBeInTheDocument();
    expect(screen.getByText("Head Coach")).toBeInTheDocument();
    expect(screen.getByText("JJ Redick")).toBeInTheDocument();
    expect(screen.queryByText("JR")).not.toBeInTheDocument();
  });

  it("shows team leaders with the top 3 in points, assists, and rebounds", async () => {
    render(<RostersDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: /LAL/i }));
    expect(await screen.findByRole("heading", { name: "Los Angeles Lakers" })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Team Leaders" })).toBeInTheDocument();
    expect(screen.getByText("Points (PPG)")).toBeInTheDocument();
    expect(screen.getByText("Assists (APG)")).toBeInTheDocument();
    expect(screen.getByText("Rebounds (RPG)")).toBeInTheDocument();
    expect(screen.queryByText("Top Performers")).not.toBeInTheDocument();

    const leadersSection = screen.getByRole("heading", { name: "Team Leaders" }).closest("section");
    expect(leadersSection).not.toBeNull();
    expect(
      leadersSection?.querySelectorAll(".team-overview-leaders-column li").length,
    ).toBeLessThanOrEqual(9);
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

function playerDetail(basePlayer: PlayerListItem): PlayerDetail {
  return {
    ...basePlayer,
    birthdate: basePlayer.nba_player_id === 2544 ? "1984-12-30" : "1988-03-14",
    height: basePlayer.nba_player_id === 2544 ? "6-9" : "6-2",
    weight_pounds: basePlayer.nba_player_id === 2544 ? 250 : 185,
  };
}

function summary(nbaPlayerId: number, minutes: number): PlayerSeasonSummary {
  return {
    player_id: nbaPlayerId,
    nba_player_id: nbaPlayerId,
    season: "2025-26",
    games_played: 10,
    minutes_per_game: minutes,
    points_per_game: nbaPlayerId === 2544 ? 26.8 : 24.3,
    rebounds_per_game: nbaPlayerId === 2544 ? 7.8 : 4.4,
    assists_per_game: nbaPlayerId === 2544 ? 8.2 : 6.1,
    turnovers_per_game: null,
    plus_minus_per_game: null,
    true_shooting_percentage: nbaPlayerId === 2544 ? 0.611 : 0.638,
    true_shooting_source: "calculated",
    usage_rate: null,
    points_per_36: null,
    rebounds_per_36: null,
    assists_per_36: null,
    turnovers_per_36: null,
    analytics_rebuilt_at: null,
    analytics_warnings: [],
  };
}
