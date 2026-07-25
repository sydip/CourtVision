import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";

import { HomeDashboardView } from "@/components/home-dashboard";
import type { DataStatus } from "@/lib/api/schemas";

const dataStatus: DataStatus = {
  current_season: "2025-26",
  player_count: 4,
  game_count: 44,
  player_game_record_count: 176,
  last_successful_sync: {
    id: 1,
    source: "fixture",
    status: "completed",
    finished_at: "2026-06-30T18:36:17.000Z",
    fetched_count: 176,
    inserted_count: 176,
    updated_count: 0,
    rejected_count: 0,
    error_message: null,
  },
  last_failed_sync: null,
};

describe("HomeDashboardView", () => {
  it("renders the welcome dashboard with the hero icon and primary actions", () => {
    const { container } = render(
      <HomeDashboardView
        dataStatus={dataStatus}
        hasDataStatusError={false}
        isDataStatusLoading={false}
      />,
    );

    expect(container.querySelector(".basketball-icon")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Welcome to CourtVision/i })).toBeInTheDocument();
    expect(screen.getByText("Your all-in-one NBA analytics platform.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View Standings/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Compare Players/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View Rosters/i })).toHaveAttribute("href", "/rosters");
    expect(screen.getByText(/4 stored players/i)).toBeInTheDocument();
  });

  it("shows data status fallback text when status is unavailable", () => {
    render(
      <HomeDashboardView
        dataStatus={undefined}
        hasDataStatusError={true}
        isDataStatusLoading={false}
      />,
    );

    expect(screen.getByText("Data status unavailable")).toBeInTheDocument();
  });
});
