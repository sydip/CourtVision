import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DraftDashboard } from "@/components/draft-dashboard";
import { getDraft } from "@/lib/api/hoopsiq";

vi.mock("@/lib/api/hoopsiq", () => ({
  getDraft: vi.fn(),
  getPlayers: vi.fn().mockResolvedValue({
    items: [],
    meta: { limit: 6, offset: 0, total: 0, next_offset: null, previous_offset: null },
  }),
  getTeams: vi.fn().mockResolvedValue({ teams: [] }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DraftDashboard", () => {
  it("shows separate first- and second-round draft boards", async () => {
    vi.mocked(getDraft).mockResolvedValue({
      draft_year: 2026,
      event_dates: "June 23-24, 2026",
      venue: "Barclays Center",
      location: "Brooklyn, New York",
      total_picks: 2,
      data_source: "test",
      picks: [
        {
          id: 1,
          draft_year: 2026,
          round: 1,
          overall_pick: 1,
          player_name: "AJ Dybantsa",
          school_country: "BYU",
          transaction_note: null,
          team: team(1, "WAS", "Washington", "Wizards"),
        },
        {
          id: 31,
          draft_year: 2026,
          round: 2,
          overall_pick: 31,
          player_name: "Bruce Thornton",
          school_country: "Ohio State",
          transaction_note: "traded from NYK",
          team: team(2, "HOU", "Houston", "Rockets"),
        },
      ],
    });

    render(<DraftDashboard />);

    const firstRound = await screen.findByRole("tabpanel");
    expect(within(firstRound).getByText("AJ Dybantsa")).toBeInTheDocument();
    expect(within(firstRound).queryByText("Bruce Thornton")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Round 2/i }));

    const secondRound = await screen.findByRole("tabpanel");
    expect(within(secondRound).getByText("Bruce Thornton")).toBeInTheDocument();
    expect(within(secondRound).getByText("traded from NYK")).toBeInTheDocument();
    expect(within(secondRound).queryByText("AJ Dybantsa")).not.toBeInTheDocument();
  });
});

function team(id: number, abbreviation: string, city: string, name: string) {
  return {
    id,
    nba_team_id: 1_610_610_000 + id,
    abbreviation,
    city,
    name,
    conference: "West",
    division: "Test",
  };
}
