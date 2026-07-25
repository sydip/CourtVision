import type { GameLogItem, PlayerBenchmarks } from "@/lib/api/schemas";

export type RollingWindow = "rolling5" | "rolling10";

export type PerformancePoint = {
  gameId: number;
  label: string;
  opponent: string;
  points: number;
  rebounds: number;
  assists: number;
  steals: number;
  blocks: number;
  fieldGoalPercentage: number | null;
  threePointPercentage: number | null;
  trueShootingPercentage: number | null;
};

export type RestSplit = {
  key: string;
  label: string;
  games: number;
  pointsPerGame: number | null;
  reboundsPerGame: number | null;
  assistsPerGame: number | null;
  minutesPerGame: number | null;
  trueShootingPercentage: number | null;
};

export type PercentileRow = {
  key: string;
  label: string;
  value: number | null;
  higherIsBetter: boolean;
};

const percentileMetrics = [
  ["points_per_game", "Points", true],
  ["assists_per_game", "Assists", true],
  ["rebounds_per_game", "Rebounds", true],
  ["plus_minus_per_game", "Plus / Minus", true],
  ["field_goal_percentage", "FG%", true],
  ["three_point_percentage", "3PT%", true],
  ["true_shooting_percentage", "TS%", true],
  ["blocks_per_game", "Blocks", true],
  ["steals_per_game", "Steals", true],
] as const;

export function buildPerformanceSeries(games: GameLogItem[]): PerformancePoint[] {
  const orderedGames = [...games].sort((left, right) =>
    left.game_date.localeCompare(right.game_date),
  );

  return orderedGames.map((game) => ({
    gameId: game.id,
    label: formatChartDate(game.game_date),
    opponent: game.opponent?.abbreviation ?? "TBD",
    points: game.points,
    rebounds: game.rebounds,
    assists: game.assists,
    steals: game.steals,
    blocks: game.blocks,
    fieldGoalPercentage: toPercentRatio(game.field_goals_made, game.field_goals_attempted),
    threePointPercentage: toPercentRatio(game.three_pointers_made, game.three_pointers_attempted),
    trueShootingPercentage: toPercentValue(game.calculated_true_shooting_percentage),
  }));
}

export function buildSeasonAverageSeries(games: GameLogItem[]): PerformancePoint[] {
  const orderedGames = [...games].sort((left, right) =>
    left.game_date.localeCompare(right.game_date),
  );
  const totals = {
    points: 0,
    rebounds: 0,
    assists: 0,
    steals: 0,
    blocks: 0,
    fieldGoalsMade: 0,
    fieldGoalsAttempted: 0,
    threePointersMade: 0,
    threePointersAttempted: 0,
    freeThrowsAttempted: 0,
  };

  return orderedGames.map((game, index) => {
    const gamesPlayed = index + 1;
    totals.points += game.points;
    totals.rebounds += game.rebounds;
    totals.assists += game.assists;
    totals.steals += game.steals;
    totals.blocks += game.blocks;
    totals.fieldGoalsMade += game.field_goals_made;
    totals.fieldGoalsAttempted += game.field_goals_attempted;
    totals.threePointersMade += game.three_pointers_made;
    totals.threePointersAttempted += game.three_pointers_attempted;
    totals.freeThrowsAttempted += game.free_throws_attempted;

    return {
      gameId: game.id,
      label: formatChartDate(game.game_date),
      opponent: game.opponent?.abbreviation ?? "TBD",
      points: totals.points / gamesPlayed,
      rebounds: totals.rebounds / gamesPlayed,
      assists: totals.assists / gamesPlayed,
      steals: totals.steals / gamesPlayed,
      blocks: totals.blocks / gamesPlayed,
      fieldGoalPercentage: toPercentRatio(totals.fieldGoalsMade, totals.fieldGoalsAttempted),
      threePointPercentage: toPercentRatio(totals.threePointersMade, totals.threePointersAttempted),
      trueShootingPercentage: toTrueShootingPercent(
        totals.points,
        totals.fieldGoalsAttempted,
        totals.freeThrowsAttempted,
      ),
    };
  });
}

export function buildRestSplits(games: GameLogItem[]): RestSplit[] {
  const buckets = [
    { key: "first_game", label: "First game" },
    { key: "back_to_back", label: "Back-to-back" },
    { key: "one_day_rest", label: "One day of rest" },
    { key: "two_or_more_days_rest", label: "Two or more days" },
  ];

  return buckets.map((bucket) => {
    const matchingGames = games.filter(
      (game) => getRestCategory(game.days_since_previous_game) === bucket.key,
    );

    return {
      ...bucket,
      games: matchingGames.length,
      pointsPerGame: average(matchingGames.map((game) => game.points)),
      reboundsPerGame: average(matchingGames.map((game) => game.rebounds)),
      assistsPerGame: average(matchingGames.map((game) => game.assists)),
      minutesPerGame: average(matchingGames.map((game) => game.minutes)),
      trueShootingPercentage: average(
        matchingGames.map((game) => game.calculated_true_shooting_percentage),
      ),
    };
  });
}

export function getPositionPercentiles(benchmarks: PlayerBenchmarks | undefined): PercentileRow[] {
  return percentileMetrics.map(([key, label, higherIsBetter]) => ({
    key,
    label,
    higherIsBetter,
    value: getNumericValue(benchmarks?.position_percentiles[key]),
  }));
}

export function getNumericValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function getRestCategory(daysSincePreviousGame: number | null): RestSplit["key"] {
  if (daysSincePreviousGame === null) {
    return "first_game";
  }
  if (daysSincePreviousGame === 1) {
    return "back_to_back";
  }
  if (daysSincePreviousGame === 2) {
    return "one_day_rest";
  }
  return "two_or_more_days_rest";
}

function average(values: Array<number | null | undefined>): number | null {
  const numericValues = values.filter((value): value is number => typeof value === "number");
  if (numericValues.length === 0) {
    return null;
  }
  return numericValues.reduce((total, value) => total + value, 0) / numericValues.length;
}

function toPercentValue(value: number | null | undefined): number | null {
  return typeof value === "number" ? value * 100 : null;
}

function toPercentRatio(made: number, attempted: number): number | null {
  if (attempted === 0) {
    return null;
  }
  return (made / attempted) * 100;
}

function toTrueShootingPercent(
  points: number,
  fieldGoalAttempts: number,
  freeThrowAttempts: number,
): number | null {
  const denominator = 2 * (fieldGoalAttempts + 0.44 * freeThrowAttempts);
  if (denominator === 0) {
    return null;
  }
  return (points / denominator) * 100;
}

function formatChartDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
