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
  it("renders the hero, the database row and the category row", () => {
    const { container } = render(
      <HomeDashboardView
        dataStatus={dataStatus}
        hasDataStatusError={false}
        isDataStatusLoading={false}
      />,
    );

    expect(container.querySelector(".basketball-icon")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Explore\. Analyze\. Elevate\./i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Your all-in-one NBA database for in-depth research and analysis."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Explore Players/i })).toHaveAttribute(
      "href",
      "/players",
    );

    expect(screen.getByRole("heading", { name: "Explore the Database" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Browse by Category" })).toBeInTheDocument();
    expect(container.querySelectorAll(".home-database-card")).toHaveLength(6);
    expect(container.querySelectorAll(".home-category-card")).toHaveLength(4);
    expect(container.querySelector(".dashboard-shell")).toHaveClass("topbar-shell");
    expect(container.querySelector(".sidebar")).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Section navigation" })).toBeInTheDocument();

    // Every card must resolve to a section that actually exists.
    for (const card of Array.from(container.querySelectorAll<HTMLAnchorElement>("a[href]"))) {
      expect(card.getAttribute("href")).not.toBe("/offseason");
    }

    // The hero keeps surfacing live database status.
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
