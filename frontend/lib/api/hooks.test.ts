import { describe, expect, it } from "vitest";

import { queryKeys } from "@/lib/api/hooks";

describe("season-aware query keys", () => {
  it("isolates list and detail caches by season", () => {
    expect(queryKeys.players("2021-22", "curry", 8)).toEqual([
      "players", "2021-22", "curry", 8,
    ]);
    expect(queryKeys.player(201939, "2025-26")).toEqual([
      "player", 201939, "2025-26",
    ]);
    expect(queryKeys.dataStatus("2024-25")).toEqual(["data-status", "2024-25"]);
  });
});
