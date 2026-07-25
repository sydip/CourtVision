import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AssistantDashboard } from "@/components/assistant-dashboard";
import { getAwardPrediction } from "@/lib/api/hoopsiq";

vi.mock("@/lib/api/hoopsiq", () => ({
  getAwardPrediction: vi.fn(),
  getStandingsPrediction: vi.fn(),
  sendAssistantMessage: vi.fn(),
}));

vi.stubGlobal(
  "ResizeObserver",
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AssistantDashboard", () => {
  it("renders grounded chat and projection controls", () => {
    render(<AssistantDashboard />);

    expect(screen.getByRole("heading", { name: "Jordan" })).toBeInTheDocument();
    expect(screen.getByLabelText("Message Jordan")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "MVP" })).toBeInTheDocument();
    expect(screen.getByText("Grounding enforced")).toBeInTheDocument();
    expect(screen.getByText("Projection workspace")).toBeInTheDocument();
  });

  it("loads and displays an explainable award projection", async () => {
    vi.mocked(getAwardPrediction).mockResolvedValue({
      prediction_id: 1,
      award_type: "MVP",
      target_season: "2025-26",
      source_season: "2025-26",
      model_version: "test-model",
      candidates: [
        {
          rank: 1,
          entity_id: 1,
          name: "Sample Player",
          team: "Sample Team",
          position: "Guard",
          probability: 0.34,
          score: 2.1,
          features: { points_per_game: 28.4 },
          feature_attributions: [
            {
              feature: "points_per_game",
              raw_value: 28.4,
              normalized_value: 2.2,
              weight: 0.24,
              contribution: 0.528,
            },
          ],
          warnings: [],
        },
      ],
      warnings: [],
      methodology: "Transparent test projection. Probabilities are not guarantees.",
    });
    render(<AssistantDashboard />);

    fireEvent.click(screen.getByRole("button", { name: "MVP" }));

    expect(await screen.findByText("Sample Player")).toBeInTheDocument();
    expect(screen.getByText("34.0%")).toBeInTheDocument();
    expect(screen.getByText("Why the model leads here")).toBeInTheDocument();
  });
});
