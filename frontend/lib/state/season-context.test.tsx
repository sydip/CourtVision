import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SeasonProvider, useSeason } from "@/lib/state/season-context";

const getSeasonsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/courtvision", () => ({ getSeasons: getSeasonsMock }));

function Consumer() {
  const { season, seasons, setSeason, isSupported } = useSeason();
  return (
    <>
      <output>{isSupported ? season : `${season} unavailable`}</output>
      <select
        aria-label="Test season"
        onChange={(event) => setSeason(event.target.value)}
        value={season}
      >
        {seasons.map((value) => (
          <option key={value}>{value}</option>
        ))}
      </select>
    </>
  );
}

describe("SeasonProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/players");
    getSeasonsMock.mockReset().mockResolvedValue({
      seasons: ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"],
    });
  });

  afterEach(cleanup);

  it("persists a changed season in the URL and local storage", async () => {
    render(
      <SeasonProvider>
        <Consumer />
      </SeasonProvider>,
    );
    await waitFor(() => expect(screen.getByLabelText("Test season")).toHaveValue("2025-26"));

    fireEvent.change(screen.getByLabelText("Test season"), { target: { value: "2021-22" } });

    expect(window.location.search).toBe("?season=2021-22");
    expect(window.localStorage.getItem("courtvision:selected-season")).toBe("2021-22");
  });

  it("keeps the canonical selector usable while the seasons request is pending", () => {
    getSeasonsMock.mockReturnValue(new Promise(() => undefined));
    render(
      <SeasonProvider>
        <Consumer />
      </SeasonProvider>,
    );

    expect(screen.getByLabelText("Test season")).toHaveValue("2025-26");
    expect(screen.getByRole("option", { name: "2021-22" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "2026-27" })).not.toBeInTheDocument();
  });

  it("tracks URL season changes from browser navigation", async () => {
    render(
      <SeasonProvider>
        <Consumer />
      </SeasonProvider>,
    );
    await waitFor(() => expect(screen.getByLabelText("Test season")).toHaveValue("2025-26"));

    window.history.pushState({}, "", "/players?season=2023-24");
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => expect(screen.getByLabelText("Test season")).toHaveValue("2023-24"));
  });

  it("does not silently replace an unsupported URL season", async () => {
    window.history.replaceState({}, "", "/players?season=2020-21");
    render(
      <SeasonProvider>
        <Consumer />
      </SeasonProvider>,
    );

    expect(await screen.findByText("2020-21 unavailable")).toBeInTheDocument();
    expect(window.location.search).toBe("?season=2020-21");
  });
});
