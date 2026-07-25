"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { TeamLogoMark, getTeamTheme, getTeamThemeStyle } from "@/components/rosters-dashboard";
import { getPlayoffRound, getTeams } from "@/lib/api/hoopsiq";
import type { PlayoffRoundResponse, Team } from "@/lib/api/schemas";
import { mergeStoredFirstRound } from "@/lib/playoff-boxscore-merge";
import {
  championId,
  eastConfFinal,
  eastFirstRound,
  eastSemis,
  finals,
  finalsMvp,
  playIn,
  westConfFinal,
  westFirstRound,
  westSemis,
  type Game,
  type PlayerRow,
  type Series,
  type TeamBox,
} from "@/lib/playoffs-2026";

type Side = "west" | "east";

export function PlayoffsBracket() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [firstRoundData, setFirstRoundData] = useState<PlayoffRoundResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [activeSeries, setActiveSeries] = useState<Series | null>(null);
  const [activeGame, setActiveGame] = useState<Game | null>(null);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setHasError(false);

    Promise.all([getTeams(), getPlayoffRound()])
      .then(([teamsResponse, playoffResponse]) => {
        if (isActive) {
          setTeams(teamsResponse.teams);
          setFirstRoundData(playoffResponse);
        }
      })
      .catch(() => {
        if (isActive) {
          setHasError(true);
        }
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      if (activeGame) {
        setActiveGame(null);
      } else if (activeSeries) {
        setActiveSeries(null);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeGame, activeSeries]);

  const byId = useMemo(() => new Map(teams.map((team) => [team.nba_team_id, team])), [teams]);
  const champion = byId.get(championId);
  const storedWestFirstRound = useMemo(
    () => mergeStoredFirstRound(westFirstRound, firstRoundData),
    [firstRoundData],
  );
  const storedEastFirstRound = useMemo(
    () => mergeStoredFirstRound(eastFirstRound, firstRoundData),
    [firstRoundData],
  );

  function openSeries(next: Series) {
    setActiveGame(null);
    setActiveSeries(next);
  }

  return (
    <AppShell active="Playoffs" variant="topbar">
      <div className="playoffs-page">
        <header className="playoffs-header">
          <div>
            <h1>NBA Playoffs</h1>
            <p>2026 Postseason Results</p>
          </div>
          <span className="playoffs-subnote">
            {firstRoundData
              ? `${firstRoundData.stored_games} of ${firstRoundData.expected_games} first-round box scores stored`
              : "Click a series, then select a game for its box score"}
          </span>
        </header>

        {isLoading ? (
          <div className="playoffs-empty">Loading bracket…</div>
        ) : hasError ? (
          <div className="playoffs-empty">Bracket data is unavailable right now.</div>
        ) : (
          <>
            <div className="bracket-scroll">
              <div className="bracket-conf-row">
                <span>Western Conference</span>
                <span className="bracket-conf-mid">2026 Bracket</span>
                <span>Eastern Conference</span>
              </div>
              <div className="bracket-grid">
                <RoundColumn
                  byId={byId}
                  label="First Round"
                  matchups={storedWestFirstRound}
                  onOpenSeries={openSeries}
                  side="west"
                />
                <RoundColumn
                  byId={byId}
                  label="Conf. Semifinals"
                  matchups={westSemis}
                  onOpenSeries={openSeries}
                  side="west"
                />
                <RoundColumn
                  byId={byId}
                  label="Conf. Finals"
                  matchups={[westConfFinal]}
                  onOpenSeries={openSeries}
                  side="west"
                />

                <div className="bracket-round finals-col">
                  <span className="round-label finals-label">NBA Finals</span>
                  <div className="round-body">
                    <Matchup
                      byId={byId}
                      onOpenSeries={openSeries}
                      series={finals}
                      side="west"
                      variant="finals"
                    />
                  </div>
                </div>

                <RoundColumn
                  byId={byId}
                  label="Conf. Finals"
                  matchups={[eastConfFinal]}
                  onOpenSeries={openSeries}
                  side="east"
                />
                <RoundColumn
                  byId={byId}
                  label="Conf. Semifinals"
                  matchups={eastSemis}
                  onOpenSeries={openSeries}
                  side="east"
                />
                <RoundColumn
                  byId={byId}
                  label="First Round"
                  matchups={storedEastFirstRound}
                  onOpenSeries={openSeries}
                  side="east"
                />
              </div>

              <div className="playin-results">
                <PlayInPanel
                  byId={byId}
                  onOpenSeries={openSeries}
                  series={playIn.west}
                  title="West Play-In"
                />
                <PlayInPanel
                  byId={byId}
                  onOpenSeries={openSeries}
                  series={playIn.east}
                  title="East Play-In"
                />
              </div>
            </div>

            <ChampionBanner champion={champion} mvp={finalsMvp} />
          </>
        )}

        {activeSeries ? (
          <SeriesModal
            byId={byId}
            onClose={() => setActiveSeries(null)}
            onOpenGame={(game) => setActiveGame(game)}
            series={activeSeries}
          />
        ) : null}

        {activeSeries && activeGame ? (
          <GameModal
            byId={byId}
            game={activeGame}
            onBack={() => setActiveGame(null)}
            series={activeSeries}
          />
        ) : null}
      </div>
    </AppShell>
  );
}

function RoundColumn({
  byId,
  label,
  matchups,
  onOpenSeries,
  side,
}: {
  byId: Map<number, Team>;
  label: string;
  matchups: Series[];
  onOpenSeries: (series: Series) => void;
  side: Side;
}) {
  return (
    <div className="bracket-round">
      <span className="round-label">{label}</span>
      <div className="round-body">
        {matchups.map((matchup, index) => (
          <Matchup
            byId={byId}
            key={index}
            onOpenSeries={onOpenSeries}
            series={matchup}
            side={side}
          />
        ))}
      </div>
    </div>
  );
}

function Matchup({
  byId,
  onOpenSeries,
  series: matchup,
  side,
  variant,
}: {
  byId: Map<number, Team>;
  onOpenSeries: (series: Series) => void;
  series: Series;
  side: Side;
  variant?: "finals";
}) {
  return (
    <div
      aria-label="View series game results"
      className={[
        "bracket-matchup",
        `bracket-matchup-${side}`,
        variant === "finals" ? "bracket-matchup-finals" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={() => onOpenSeries(matchup)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpenSeries(matchup);
        }
      }}
      role="button"
      tabIndex={0}
    >
      <TeamSlot byId={byId} participant={matchup.top} won={matchup.winnerId === matchup.top.id} />
      <TeamSlot
        byId={byId}
        participant={matchup.bottom}
        won={matchup.winnerId === matchup.bottom.id}
      />
    </div>
  );
}

function TeamSlot({
  byId,
  participant,
  won,
}: {
  byId: Map<number, Team>;
  participant: { id: number; seed?: number; wins: number };
  won: boolean;
}) {
  const team = byId.get(participant.id);
  if (!team) {
    return (
      <div className="bracket-slot empty">
        <span className="slot-tbd">TBD</span>
      </div>
    );
  }

  return (
    <div className={["bracket-slot", won ? "won" : "lost"].join(" ")} style={themeStyle(team)}>
      <span className="slot-seed">{participant.seed ?? ""}</span>
      <span className="slot-logo" aria-hidden="true">
        <TeamLogoMark team={team} />
      </span>
      <a
        className="slot-name-link"
        href={`/rosters?team=${team.nba_team_id}`}
        onClick={(event) => event.stopPropagation()}
      >
        {team.abbreviation}
      </a>
      <span className="slot-games">{participant.wins}</span>
    </div>
  );
}

function SeriesModal({
  byId,
  onClose,
  onOpenGame,
  series: matchup,
}: {
  byId: Map<number, Team>;
  onClose: () => void;
  onOpenGame: (game: Game) => void;
  series: Series;
}) {
  const winner = byId.get(matchup.winnerId);
  const loserId = matchup.winnerId === matchup.top.id ? matchup.bottom.id : matchup.top.id;
  const winnerWins = matchup.winnerId === matchup.top.id ? matchup.top.wins : matchup.bottom.wins;
  const loserWins = matchup.winnerId === matchup.top.id ? matchup.bottom.wins : matchup.top.wins;

  return (
    <div className="pf-backdrop" onClick={onClose} role="presentation">
      <div
        aria-modal="true"
        className="pf-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <button aria-label="Close" className="pf-close" onClick={onClose} type="button">
          ×
        </button>

        <span className="pf-round-tag">{matchup.round}</span>
        <div className="pf-series-head">
          <TeamHead byId={byId} teamId={matchup.top.id} won={matchup.winnerId === matchup.top.id} />
          <div className="pf-series-mid">
            <span className="pf-series-tag">Series</span>
            <strong>
              {winnerWins}–{loserWins}
            </strong>
            <span className="pf-series-winner">{winner?.name ?? ""} win</span>
          </div>
          <TeamHead
            byId={byId}
            teamId={matchup.bottom.id}
            won={matchup.winnerId === matchup.bottom.id}
          />
        </div>

        <p className="pf-hint">Select a game for the full box score</p>
        <ul className="pf-game-list">
          {matchup.games.map((game) => {
            const winnerGameId = game.winnerId;
            const loserGameId =
              winnerGameId === matchup.top.id ? matchup.bottom.id : matchup.top.id;
            return (
              <li key={game.n}>
                <button className="pf-game-row" onClick={() => onOpenGame(game)} type="button">
                  <span className="pf-game-num">
                    Game {game.n}
                    <em>{game.date}</em>
                  </span>
                  <span className="pf-game-result">
                    <TeamMini byId={byId} teamId={winnerGameId} won />
                    <b className="pf-game-score">
                      {game.scores[winnerGameId]}–{game.scores[loserGameId]}
                    </b>
                    <TeamMini byId={byId} teamId={loserGameId} won={false} />
                  </span>
                  <span className="pf-game-cta" aria-hidden="true">
                    {game.boxes ? "Box score →" : "Recap →"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <p className="pf-note">
          {winner?.city} {winner?.name} won the series over {byId.get(loserId)?.name}.
        </p>
      </div>
    </div>
  );
}

function GameModal({
  byId,
  game,
  onBack,
  series: matchup,
}: {
  byId: Map<number, Team>;
  game: Game;
  onBack: () => void;
  series: Series;
}) {
  const topTeam = byId.get(matchup.top.id);
  const bottomTeam = byId.get(matchup.bottom.id);
  const topScore = game.scores[matchup.top.id];
  const bottomScore = game.scores[matchup.bottom.id];
  const topBox = game.boxes?.[matchup.top.id];
  const bottomBox = game.boxes?.[matchup.bottom.id];

  return (
    <div className="pf-fullscreen" role="dialog" aria-modal="true">
      <div className="pf-fs-inner">
        <div className="pf-fs-topbar">
          <button className="pf-fs-back" onClick={onBack} type="button">
            ← Back to series
          </button>
          <span className="pf-fs-meta">
            {matchup.round} · Game {game.n} · {game.date}, 2026
            {game.loc ? ` · ${game.loc}` : ""}
            {game.ot ? " · OT" : ""}
          </span>
        </div>

        <div className="pf-game-head">
          <GameTeamScore score={topScore} team={topTeam} won={game.winnerId === matchup.top.id} />
          <div className="pf-game-head-mid">
            <b>FINAL</b>
          </div>
          <GameTeamScore
            score={bottomScore}
            team={bottomTeam}
            won={game.winnerId === matchup.bottom.id}
          />
        </div>

        {topBox && bottomBox ? (
          <>
            <LineScore
              bottomBox={bottomBox}
              bottomScore={bottomScore}
              bottomTeam={bottomTeam}
              topBox={topBox}
              topScore={topScore}
              topTeam={topTeam}
            />

            {game.note ? <p className="pf-data-note">{game.note}</p> : null}

            <div className="pf-best-row">
              <BestPlayerCard box={topBox} team={topTeam} />
              <BestPlayerCard box={bottomBox} team={bottomTeam} />
            </div>

            <div className="pf-boxscores">
              <BoxScoreTable box={topBox} team={topTeam} />
              <BoxScoreTable box={bottomBox} team={bottomTeam} />
            </div>
          </>
        ) : (
          <p className="pf-no-box">
            Full box score not recorded for this game — final score shown above.
          </p>
        )}
      </div>
    </div>
  );
}

function LineScore({
  bottomBox,
  bottomScore,
  bottomTeam,
  topBox,
  topScore,
  topTeam,
}: {
  bottomBox: TeamBox;
  bottomScore: number;
  bottomTeam: Team | undefined;
  topBox: TeamBox;
  topScore: number;
  topTeam: Team | undefined;
}) {
  const periods = Math.max(topBox.q.length, bottomBox.q.length);
  const heads = Array.from({ length: periods }, (_, index) => `Q${index + 1}`);
  return (
    <div className="pf-linescore">
      <table>
        <thead>
          <tr>
            <th className="pf-ls-team">Team</th>
            {heads.map((head) => (
              <th key={head}>{head}</th>
            ))}
            <th>Final</th>
          </tr>
        </thead>
        <tbody>
          <LineScoreRow box={topBox} periods={periods} score={topScore} team={topTeam} />
          <LineScoreRow box={bottomBox} periods={periods} score={bottomScore} team={bottomTeam} />
        </tbody>
      </table>
    </div>
  );
}

function LineScoreRow({
  box,
  periods,
  score,
  team,
}: {
  box: TeamBox;
  periods: number;
  score: number;
  team: Team | undefined;
}) {
  return (
    <tr>
      <td className="pf-ls-team">{team?.abbreviation ?? "—"}</td>
      {Array.from({ length: periods }, (_, index) => (
        <td key={index}>{box.q[index] ?? "—"}</td>
      ))}
      <td className="pf-ls-final">{score}</td>
    </tr>
  );
}

function BestPlayerCard({ box, team }: { box: TeamBox; team: Team | undefined }) {
  const best = bestPlayer(box);
  if (!best || !team) {
    return null;
  }
  return (
    <div className="pf-best-card" style={team ? themeStyle(team) : undefined}>
      <span className="pf-best-label">Top Performer · {team?.abbreviation}</span>
      <div className="pf-best-body">
        <span className="pf-best-logo" aria-hidden="true">
          {team ? <TeamLogoMark team={team} /> : null}
        </span>
        <strong>{best[0]}</strong>
      </div>
      <div className="pf-best-stats">
        <span>
          <b>{best[1]}</b>PTS
        </span>
        <span>
          <b>{best[2]}</b>REB
        </span>
        <span>
          <b>{best[3]}</b>AST
        </span>
        <span>
          <b>{best[7]}</b>FG
        </span>
        <span>
          <b>{best[8]}</b>3PT
        </span>
      </div>
    </div>
  );
}

function BoxScoreTable({ box, team }: { box: TeamBox; team: Team | undefined }) {
  const sorted = useMemo(() => sortPlayers(box.players), [box.players]);
  const bestName = sorted.length > 0 ? bestPlayer(box)?.[0] : undefined;
  const [fg, tp, ft, reb, ast, stl, blk, to, pf] = box.tot;

  return (
    <div className="pf-box">
      <div className="pf-box-head">
        <span className="pf-box-logo" aria-hidden="true">
          {team ? <TeamLogoMark team={team} /> : null}
        </span>
        <strong>
          {team?.city} {team?.name}
        </strong>
      </div>
      <p className="pf-box-totals">
        FG {fg} · 3PT {tp} · FT {ft} · REB {reb} · AST {ast} · STL {stl} · BLK {blk} · TO {to}
        {pf > 0 ? ` · PF ${pf}` : ""}
      </p>
      <div className="pf-box-scroll">
        <table className="pf-box-table">
          <thead>
            <tr>
              <th className="pf-col-player">Player</th>
              <th>PTS</th>
              <th>REB</th>
              <th>AST</th>
              <th>STL</th>
              <th>BLK</th>
              <th>TO</th>
              <th>FG</th>
              <th>3PT</th>
              <th>FT</th>
              <th>+/-</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr className={row[0] === bestName ? "pf-box-best" : ""} key={row[0]}>
                <td className="pf-col-player">{row[0]}</td>
                <td className="pf-box-pts">{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3]}</td>
                <td>{row[4]}</td>
                <td>{row[5]}</td>
                <td>{row[6]}</td>
                <td>{row[7]}</td>
                <td>{row[8]}</td>
                <td>{row[9]}</td>
                <td>{row[10]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GameTeamScore({
  score,
  team,
  won,
}: {
  score: number;
  team: Team | undefined;
  won: boolean;
}) {
  if (!team) {
    return <div className="pf-game-team" />;
  }
  return (
    <div className={["pf-game-team", won ? "won" : "lost"].join(" ")} style={themeStyle(team)}>
      <span className="pf-game-logo" aria-hidden="true">
        <TeamLogoMark team={team} />
      </span>
      <span className="pf-game-abbr">{team.abbreviation}</span>
      <strong className="pf-game-points">{score}</strong>
      {won ? <span className="pf-game-win-tag">W</span> : null}
    </div>
  );
}

function TeamHead({
  byId,
  teamId,
  won,
}: {
  byId: Map<number, Team>;
  teamId: number;
  won: boolean;
}) {
  const team = byId.get(teamId);
  if (!team) {
    return <div className="pf-team-head" />;
  }
  return (
    <div className={["pf-team-head", won ? "won" : "lost"].join(" ")} style={themeStyle(team)}>
      <span className="pf-team-head-logo" aria-hidden="true">
        <TeamLogoMark team={team} />
      </span>
      <strong>{team.abbreviation}</strong>
      {won ? <span className="pf-team-head-tag">Series win</span> : null}
    </div>
  );
}

function TeamMini({
  byId,
  teamId,
  won,
}: {
  byId: Map<number, Team>;
  teamId: number;
  won: boolean;
}) {
  const team = byId.get(teamId);
  if (!team) {
    return <span className="pf-mini">TBD</span>;
  }
  return (
    <span className={["pf-mini", won ? "won" : "lost"].join(" ")} style={themeStyle(team)}>
      <span className="pf-mini-logo" aria-hidden="true">
        <TeamLogoMark team={team} />
      </span>
      {team.abbreviation}
    </span>
  );
}

function PlayInPanel({
  byId,
  onOpenSeries,
  series,
  title,
}: {
  byId: Map<number, Team>;
  onOpenSeries: (series: Series) => void;
  series: Series[];
  title: string;
}) {
  return (
    <div className="playin-panel">
      <span className="playin-label">{title}</span>
      <ul className="playin-list">
        {series.map((entry, index) => {
          const game = entry.games[0];
          const winnerId = entry.winnerId;
          const loserId = winnerId === entry.top.id ? entry.bottom.id : entry.top.id;
          return (
            <li key={index}>
              <button className="playin-row" onClick={() => onOpenSeries(entry)} type="button">
                <span className="playin-note">{entry.round}</span>
                <PlayInTeam byId={byId} teamId={winnerId} won />
                <b className="playin-score">
                  {game.scores[winnerId]}–{game.scores[loserId]}
                </b>
                <PlayInTeam byId={byId} teamId={loserId} won={false} />
                <span className="playin-cta" aria-hidden="true">
                  Box →
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function PlayInTeam({
  byId,
  teamId,
  won,
}: {
  byId: Map<number, Team>;
  teamId: number;
  won: boolean;
}) {
  const team = byId.get(teamId);
  if (!team) {
    return <span className="playin-team">TBD</span>;
  }
  return (
    <span className={["playin-team", won ? "won" : "lost"].join(" ")} style={themeStyle(team)}>
      <span className="playin-chip-logo" aria-hidden="true">
        <TeamLogoMark team={team} />
      </span>
      {team.abbreviation}
    </span>
  );
}

function ChampionBanner({ champion, mvp }: { champion: Team | undefined; mvp: string }) {
  if (!champion) {
    return null;
  }
  return (
    <div className="champion-banner" style={themeStyle(champion)}>
      <div className="champion-trophy" aria-hidden="true">
        🏆
      </div>
      <div className="champion-logo" aria-hidden="true">
        <TeamLogoMark team={champion} />
      </div>
      <div className="champion-text">
        <span className="champion-eyebrow">2026 NBA Champions</span>
        <strong>
          {champion.city} {champion.name}
        </strong>
        <em>Finals MVP · {mvp}</em>
      </div>
      <div className="champion-trophy" aria-hidden="true">
        🏆
      </div>
    </div>
  );
}

function themeStyle(team: Team): CSSProperties {
  return getTeamThemeStyle(getTeamTheme(team)) as CSSProperties;
}

function rowScore(row: PlayerRow): number {
  return row[1] + 1.2 * row[2] + 1.5 * row[3] + 3 * row[4] + 3 * row[5];
}

function bestPlayer(box: TeamBox): PlayerRow | undefined {
  let best: PlayerRow | undefined;
  let bestScore = -Infinity;
  for (const row of box.players) {
    const score = rowScore(row);
    if (score > bestScore) {
      bestScore = score;
      best = row;
    }
  }
  return best;
}

function sortPlayers(players: PlayerRow[]): PlayerRow[] {
  return [...players].sort((left, right) => rowScore(right) - rowScore(left));
}
