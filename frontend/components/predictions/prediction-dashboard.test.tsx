import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PredictionDashboard } from "@/components/predictions/prediction-dashboard";
import {
  getAllNbaPrediction,
  getFinalsWinnerPrediction,
  getPredictionAvailability,
  getSeasonStandingsPrediction,
} from "@/lib/api/courtvision";
import type { PredictionAvailability } from "@/lib/api/schemas";

vi.mock("@/lib/api/courtvision", () => ({
  getPredictionAvailability: vi.fn(),
  getAllNbaPrediction: vi.fn(),
  getSeasonStandingsPrediction: vi.fn(),
  getFinalsWinnerPrediction: vi.fn(),
}));

const availability: PredictionAvailability = {
  predictionSeason: "2026-27",
  enabled: true,
  supportedPredictionTypes: ["all_nba", "standings", "finals_winner"],
  blockedSeasons: ["2025-26"],
  message: "Predictions are only available for the 2026-27 season.",
};
const allNba = {
  season: "2026-27" as const,
  predictionType: "all_nba" as const,
  model: {
    name: "logistic_regression_all_nba",
    version: "0.1.0",
    trainingSeasons: ["2021-22", "2025-26"],
  },
  data: [
    {
      playerId: 1,
      playerName: "Sample Player",
      team: "Sample Team",
      predictedRank: 1,
      probability: 0.72,
      projectedTeam: "First Team",
      topFactors: ["Elite scoring profile"],
      warnings: [],
    },
  ],
  disclaimer: "Experimental model estimate, not an official prediction or betting recommendation.",
};
const standings = {
  season: "2026-27" as const,
  predictionType: "standings" as const,
  east: [
    {
      rank: 1,
      teamId: 1,
      teamName: "Boston Celtics",
      conference: "East",
      predictedWins: 56,
      predictedLosses: 26,
      playoffProbability: 0.91,
      confidence: 0.68,
      topFactors: ["Net rating"],
    },
  ],
  west: [
    {
      rank: 1,
      teamId: 2,
      teamName: "Oklahoma City Thunder",
      conference: "West",
      predictedWins: 58,
      predictedLosses: 24,
      playoffProbability: 0.94,
      confidence: 0.73,
      topFactors: [],
    },
  ],
  disclaimer: "Experimental model estimate, not an official prediction or betting recommendation.",
};
const finals = {
  season: "2026-27" as const,
  predictionType: "finals_winner" as const,
  predictedChampion: {
    teamId: 2,
    teamName: "Oklahoma City Thunder",
    probability: 0.18,
    topFactors: [],
  },
  contenders: [{ teamId: 2, teamName: "Oklahoma City Thunder", probability: 0.18, topFactors: [] }],
  disclaimer: "Experimental model estimate, not an official prediction or betting recommendation.",
};

beforeEach(() => {
  vi.mocked(getPredictionAvailability).mockResolvedValue(availability);
  vi.mocked(getAllNbaPrediction).mockResolvedValue(allNba);
  vi.mocked(getSeasonStandingsPrediction).mockResolvedValue(standings);
  vi.mocked(getFinalsWinnerPrediction).mockResolvedValue(finals);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PredictionDashboard", () => {
  it("renders validated All-NBA, standings, Finals, methodology, and disclaimer results", async () => {
    render(<PredictionDashboard />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading 2026–27 model estimates");
    expect(await screen.findByText("Sample Player")).toBeInTheDocument();
    expect(screen.getAllByText("Oklahoma City Thunder").length).toBeGreaterThan(0);
    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();
    expect(screen.getByText("How estimates are produced")).toBeInTheDocument();
    expect(screen.getByText("Model estimates, not facts")).toBeInTheDocument();
    expect(screen.getByText("72.0%")).toBeInTheDocument();
    expect(
      screen.getAllByText(/not an official prediction or betting recommendation/).length,
    ).toBeGreaterThanOrEqual(2);
  });

  it("renders an API error state", async () => {
    vi.mocked(getAllNbaPrediction).mockRejectedValue(new Error("No completed run is available."));
    render(<PredictionDashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No completed run is available.");
    expect(screen.getByText("Boston Celtics")).toBeInTheDocument();
  });

  it("renders explicit empty result states", async () => {
    vi.mocked(getAllNbaPrediction).mockResolvedValue({ ...allNba, data: [] });
    vi.mocked(getSeasonStandingsPrediction).mockResolvedValue({ ...standings, east: [], west: [] });
    vi.mocked(getFinalsWinnerPrediction).mockResolvedValue({
      ...finals,
      predictedChampion: null,
      contenders: [],
    });
    render(<PredictionDashboard />);
    expect((await screen.findAllByText("No model results")).length).toBeGreaterThanOrEqual(4);
  });
});
