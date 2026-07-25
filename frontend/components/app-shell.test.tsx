import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";
import type { PlayerListItem, Team } from "@/lib/api/schemas";

const getPlayersMock = vi.hoisted(() => vi.fn());
const getTeamsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/hoopsiq", () => ({
  getPlayers: getPlayersMock,
  getTeams: getTeamsMock,
}));

const lebron: PlayerListItem = {
  id: 2,
  nba_player_id: 2544,
  slug: "lebron-james-2544",
  full_name: "LeBron James",
  first_name: "LeBron",
  last_name: "James",
  position: "Forward",
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

const warriors: Team = {
  id: 1,
  nba_team_id: 1610612744,
  abbreviation: "GSW",
  city: "Golden State",
  name: "Warriors",
  conference: "West",
  division: "Pacific",
};

describe("AppShell", () => {
  beforeEach(() => {
    getPlayersMock.mockReset();
    getTeamsMock.mockReset();
    getTeamsMock.mockResolvedValue({ teams: [lakers, warriors] });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders a global player lookup in the top navigation", () => {
    render(
      <AppShell active="Players">
        <div>Profile content</div>
      </AppShell>,
    );

    expect(screen.getByRole("search")).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Global player and team lookup" }),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search players or teams")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "CourtVision home" }).at(-1)).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getAllByRole("link", { name: "Players" })[0]).toHaveAttribute("href", "/players");
    expect(screen.getAllByRole("link", { name: "Teams" })[0]).toHaveAttribute("href", "/rosters");
  });

  it("shows global player lookup results", async () => {
    getPlayersMock.mockResolvedValue({
      items: [lebron],
      meta: {
        limit: 6,
        offset: 0,
        total: 1,
        next_offset: null,
        previous_offset: null,
      },
    });

    render(
      <AppShell active="Players">
        <div>Profile content</div>
      </AppShell>,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "Global player and team lookup" }), {
      target: { value: "lebron" },
    });

    await waitFor(() => {
      expect(getPlayersMock).toHaveBeenCalledWith({ q: "lebron", limit: 6 });
    });
    expect(await screen.findByRole("option", { name: /LeBron James/i })).toHaveAttribute(
      "href",
      "/players/2544",
    );
  });

  it("shows matching teams and links to their roster page", async () => {
    getPlayersMock.mockResolvedValue({
      items: [],
      meta: { limit: 6, offset: 0, total: 0, next_offset: null, previous_offset: null },
    });

    render(
      <AppShell active="Players">
        <div>Profile content</div>
      </AppShell>,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "Global player and team lookup" }), {
      target: { value: "lakers" },
    });

    expect(await screen.findByRole("option", { name: /Los Angeles Lakers/i })).toHaveAttribute(
      "href",
      "/rosters?team=1610612747",
    );
  });
});
