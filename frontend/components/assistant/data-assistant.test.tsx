import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DataAssistant } from "@/components/assistant/data-assistant";
import { getDataStatus, queryAssistant } from "@/lib/api/courtvision";
import { SeasonProvider } from "@/lib/state/season-context";

vi.mock("@/lib/api/courtvision", () => ({
  getSeasons: vi.fn().mockResolvedValue({ seasons: ["2021-22", "2024-25", "2025-26"] }),
  getDataStatus: vi.fn().mockResolvedValue({
    current_season: "2025-26",
    player_count: 530,
    game_count: 1230,
    player_game_record_count: 26000,
    teams: 30,
    last_successful_sync: null,
    last_failed_sync: null,
  }),
  queryAssistant: vi.fn(),
  getPredictionAvailability: vi.fn().mockResolvedValue({
    predictionSeason: "2026-27",
    enabled: true,
    supportedPredictionTypes: ["all_nba", "standings", "finals_winner"],
    blockedSeasons: ["2021-22", "2025-26"],
    message: "Predictions are only available for the 2026-27 season.",
  }),
  getAllNbaPrediction: vi.fn().mockResolvedValue({
    season: "2026-27",
    predictionType: "all_nba",
    model: { name: "model", version: "0.1.0", trainingSeasons: ["2021-22"] },
    data: [],
    disclaimer: "Experimental model estimate.",
  }),
  getSeasonStandingsPrediction: vi.fn().mockResolvedValue({
    season: "2026-27",
    predictionType: "standings",
    east: [],
    west: [],
    disclaimer: "Experimental model estimate.",
  }),
  getFinalsWinnerPrediction: vi.fn().mockResolvedValue({
    season: "2026-27",
    predictionType: "finals_winner",
    predictedChampion: null,
    contenders: [],
    disclaimer: "Experimental model estimate.",
  }),
}));

function renderAssistant() {
  return render(
    <SeasonProvider>
      <DataAssistant />
    </SeasonProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  window.history.replaceState({}, "", "/ai-assistant");
  vi.clearAllMocks();
});
afterEach(cleanup);

describe("DataAssistant", () => {
  it("renders native query, availability, and season-aware prompt sections", async () => {
    renderAssistant();
    expect(screen.getByRole("heading", { name: "CourtVision AI Assistant" })).toBeInTheDocument();
    expect(screen.getByLabelText("Ask CourtVision")).toBeInTheDocument();
    expect(screen.getByLabelText("Data availability")).toBeInTheDocument();
    expect(await screen.findByText("Predict the 2026-27 All-NBA teams.")).toBeInTheDocument();
    expect(screen.getByLabelText("Jordan forecast context")).toHaveTextContent(
      "Forecast target: 2026–27",
    );
  });

  it("sends the selected season and displays grounded evidence", async () => {
    vi.mocked(queryAssistant).mockResolvedValue({
      answer: "Devin Booker scored 28 points.",
      intent: "player_game_stats_exact",
      season: "2024-25",
      requiresClarification: false,
      evidence: [
        {
          type: "player_game_stats",
          player: "Devin Booker",
          opponent: "Los Angeles Lakers",
          gameDate: "2025-03-03",
          points: 28,
          rebounds: 5,
          assists: 7,
          source: "database",
        },
      ],
    });
    window.history.replaceState({}, "", "/ai-assistant?season=2024-25");
    renderAssistant();
    fireEvent.change(screen.getByLabelText("Ask CourtVision"), {
      target: { value: "How many points did Devin Booker score?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask CourtVision" }));
    await waitFor(() =>
      expect(queryAssistant).toHaveBeenCalledWith(
        "How many points did Devin Booker score?",
        "2024-25",
      ),
    );
    expect(await screen.findByText("Devin Booker scored 28 points.")).toBeInTheDocument();
    expect(screen.getByText("28")).toBeInTheDocument();
    expect(screen.getByText("Source: database")).toBeInTheDocument();
    expect(getDataStatus).toHaveBeenCalledWith("2024-25");
  });

  it("keeps missing data and clarification responses visible", async () => {
    vi.mocked(queryAssistant).mockResolvedValueOnce({
      answer: "Which player did you mean: Jalen Williams, Jaylin Williams?",
      intent: "player_season_stats",
      season: "2025-26",
      requiresClarification: true,
      evidence: [],
    });
    renderAssistant();
    fireEvent.change(screen.getByLabelText("Ask CourtVision"), {
      target: { value: "What did Williams average?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask CourtVision" }));
    expect(await screen.findByRole("button", { name: "Jalen Williams" })).toBeInTheDocument();
    expect(screen.getByText("No database records found")).toBeInTheDocument();
  });

  it("shows following-season predictions only inside the 2025-26 tab", async () => {
    renderAssistant();
    expect(await screen.findByLabelText("2026-27 predictions")).toBeInTheDocument();
    expect(screen.getByText("Predict the 2026-27 All-NBA teams.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Historical analysis mode")).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "2026-27" })).not.toBeInTheDocument();

    cleanup();
    window.history.replaceState({}, "", "/ai-assistant?season=2024-25");
    renderAssistant();
    expect(screen.getByLabelText("Historical analysis mode")).toBeInTheDocument();
    expect(screen.queryByLabelText("2026-27 predictions")).not.toBeInTheDocument();
    expect(screen.queryByText("Predict the 2026-27 All-NBA teams.")).not.toBeInTheDocument();
  });

  it("routes prediction prompts to the supported following-season backend", async () => {
    vi.mocked(queryAssistant).mockResolvedValue({
      answer: "Stored model estimate.",
      intent: "prediction_lookup",
      season: "2026-27",
      requiresClarification: false,
      evidence: [],
    });
    renderAssistant();
    fireEvent.click(await screen.findByText("Predict the 2026-27 All-NBA teams."));
    fireEvent.click(screen.getByRole("button", { name: "Ask CourtVision" }));

    await waitFor(() =>
      expect(queryAssistant).toHaveBeenCalledWith("Predict the 2026-27 All-NBA teams.", "2026-27"),
    );
  });
});
