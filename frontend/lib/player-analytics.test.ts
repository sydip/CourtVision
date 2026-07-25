import { describe, expect, it } from "vitest";

import { buildPerformanceSeries, buildSeasonAverageSeries } from "@/lib/player-analytics";
import type { GameLogItem } from "@/lib/api/schemas";

describe("buildPerformanceSeries", () => {
  it("plots actual game-log values instead of rolling averages", () => {
    const series = buildPerformanceSeries([
      buildGame({ id: 2, date: "2026-04-10", points: 28, assists: 4, ts: 0.71 }),
      buildGame({ id: 1, date: "2026-04-08", points: 10, assists: 12, ts: 0.5 }),
      buildGame({ id: 3, date: "2026-04-12", points: 36, assists: 2, ts: null }),
    ]);

    expect(series).toMatchObject([
      {
        gameId: 1,
        points: 10,
        rebounds: 6,
        assists: 12,
        steals: 1,
        blocks: 0,
        fieldGoalPercentage: 50,
        threePointPercentage: 40,
        trueShootingPercentage: 50,
      },
      {
        gameId: 2,
        points: 28,
        rebounds: 6,
        assists: 4,
        steals: 1,
        blocks: 0,
        fieldGoalPercentage: 50,
        threePointPercentage: 40,
        trueShootingPercentage: 71,
      },
      {
        gameId: 3,
        points: 36,
        rebounds: 6,
        assists: 2,
        steals: 1,
        blocks: 0,
        fieldGoalPercentage: 50,
        threePointPercentage: 40,
        trueShootingPercentage: null,
      },
    ]);
  });

  it("builds season-to-date averages for full-season graph modals", () => {
    const series = buildSeasonAverageSeries([
      buildGame({ id: 2, date: "2026-04-10", points: 28, assists: 4, ts: 0.71 }),
      buildGame({ id: 1, date: "2026-04-08", points: 10, assists: 12, ts: 0.5 }),
      buildGame({ id: 3, date: "2026-04-12", points: 36, assists: 2, ts: null }),
    ]);

    expect(series).toMatchObject([
      {
        gameId: 1,
        points: 10,
        rebounds: 6,
        assists: 12,
        steals: 1,
        blocks: 0,
        fieldGoalPercentage: 50,
        threePointPercentage: 40,
      },
      {
        gameId: 2,
        points: 19,
        rebounds: 6,
        assists: 8,
        steals: 1,
        blocks: 0,
        fieldGoalPercentage: 50,
        threePointPercentage: 40,
      },
      {
        gameId: 3,
        points: 74 / 3,
        rebounds: 6,
        assists: 6,
        steals: 1,
        blocks: 0,
        fieldGoalPercentage: 50,
        threePointPercentage: 40,
      },
    ]);
  });
});

function buildGame({
  id,
  date,
  points,
  assists,
  ts,
}: {
  id: number;
  date: string;
  points: number;
  assists: number;
  ts: number | null;
}): GameLogItem {
  return {
    id,
    game_id: id,
    nba_game_id: `00225000${id}`,
    game_date: date,
    season: "2025-26",
    matchup: "LAL vs. GSW",
    location: "home",
    opponent: null,
    result: "W",
    days_since_previous_game: null,
    minutes: 32,
    points,
    rebounds: 6,
    assists,
    steals: 1,
    blocks: 0,
    turnovers: 2,
    personal_fouls: 1,
    field_goals_made: 8,
    field_goals_attempted: 16,
    three_pointers_made: 2,
    three_pointers_attempted: 5,
    free_throws_made: 4,
    free_throws_attempted: 4,
    plus_minus: 3,
    calculated_true_shooting_percentage: ts,
  };
}
