import { afterEach, describe, expect, it, vi } from "vitest";

import { queryAssistant } from "@/lib/api/courtvision";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("queryAssistant", () => {
  it("posts the question, season, and page context", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ answer: "Stored answer", intent: "player_season_stats", season: "2021-22", evidence: [], requiresClarification: false }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await queryAssistant("What did the player average?", "2021-22");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/assistant/query", expect.objectContaining({ method: "POST", body: JSON.stringify({ question: "What did the player average?", season: "2021-22", context: { currentPage: "ai-assistant" } }) }));
  });
});
