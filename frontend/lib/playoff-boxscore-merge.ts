import type { PlayoffRoundResponse } from "@/lib/api/schemas";
import type { Game, PlayerRow, Series, TeamBox } from "@/lib/playoffs-2026";

export function mergeStoredFirstRound(
  bracketSeries: Series[],
  stored: PlayoffRoundResponse | null,
): Series[] {
  if (!stored) {
    return bracketSeries;
  }
  const storedByTeams = new Map(
    stored.series.map((series) => [
      seriesKey(series.winner.nba_team_id, series.loser.nba_team_id),
      series,
    ]),
  );

  return bracketSeries.map((series) => {
    const persisted = storedByTeams.get(seriesKey(series.top.id, series.bottom.id));
    if (!persisted) {
      return series;
    }
    const gamesByNumber = new Map(persisted.games.map((game) => [game.game_number, game]));
    return {
      ...series,
      games: series.games.map((game) => {
        const storedGame = gamesByNumber.get(game.n);
        if (!storedGame) {
          return game;
        }
        const scores = {
          [storedGame.home_team.nba_team_id]: storedGame.home_score,
          [storedGame.away_team.nba_team_id]: storedGame.away_score,
        };
        const winnerId =
          storedGame.home_score > storedGame.away_score
            ? storedGame.home_team.nba_team_id
            : storedGame.away_team.nba_team_id;
        const boxes = Object.fromEntries(
          storedGame.team_box_scores.map((box) => [box.team.nba_team_id, toTeamBox(box)]),
        );
        return {
          ...game,
          scores,
          winnerId,
          boxes,
          loc: storedGame.home_team.city,
          ot: storedGame.overtime,
          note: storedGame.data_note ?? undefined,
        } satisfies Game;
      }),
    };
  });
}

function toTeamBox(
  box: PlayoffRoundResponse["series"][number]["games"][number]["team_box_scores"][number],
): TeamBox {
  return {
    q: [],
    tot: [
      shotLine(box.field_goals_made, box.field_goals_attempted),
      shotLine(box.three_pointers_made, box.three_pointers_attempted),
      shotLine(box.free_throws_made, box.free_throws_attempted),
      box.rebounds,
      box.assists,
      box.steals,
      box.blocks,
      box.turnovers,
      0,
    ],
    players: box.players.map(
      (player): PlayerRow => [
        player.player_name,
        player.points,
        player.rebounds,
        player.assists,
        player.steals,
        player.blocks,
        player.turnovers,
        shotLine(player.field_goals_made, player.field_goals_attempted),
        shotLine(player.three_pointers_made, player.three_pointers_attempted),
        shotLine(player.free_throws_made, player.free_throws_attempted),
        plusMinus(player.plus_minus),
      ],
    ),
  };
}

function shotLine(made: number, attempted: number): string {
  return `${made}-${attempted}`;
}

function plusMinus(value: number | null): string {
  if (value === null) {
    return "--";
  }
  return value > 0 ? `+${value}` : `${value}`;
}

function seriesKey(firstTeamId: number, secondTeamId: number): string {
  return [firstTeamId, secondTeamId].sort((left, right) => left - right).join(":");
}
