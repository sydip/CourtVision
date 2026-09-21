import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getAllNbaPrediction,
  getFinalsWinnerPrediction,
  getPredictionAvailability,
  getSeasonStandingsPrediction,
} from "@/lib/api/courtvision";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("prediction API client", () => {
  it.each([
    [
      getPredictionAvailability,
      "/api/predictions/availability",
      {
        predictionSeason: "2026-27",
        enabled: true,
        supportedPredictionTypes: ["all_nba"],
        blockedSeasons: ["2025-26"],
        message: "Predictions are only available for the 2026-27 season.",
      },
    ],
    [
      getAllNbaPrediction,
      "/api/predictions/2026-27/all-nba",
      {
        season: "2026-27",
        predictionType: "all_nba",
        model: { name: "model", version: "0.1.0", trainingSeasons: ["2021-22"] },
        data: [],
        disclaimer: "Experimental model estimate.",
      },
    ],
    [
      getSeasonStandingsPrediction,
      "/api/predictions/2026-27/standings",
      {
        season: "2026-27",
        predictionType: "standings",
        east: [],
        west: [],
        disclaimer: "Experimental model estimate.",
      },
    ],
    [
      getFinalsWinnerPrediction,
      "/api/predictions/2026-27/finals-winner",
      {
        season: "2026-27",
        predictionType: "finals_winner",
        predictedChampion: null,
        contenders: [],
        disclaimer: "Experimental model estimate.",
      },
    ],
  ])("validates the fixed 2026-27 endpoint", async (request, path, payload) => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    await expect(request()).resolves.toMatchObject(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000${path}`,
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("rejects a response labeled as a historical prediction", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({
              season: "2025-26",
              predictionType: "all_nba",
              model: { name: "model", version: "0.1.0", trainingSeasons: [] },
              data: [],
              disclaimer: "Estimate",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        ),
    );
    await expect(getAllNbaPrediction()).rejects.toThrow();
  });
});
