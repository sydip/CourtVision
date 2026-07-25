import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchBackendHealth } from "./health";

describe("fetchBackendHealth", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns backend health data when the API responds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          status: "ok",
          service: "hoopsiq-api",
          nba_season: "2025-26",
          database_configured: true,
          raw_data_dir: "../data/raw",
          request_timeout_seconds: 20,
          checked_at: "2026-06-25T15:00:00Z",
        }),
      })),
    );

    const result = await fetchBackendHealth("http://localhost:8000");

    expect(result.ok).toBe(true);
    expect(result.data?.service).toBe("hoopsiq-api");
    expect(result.data?.nba_season).toBe("2025-26");
  });

  it("reports an unavailable API when fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("connection refused");
      }),
    );

    const result = await fetchBackendHealth("http://localhost:8000");

    expect(result.ok).toBe(false);
    expect(result.message).toContain("Backend health endpoint is not reachable");
  });
});
