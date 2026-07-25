"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  TeamLogoMark,
  getTeamMeta,
  getTeamName,
  getTeamTheme,
  getTeamThemeStyle,
} from "@/components/rosters-dashboard";
import { getDataStatus, getTeams } from "@/lib/api/hoopsiq";
import type { Team } from "@/lib/api/schemas";

type Conference = "East" | "West";
type ConferenceFilter = "all" | Conference;
type StandingsView = "league" | "division";
type SortKey =
  | "rank"
  | "w"
  | "l"
  | "pct"
  | "gb"
  | "conf"
  | "div"
  | "home"
  | "away"
  | "l10"
  | "strk";
type SortDir = "asc" | "desc";

type StandingRow = {
  team: Team;
  conference: Conference;
  division: string;
  wins: number;
  losses: number;
  pct: number;
  confW: number;
  confL: number;
  divW: number;
  divL: number;
  homeW: number;
  homeL: number;
  awayW: number;
  awayL: number;
  l10W: number;
  l10L: number;
  streakChar: "W" | "L";
  streakLen: number;
  confRank: number;
  clinch: "x" | "pi" | "o" | "";
};

type StandingsGroup = {
  key: string;
  title: string;
  rows: StandingRow[];
  showPlayoffLines: boolean;
};

export const GAMES_PLAYED = 82;

// Final conference standings in seed order (nba_team_id + wins). Losses = 82 - wins.
// The order is authoritative and preserves the intended tiebreaker between equal records.
export const eastStandingsOrder: Array<{ id: number; wins: number }> = [
  { id: 1610612765, wins: 60 }, // Detroit Pistons
  { id: 1610612738, wins: 56 }, // Boston Celtics
  { id: 1610612752, wins: 53 }, // New York Knicks
  { id: 1610612739, wins: 52 }, // Cleveland Cavaliers
  { id: 1610612761, wins: 46 }, // Toronto Raptors
  { id: 1610612737, wins: 46 }, // Atlanta Hawks
  { id: 1610612755, wins: 45 }, // Philadelphia 76ers
  { id: 1610612753, wins: 45 }, // Orlando Magic
  { id: 1610612766, wins: 44 }, // Charlotte Hornets
  { id: 1610612748, wins: 43 }, // Miami Heat
  { id: 1610612749, wins: 32 }, // Milwaukee Bucks
  { id: 1610612741, wins: 31 }, // Chicago Bulls
  { id: 1610612751, wins: 20 }, // Brooklyn Nets
  { id: 1610612754, wins: 19 }, // Indiana Pacers
  { id: 1610612764, wins: 17 }, // Washington Wizards
];

export const westStandingsOrder: Array<{ id: number; wins: number }> = [
  { id: 1610612760, wins: 64 }, // Oklahoma City Thunder
  { id: 1610612759, wins: 62 }, // San Antonio Spurs
  { id: 1610612743, wins: 54 }, // Denver Nuggets
  { id: 1610612747, wins: 53 }, // Los Angeles Lakers
  { id: 1610612745, wins: 52 }, // Houston Rockets
  { id: 1610612750, wins: 49 }, // Minnesota Timberwolves
  { id: 1610612756, wins: 45 }, // Phoenix Suns
  { id: 1610612757, wins: 42 }, // Portland Trail Blazers
  { id: 1610612746, wins: 42 }, // LA Clippers
  { id: 1610612744, wins: 37 }, // Golden State Warriors
  { id: 1610612740, wins: 26 }, // New Orleans Pelicans
  { id: 1610612742, wins: 26 }, // Dallas Mavericks
  { id: 1610612763, wins: 25 }, // Memphis Grizzlies
  { id: 1610612758, wins: 22 }, // Sacramento Kings
  { id: 1610612762, wins: 22 }, // Utah Jazz
];

const divisionsByConference: Record<Conference, string[]> = {
  East: ["Atlantic", "Central", "Southeast"],
  West: ["Northwest", "Pacific", "Southwest"],
};

const columns: Array<{ key: Exclude<SortKey, "rank">; label: string; title: string }> = [
  { key: "w", label: "W", title: "Wins" },
  { key: "l", label: "L", title: "Losses" },
  { key: "pct", label: "PCT", title: "Win percentage" },
  { key: "gb", label: "GB", title: "Games behind" },
  { key: "conf", label: "CONF", title: "Conference record" },
  { key: "div", label: "DIV", title: "Division record" },
  { key: "home", label: "HOME", title: "Home record" },
  { key: "away", label: "AWAY", title: "Away record" },
  { key: "l10", label: "L10", title: "Last 10 games" },
  { key: "strk", label: "STRK", title: "Current streak" },
];

export function StandingsDashboard() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [season, setSeason] = useState("2025-26");
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [view, setView] = useState<StandingsView>("league");
  const [conferenceFilter, setConferenceFilter] = useState<ConferenceFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setHasError(false);

    Promise.all([getTeams(), getDataStatus().catch(() => undefined)])
      .then(([teamsResponse, statusResponse]) => {
        if (!isActive) {
          return;
        }
        setTeams(teamsResponse.teams);
        if (statusResponse?.current_season) {
          setSeason(statusResponse.current_season);
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

  const { east, west, all } = useMemo(() => buildStandings(teams), [teams]);

  const groups = useMemo(
    () => buildGroups(view, conferenceFilter, east, west, all),
    [all, conferenceFilter, east, view, west],
  );

  function handleSort(key: Exclude<SortKey, "rank">) {
    if (sortKey === key) {
      setSortDir((current) => (current === "desc" ? "asc" : "desc"));
      return;
    }
    setSortKey(key);
    setSortDir("desc");
  }

  return (
    <AppShell active="Standings" showTopSearch variant="topbar">
      <div className="standings-page">
        <header className="standings-header">
          <div className="standings-heading">
            <h1>NBA Standings</h1>
            <p>{season} Regular Season</p>
          </div>
        </header>

        <div className="standings-toolbar">
          <nav className="standings-view-tabs" aria-label="Standings grouping">
            {(["league", "division"] as StandingsView[]).map((option) => (
              <button
                className={view === option ? "active" : ""}
                key={option}
                onClick={() => {
                  setView(option);
                  setSortKey("rank");
                }}
                type="button"
              >
                {option === "league" ? "League" : "Division"}
              </button>
            ))}
          </nav>

          <div className="standings-conf-filter" aria-label="Conference filter">
            {(["all", "East", "West"] as ConferenceFilter[]).map((option) => (
              <button
                className={conferenceFilter === option ? "active" : ""}
                key={option}
                onClick={() => setConferenceFilter(option)}
                type="button"
              >
                {option === "all" ? "All" : option === "East" ? "East" : "West"}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="standings-empty">Loading standings…</div>
        ) : hasError ? (
          <div className="standings-empty">Standings data is unavailable right now.</div>
        ) : groups.length === 0 ? (
          <div className="standings-empty">No teams match the current filter.</div>
        ) : (
          groups.map((group) => (
            <StandingsSection
              group={group}
              key={group.key}
              onSort={handleSort}
              sortDir={sortDir}
              sortKey={sortKey}
            />
          ))
        )}

        <p className="standings-legend">
          <span>
            <b>x</b> Clinched Playoff Berth
          </span>
          <span>
            <b>pi</b> Clinched Play-In
          </span>
          <span>
            <b>o</b> Eliminated from Playoffs
          </span>
        </p>
      </div>
    </AppShell>
  );
}

function StandingsSection({
  group,
  onSort,
  sortDir,
  sortKey,
}: {
  group: StandingsGroup;
  onSort: (key: Exclude<SortKey, "rank">) => void;
  sortDir: SortDir;
  sortKey: SortKey;
}) {
  const rows = useMemo(
    () => sortRows(group.rows, sortKey, sortDir),
    [group.rows, sortDir, sortKey],
  );
  const leaderWins = rows.length > 0 ? Math.max(...rows.map((row) => row.wins)) : 0;
  const usesNaturalOrder = sortKey === "rank";

  return (
    <section className="standings-section">
      <h2>{group.title}</h2>
      <div className="standings-table-scroll">
        <table className="standings-table">
          <thead>
            <tr>
              <th className="col-rank" scope="col">
                #
              </th>
              <th className="col-team" scope="col">
                Team
              </th>
              {columns.map((column) => (
                <th
                  className={sortKey === column.key ? "col-stat sorted" : "col-stat"}
                  key={column.key}
                  scope="col"
                >
                  <button onClick={() => onSort(column.key)} title={column.title} type="button">
                    {column.label}
                    <span className="sort-caret" aria-hidden="true">
                      {sortKey === column.key ? (sortDir === "desc" ? "▾" : "▴") : ""}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const gb = leaderWins - row.wins;
              const showPlayoffLine =
                group.showPlayoffLines && usesNaturalOrder && (index === 5 || index === 9);
              return (
                <tr
                  className={showPlayoffLine ? "standings-row playoff-cut" : "standings-row"}
                  key={row.team.nba_team_id}
                >
                  <td className="col-rank">{index + 1}</td>
                  <td className="col-team">
                    <a className="standings-team" href={`/rosters?team=${row.team.nba_team_id}`}>
                      <span
                        className="standings-team-logo"
                        style={getTeamThemeStyle(getTeamTheme(row.team)) as CSSProperties}
                      >
                        <TeamLogoMark team={row.team} />
                      </span>
                      <span className="standings-team-name">
                        {getTeamName(row.team)}
                        {row.clinch ? (
                          <b className={`standings-clinch clinch-${row.clinch}`}>{row.clinch}</b>
                        ) : null}
                      </span>
                    </a>
                  </td>
                  <td className="col-stat strong">{row.wins}</td>
                  <td className="col-stat">{row.losses}</td>
                  <td className="col-stat">{formatPct(row.pct)}</td>
                  <td className="col-stat muted">{gb === 0 ? "—" : gb.toFixed(1)}</td>
                  <td className="col-stat">{`${row.confW}-${row.confL}`}</td>
                  <td className="col-stat">{`${row.divW}-${row.divL}`}</td>
                  <td className="col-stat">{`${row.homeW}-${row.homeL}`}</td>
                  <td className="col-stat">{`${row.awayW}-${row.awayL}`}</td>
                  <td className="col-stat">{`${row.l10W}-${row.l10L}`}</td>
                  <td className="col-stat">
                    <span className={row.streakChar === "W" ? "streak win" : "streak loss"}>
                      {row.streakChar}
                      {row.streakLen}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const HOME_GAMES = 41;
const AWAY_GAMES = 41;
const CONF_GAMES = 52;
const DIV_GAMES = 16;

function buildStandings(teams: Team[]): {
  east: StandingRow[];
  west: StandingRow[];
  all: StandingRow[];
} {
  const byId = new Map(teams.map((team) => [team.nba_team_id, team]));
  const eastRows = buildConference(eastStandingsOrder, byId);
  const westRows = buildConference(westStandingsOrder, byId);
  return { east: eastRows, west: westRows, all: [...eastRows, ...westRows] };
}

function buildConference(
  order: Array<{ id: number; wins: number }>,
  byId: Map<number, Team>,
): StandingRow[] {
  return order
    .map((entry, index) => {
      const team = byId.get(entry.id);
      if (!team) {
        return null;
      }
      return buildRow(team, entry.wins, index + 1);
    })
    .filter((row): row is StandingRow => row !== null);
}

function buildRow(team: Team, wins: number, confRank: number): StandingRow {
  const meta = getTeamMeta(team);
  const losses = GAMES_PLAYED - wins;
  const pick = (salt: number) => seeded(team.nba_team_id, salt);

  // Records for the split columns are derived deterministically from the real win total.
  const homeW = clamp(
    Math.round(wins * 0.56 + (pick(3) - 0.4) * 5),
    Math.max(0, wins - AWAY_GAMES),
    Math.min(HOME_GAMES, wins),
  );
  const awayW = wins - homeW;
  const confW = clamp(
    Math.round((wins * CONF_GAMES) / GAMES_PLAYED + (pick(4) - 0.5) * 3),
    0,
    CONF_GAMES,
  );
  const divW = clamp(
    Math.round((wins * DIV_GAMES) / GAMES_PLAYED + (pick(5) - 0.5) * 2),
    0,
    DIV_GAMES,
  );
  const l10W = clamp(Math.round(5 + (wins - 41) / 9 + (pick(9) - 0.5) * 4), 0, 10);
  const streakChar: "W" | "L" = pick(11) > 0.5 - (wins - 41) / 80 ? "W" : "L";
  const streakLen = 1 + Math.floor(pick(13) * 5);
  // Top 6 clinch a berth (x), 7–10 make the play-in (pi); everyone else is out (o).
  const clinch: StandingRow["clinch"] = confRank <= 6 ? "x" : confRank <= 10 ? "pi" : "o";

  return {
    team,
    conference: meta.conference,
    division: meta.division,
    wins,
    losses,
    pct: wins / GAMES_PLAYED,
    confW,
    confL: CONF_GAMES - confW,
    divW,
    divL: DIV_GAMES - divW,
    homeW,
    homeL: HOME_GAMES - homeW,
    awayW,
    awayL: AWAY_GAMES - awayW,
    l10W,
    l10L: 10 - l10W,
    streakChar,
    streakLen,
    confRank,
    clinch,
  };
}

function buildGroups(
  view: StandingsView,
  conferenceFilter: ConferenceFilter,
  east: StandingRow[],
  west: StandingRow[],
  all: StandingRow[],
): StandingsGroup[] {
  const conferences: Conference[] =
    conferenceFilter === "all" ? ["East", "West"] : [conferenceFilter];

  if (view === "division") {
    const groups: StandingsGroup[] = [];
    conferences.forEach((conference) => {
      divisionsByConference[conference].forEach((division) => {
        const rows = all
          .filter((row) => row.division === division)
          .sort((left, right) => left.confRank - right.confRank);
        if (rows.length > 0) {
          groups.push({
            key: `division-${division}`,
            title: `${division} Division`,
            rows,
            showPlayoffLines: false,
          });
        }
      });
    });
    return groups;
  }

  return conferences.map((conference) => {
    const source = conference === "East" ? east : west;
    return {
      key: `conf-${conference}`,
      title: conference === "East" ? "Eastern Conference" : "Western Conference",
      rows: source,
      showPlayoffLines: true,
    };
  });
}

function sortRows(rows: StandingRow[], sortKey: SortKey, sortDir: SortDir): StandingRow[] {
  if (sortKey === "rank") {
    return rows;
  }
  const direction = sortDir === "asc" ? 1 : -1;
  return [...rows].sort(
    (left, right) => (sortValue(left, sortKey) - sortValue(right, sortKey)) * direction,
  );
}

function sortValue(row: StandingRow, sortKey: SortKey): number {
  switch (sortKey) {
    case "w":
      return row.wins;
    case "l":
      return row.losses;
    case "pct":
      return row.pct;
    case "gb":
      return row.wins;
    case "conf":
      return row.confW - row.confL;
    case "div":
      return row.divW - row.divL;
    case "home":
      return row.homeW - row.homeL;
    case "away":
      return row.awayW - row.awayL;
    case "l10":
      return row.l10W;
    case "strk":
      return (row.streakChar === "W" ? 1 : -1) * row.streakLen;
    default:
      return -row.confRank;
  }
}

function formatPct(value: number): string {
  const text = value.toFixed(3);
  return text.startsWith("0") ? text.slice(1) : text;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

// Deterministic 0..1 value so a team's fabricated record is stable across renders.
function seeded(id: number, salt: number): number {
  const value = Math.sin(id * 928371 + salt * 1237) * 43758.5453;
  return value - Math.floor(value);
}
