import { describe, expect, it } from "vitest";

import type { PlayoffRoundResponse } from "@/lib/api/schemas";
import { mergeStoredFirstRound } from "@/lib/playoff-boxscore-merge";
import type { Series } from "@/lib/playoffs-2026";

const source: Series[] = [
  {
    round: "First Round",
    top: { id: 1, wins: 0 },
    bottom: { id: 2, wins: 1 },
    winnerId: 2,
    games: [{ n: 1, date: "Apr 19", scores: { 1: 101, 2: 112 }, winnerId: 2 }],
  },
  {
    round: "First Round",
    top: { id: 3, wins: 4 },
    bottom: { id: 4, wins: 2 },
    winnerId: 3,
    games: [{ n: 1, date: "Apr 18", scores: { 3: 107, 4: 98 }, winnerId: 3 }],
  },
];

const stored = {
  season: "2025-26",
  round: "First Round",
  stored_series: 1,
  stored_games: 1,
  expected_games: 48,
  coverage_complete: false,
  data_source: "fixture",
  series: [
    {
      id: 10,
      conference: "East",
      winner: team(2, "ORL", "Orlando"),
      loser: team(1, "DET", "Detroit"),
      winner_wins: 1,
      loser_wins: 0,
      games: [
        {
          id: 20,
          game_number: 1,
          home_team: team(1, "DET", "Detroit"),
          away_team: team(2, "ORL", "Orlando"),
          home_score: 101,
          away_score: 112,
          overtime: false,
          data_note: "Official team totals; one source line is unavailable.",
          team_box_scores: [
            {
              team: team(1, "DET", "Detroit"),
              points: 101,
              rebounds: 51,
              assists: 19,
              steals: 9,
              blocks: 6,
              turnovers: 14,
              field_goals_made: 31,
              field_goals_attempted: 77,
              three_pointers_made: 10,
              three_pointers_attempted: 32,
              free_throws_made: 29,
              free_throws_attempted: 38,
              players: [
                {
                  player_id: 5,
                  player_name: "Cade Cunningham",
                  points: 39,
                  rebounds: 5,
                  assists: 4,
                  steals: 0,
                  blocks: 0,
                  turnovers: 3,
                  field_goals_made: 13,
                  field_goals_attempted: 27,
                  three_pointers_made: 3,
                  three_pointers_attempted: 8,
                  free_throws_made: 10,
                  free_throws_attempted: 11,
                  plus_minus: -1,
                },
              ],
            },
          ],
        },
      ],
    },
  ],
} satisfies PlayoffRoundResponse;

describe("mergeStoredFirstRound", () => {
  it("hydrates supplied series and leaves unsupplied matchups score-only", () => {
    const merged = mergeStoredFirstRound(source, stored);

    expect(merged[0].games[0].boxes?.[1].tot[0]).toBe("31-77");
    expect(merged[0].games[0].boxes?.[1].players[0]).toEqual([
      "Cade Cunningham",
      39,
      5,
      4,
      0,
      0,
      3,
      "13-27",
      "3-8",
      "10-11",
      "-1",
    ]);
    expect(merged[0].games[0].note).toContain("Official team totals");
    expect(merged[1]).toBe(source[1]);
  });
});

function team(nbaTeamId: number, abbreviation: string, city: string) {
  return {
    id: nbaTeamId,
    nba_team_id: nbaTeamId,
    abbreviation,
    city,
    name: `${city} Team`,
    conference: null,
    division: null,
  };
}
