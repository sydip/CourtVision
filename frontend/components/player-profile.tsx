"use client";

import {
  type CSSProperties,
  type MutableRefObject,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AppShell } from "@/components/app-shell";
import { PlayerPortrait } from "@/components/home-dashboard";
import { PlayerNumberMark } from "@/components/player-number-mark";
import {
  useDataStatus,
  usePlayer,
  usePlayerBenchmarks,
  usePlayerGames,
  usePlayerSplits,
  usePlayerSummary,
  usePlayerTrends,
  useSeasons,
  useSimilarPlayers,
} from "@/lib/api/hooks";
import type {
  GameLogItem,
  PlayerBenchmarks,
  PlayerDetail,
  PlayerSeasonSummary,
  PlayerSplits,
  PlayerTrends,
  SimilarPlayer,
} from "@/lib/api/schemas";
import {
  buildPerformanceSeries,
  buildRestSplits,
  buildSeasonAverageSeries,
  getPositionPercentiles,
  type PerformancePoint,
  type RestSplit,
  type RollingWindow,
} from "@/lib/player-analytics";
import {
  formatDate,
  formatInteger,
  formatNumber,
  formatPercent,
  formatPercentile,
  formatShortDate,
  pluralize,
} from "@/lib/format";

type PlayerProfileViewProps = {
  benchmarks: PlayerBenchmarks | undefined;
  games: GameLogItem[];
  isLoading: boolean;
  hasProfileError: boolean;
  player: PlayerDetail | undefined;
  selectedSeason: string;
  similarPlayers: SimilarPlayer[];
  splits: PlayerSplits | undefined;
  summary: PlayerSeasonSummary | undefined;
  trends: PlayerTrends | undefined;
};

type ExpandedGraph = "offense" | "defense";

export type TeamLike =
  | {
      nba_team_id: number;
      city: string;
      name: string;
    }
  | null
  | undefined;

type TeamTheme = {
  primary: string;
  accent: string;
  muted: string;
  glow: string;
  text: string;
  graphThird: string;
};

type BaseTeamTheme = Omit<TeamTheme, "graphThird">;

const summaryCards = [
  ["points_per_game", "Points", "PPG"],
  ["rebounds_per_game", "Rebounds", "RPG"],
  ["assists_per_game", "Assists", "APG"],
  ["minutes_per_game", "Minutes", "MPG"],
  ["true_shooting_percentage", "True Shooting", "TS%"],
  ["turnovers_per_game", "Turnovers", "TOPG"],
] as const;

const defaultTheme: BaseTeamTheme = {
  primary: "#4f83ff",
  accent: "#8fb2ff",
  muted: "rgba(79, 131, 255, 0.18)",
  glow: "rgba(79, 131, 255, 0.24)",
  text: "#8fb2ff",
};

const teamThemes: Record<number, BaseTeamTheme> = {
  1610612737: {
    primary: "#e03a3e",
    accent: "#fdb927",
    muted: "rgba(224, 58, 62, 0.18)",
    glow: "rgba(253, 185, 39, 0.18)",
    text: "#ff6b70",
  },
  1610612738: {
    primary: "#007a33",
    accent: "#ba9653",
    muted: "rgba(0, 122, 51, 0.2)",
    glow: "rgba(0, 122, 51, 0.24)",
    text: "#58e58b",
  },
  1610612739: {
    primary: "#6f263d",
    accent: "#ffb81c",
    muted: "rgba(111, 38, 61, 0.18)",
    glow: "rgba(255, 184, 28, 0.18)",
    text: "#ffcf5a",
  },
  1610612740: {
    primary: "#0c2340",
    accent: "#c8102e",
    muted: "rgba(12, 35, 64, 0.24)",
    glow: "rgba(200, 16, 46, 0.18)",
    text: "#6cb7ff",
  },
  1610612741: {
    primary: "#ce1141",
    accent: "#ffffff",
    muted: "rgba(206, 17, 65, 0.2)",
    glow: "rgba(206, 17, 65, 0.24)",
    text: "#ff6f94",
  },
  1610612742: {
    primary: "#00538c",
    accent: "#b8c4ca",
    muted: "rgba(0, 83, 140, 0.22)",
    glow: "rgba(0, 83, 140, 0.26)",
    text: "#5db8ff",
  },
  1610612743: {
    primary: "#0e2240",
    accent: "#fec524",
    muted: "rgba(14, 34, 64, 0.24)",
    glow: "rgba(254, 197, 36, 0.18)",
    text: "#ffd84e",
  },
  1610612744: {
    primary: "#1d428a",
    accent: "#ffc72c",
    muted: "rgba(29, 66, 138, 0.24)",
    glow: "rgba(255, 199, 44, 0.22)",
    text: "#ffc72c",
  },
  1610612745: {
    primary: "#ce1141",
    accent: "#c4ced4",
    muted: "rgba(206, 17, 65, 0.18)",
    glow: "rgba(206, 17, 65, 0.22)",
    text: "#ff6b85",
  },
  1610612746: {
    primary: "#c8102e",
    accent: "#1d428a",
    muted: "rgba(200, 16, 46, 0.18)",
    glow: "rgba(29, 66, 138, 0.18)",
    text: "#ff6b70",
  },
  1610612747: {
    primary: "#552583",
    accent: "#fdb927",
    muted: "rgba(85, 37, 131, 0.22)",
    glow: "rgba(253, 185, 39, 0.2)",
    text: "#fdb927",
  },
  1610612748: {
    primary: "#98002e",
    accent: "#f9a01b",
    muted: "rgba(152, 0, 46, 0.2)",
    glow: "rgba(249, 160, 27, 0.18)",
    text: "#ff8baa",
  },
  1610612749: {
    primary: "#00471b",
    accent: "#eee1c6",
    muted: "rgba(0, 71, 27, 0.22)",
    glow: "rgba(0, 113, 45, 0.22)",
    text: "#62e68f",
  },
  1610612750: {
    primary: "#0c2340",
    accent: "#236192",
    muted: "rgba(12, 35, 64, 0.24)",
    glow: "rgba(35, 97, 146, 0.24)",
    text: "#9bc5e8",
  },
  1610612751: {
    primary: "#111827",
    accent: "#ffffff",
    muted: "rgba(255, 255, 255, 0.11)",
    glow: "rgba(255, 255, 255, 0.12)",
    text: "#dce6f5",
  },
  1610612752: {
    primary: "#006bb6",
    accent: "#f58426",
    muted: "rgba(0, 107, 182, 0.22)",
    glow: "rgba(245, 132, 38, 0.18)",
    text: "#f58426",
  },
  1610612753: {
    primary: "#0077c0",
    accent: "#c4ced4",
    muted: "rgba(0, 119, 192, 0.22)",
    glow: "rgba(0, 119, 192, 0.24)",
    text: "#6bc9ff",
  },
  1610612754: {
    primary: "#002d62",
    accent: "#fdbb30",
    muted: "rgba(0, 45, 98, 0.24)",
    glow: "rgba(253, 187, 48, 0.2)",
    text: "#fdbb30",
  },
  1610612755: {
    primary: "#006bb6",
    accent: "#ed174c",
    muted: "rgba(0, 107, 182, 0.22)",
    glow: "rgba(237, 23, 76, 0.16)",
    text: "#72c4ff",
  },
  1610612756: {
    primary: "#1d1160",
    accent: "#e56020",
    muted: "rgba(29, 17, 96, 0.24)",
    glow: "rgba(229, 96, 32, 0.22)",
    text: "#ff8a3d",
  },
  1610612757: {
    primary: "#e03a3e",
    accent: "#111827",
    muted: "rgba(224, 58, 62, 0.2)",
    glow: "rgba(224, 58, 62, 0.2)",
    text: "#ff6b70",
  },
  1610612758: {
    primary: "#5a2d81",
    accent: "#63727a",
    muted: "rgba(90, 45, 129, 0.22)",
    glow: "rgba(90, 45, 129, 0.24)",
    text: "#c28dff",
  },
  1610612759: {
    primary: "#111827",
    accent: "#c4ced4",
    muted: "rgba(196, 206, 212, 0.14)",
    glow: "rgba(196, 206, 212, 0.14)",
    text: "#c4ced4",
  },
  1610612760: {
    primary: "#007ac1",
    accent: "#ef3b24",
    muted: "rgba(0, 122, 193, 0.23)",
    glow: "rgba(239, 59, 36, 0.18)",
    text: "#2ea7ff",
  },
  1610612761: {
    primary: "#ce1141",
    accent: "#111827",
    muted: "rgba(206, 17, 65, 0.2)",
    glow: "rgba(206, 17, 65, 0.22)",
    text: "#ff7095",
  },
  1610612762: {
    primary: "#753bbd",
    accent: "#9bd8ff",
    muted: "rgba(117, 59, 189, 0.24)",
    glow: "rgba(155, 216, 255, 0.22)",
    text: "#ffffff",
  },
  1610612763: {
    primary: "#5d76a9",
    accent: "#f5b112",
    muted: "rgba(93, 118, 169, 0.22)",
    glow: "rgba(245, 177, 18, 0.18)",
    text: "#9fbaff",
  },
  1610612764: {
    primary: "#002b5c",
    accent: "#e31837",
    muted: "rgba(0, 43, 92, 0.24)",
    glow: "rgba(227, 24, 55, 0.16)",
    text: "#ff6f86",
  },
  1610612765: {
    primary: "#c8102e",
    accent: "#1d42ba",
    muted: "rgba(200, 16, 46, 0.2)",
    glow: "rgba(29, 66, 186, 0.18)",
    text: "#ff6a7a",
  },
  1610612766: {
    primary: "#00788c",
    accent: "#1d1160",
    muted: "rgba(0, 120, 140, 0.24)",
    glow: "rgba(29, 17, 96, 0.22)",
    text: "#45d5e8",
  },
};

const graphThirdColors: Record<number, string> = {
  1610612737: "#ffffff",
  1610612738: "#ffffff",
  1610612739: "#041e42",
  1610612740: "#b4975a",
  1610612741: "#ffffff",
  1610612742: "#ffffff",
  1610612743: "#8b2131",
  1610612744: "#ffffff",
  1610612745: "#ffffff",
  1610612746: "#ffffff",
  1610612747: "#ffffff",
  1610612748: "#ffffff",
  1610612749: "#0077c0",
  1610612750: "#ffffff",
  1610612751: "#ffffff",
  1610612752: "#ffffff",
  1610612753: "#ffffff",
  1610612754: "#ffffff",
  1610612755: "#ffffff",
  1610612756: "#ffffff",
  1610612757: "#ffffff",
  1610612758: "#ffffff",
  1610612759: "#ffffff",
  1610612760: "#ffffff",
  1610612761: "#753bbd",
  1610612762: "#ffffff",
  1610612763: "#ffffff",
  1610612764: "#ffffff",
  1610612765: "#ffffff",
  1610612766: "#ffffff",
};

// Teams whose panel backgrounds read too bright/washed-out at the standard
// mix strength and need a darker fill. Every other team is dark enough already.
const teamsNeedingDarkerPanels = new Set([
  1610612737, // Hawks
  1610612738, // Celtics
  1610612741, // Bulls
  1610612742, // Mavericks
  1610612745, // Rockets
  1610612746, // Clippers
  1610612748, // Heat
  1610612752, // Knicks
  1610612753, // Magic
  1610612755, // 76ers
  1610612757, // Trail Blazers
  1610612758, // Kings
  1610612760, // Thunder
  1610612761, // Raptors
  1610612762, // Jazz
  1610612763, // Grizzlies
  1610612765, // Pistons
]);

export function getTeamTheme(team: TeamLike): TeamTheme {
  const baseTheme = team ? (teamThemes[team.nba_team_id] ?? defaultTheme) : defaultTheme;

  return {
    ...baseTheme,
    graphThird: team ? (graphThirdColors[team.nba_team_id] ?? "#ffffff") : "#ffffff",
  };
}

function hexToRgb(hex: string): [number, number, number] | null {
  const normalized = hex.trim();
  if (!normalized.startsWith("#") || normalized.length !== 7) {
    return null;
  }
  const value = Number.parseInt(normalized.slice(1), 16);
  if (Number.isNaN(value)) {
    return null;
  }
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

// "Bright" variant: a vivid, mid-lightness take on the hue.
export function getGraphStroke(color: string): string {
  const hsl = hexToHsl(color);
  if (!hsl) {
    return color;
  }
  const [hue, saturation] = hsl;
  if (saturation < 0.12) {
    return "#cbd6ea";
  }
  return hslToCss(hue, clamp(Math.max(saturation, 0.9), 0, 0.96), 0.62);
}

// "Light" variant: a pale, high-lightness take on the same hue, kept far enough
// from the bright variant (large lightness + saturation gap) to read as distinct.
function getAlternateGraphStroke(color: string): string {
  const hsl = hexToHsl(color);
  if (!hsl) {
    return color;
  }
  const [hue, saturation] = hsl;
  if (saturation < 0.12) {
    return "#8b9bb8";
  }
  return hslToCss(hue, clamp(Math.max(saturation, 0.62), 0.6, 0.85), 0.76);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function hexToHsl(hex: string): [number, number, number] | null {
  const rgb = hexToRgb(hex);
  if (!rgb) {
    return null;
  }
  const r = rgb[0] / 255;
  const g = rgb[1] / 255;
  const b = rgb[2] / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const lightness = (max + min) / 2;
  const delta = max - min;
  if (delta === 0) {
    return [0, 0, lightness];
  }
  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  let hue: number;
  if (max === r) {
    hue = ((g - b) / delta) % 6;
  } else if (max === g) {
    hue = (b - r) / delta + 2;
  } else {
    hue = (r - g) / delta + 4;
  }
  hue = Math.round(hue * 60);
  if (hue < 0) {
    hue += 360;
  }
  return [hue, saturation, lightness];
}

function hslToCss(hue: number, saturation: number, lightness: number): string {
  return `hsl(${hue}, ${Math.round(saturation * 100)}%, ${Math.round(lightness * 100)}%)`;
}

export function getThemeStyle(team: TeamLike): CSSProperties {
  const theme = getTeamTheme(team);
  const needsDarkerPanels = team ? teamsNeedingDarkerPanels.has(team.nba_team_id) : false;

  return {
    "--team-primary": theme.primary,
    "--team-accent": theme.accent,
    "--team-muted": theme.muted,
    "--team-glow": theme.glow,
    "--team-text": theme.text,
    "--team-graph-third": theme.graphThird,
    "--team-panel-mix": needsDarkerPanels ? "0.6" : "1",
  } as CSSProperties;
}

export function PlayerProfile({ playerId }: { playerId: number }) {
  const dataStatusQuery = useDataStatus();
  const seasonsQuery = useSeasons();
  const playerQuery = usePlayer(playerId);
  const seasons = seasonsQuery.data?.seasons ?? [dataStatusQuery.data?.current_season ?? "2025-26"];
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const season = selectedSeason ?? dataStatusQuery.data?.current_season ?? seasons[0] ?? "2025-26";

  useEffect(() => {
    if (selectedSeason === null && season) {
      setSelectedSeason(season);
    }
  }, [season, selectedSeason]);

  const summaryQuery = usePlayerSummary(playerId, season);
  const gamesQuery = usePlayerGames(playerId, season, { limit: 100, sort: "asc" });
  const trendsQuery = usePlayerTrends(playerId, season);
  const splitsQuery = usePlayerSplits(playerId, season);
  const benchmarksQuery = usePlayerBenchmarks(playerId, season);
  const similarPlayersQuery = useSimilarPlayers(playerId, season, 5);

  return (
    <PlayerProfileView
      benchmarks={benchmarksQuery.data}
      games={gamesQuery.data?.items ?? []}
      hasProfileError={playerQuery.isError}
      isLoading={playerQuery.isLoading}
      player={playerQuery.data}
      selectedSeason={season}
      similarPlayers={similarPlayersQuery.data?.players ?? []}
      splits={splitsQuery.data}
      summary={summaryQuery.data}
      trends={trendsQuery.data}
    />
  );
}

export function PlayerProfileView({
  benchmarks,
  games,
  isLoading,
  hasProfileError,
  player,
  selectedSeason,
  similarPlayers,
  splits,
  summary,
  trends,
}: PlayerProfileViewProps) {
  const [offensiveWindow, setOffensiveWindow] = useState<RollingWindow>("rolling10");
  const [defensiveWindow, setDefensiveWindow] = useState<RollingWindow>("rolling10");
  const [expandedGraph, setExpandedGraph] = useState<ExpandedGraph | null>(null);
  const [isGameLogExpanded, setIsGameLogExpanded] = useState(false);
  const offensiveSeries = useMemo(
    () => buildPerformanceSeries(selectChartGames(games, offensiveWindow)),
    [games, offensiveWindow],
  );
  const defensiveSeries = useMemo(
    () => buildPerformanceSeries(selectChartGames(games, defensiveWindow)),
    [games, defensiveWindow],
  );
  const fullSeasonAverageSeries = useMemo(() => buildSeasonAverageSeries(games), [games]);
  const restSplits = useMemo(() => buildRestSplits(games), [games]);
  const percentileRows = useMemo(() => getPositionPercentiles(benchmarks), [benchmarks]);
  const teamStyle = useMemo(() => getThemeStyle(player?.team), [player?.team]);
  const sortedGames = useMemo(
    () => [...games].sort((left, right) => right.game_date.localeCompare(left.game_date)),
    [games],
  );
  const displayedGames = useMemo(() => sortedGames.slice(0, 10), [sortedGames]);
  const gameLogCaption = `${Math.min(10, sortedGames.length)} of ${pluralize(
    sortedGames.length,
    "season game",
    "season games",
  )}`;

  if (hasProfileError) {
    return (
      <AppShell active="Players" variant="topbar">
        <div className="page-grid">
          <section className="panel full-panel">
            <div className="empty-state tall">
              <strong>Player unavailable</strong>
              <span>The backend returned no stored player for this profile.</span>
              <a className="primary-link" href="/">
                Return home
              </a>
            </div>
          </section>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell active="Players" themeStyle={teamStyle} variant="topbar">
      <div className="page-grid profile-grid" style={teamStyle}>
        <section className="panel profile-header">
          {isLoading || !player ? (
            <ProfileHeaderSkeleton />
          ) : (
            <>
              <div className="profile-number-watermark" aria-hidden="true">
                <PlayerNumberMark player={player} />
              </div>
              <div className="profile-title">
                <div className="eyebrow-row">
                  <span>{player.team?.abbreviation ?? "FA"}</span>
                  <span>{player.position ?? "Position TBD"}</span>
                  <span>{selectedSeason}</span>
                </div>
                <h1>{player.full_name}</h1>
                <p>
                  {player.team ? (
                    <a
                      className="profile-team-name-link"
                      href={`/rosters?team=${player.team.nba_team_id}`}
                    >
                      {player.team.city} {player.team.name}
                    </a>
                  ) : (
                    "No team"
                  )}{" "}
                  / {player.height ?? "Height TBD"} / {player.weight_pounds ?? "--"} lbs
                </p>
                <p className="profile-copy">
                  {player.team
                    ? `${player.full_name} is shown with stored ${selectedSeason} game logs, calculated efficiency, rolling form, split context, and benchmark percentiles.`
                    : "Stored player profile data is available without an assigned team."}
                </p>
                <div className="trend-row" aria-label="Trend badges">
                  <TrendBadge label="Production" value={trends?.production_trend} />
                  <TrendBadge label="Efficiency" value={trends?.efficiency_trend} />
                </div>
              </div>
              <ProfileMetadata player={player} summary={summary} />
            </>
          )}
        </section>

        <section className="panel profile-summary-panel">
          <div className="panel-heading split">
            <div>
              <h2>{selectedSeason} Season Averages</h2>
              <p>Calculated from stored game logs</p>
            </div>
          </div>
          <div className="profile-summary-grid">
            {summaryCards.map(([key, label, suffix]) => (
              <SummaryCard
                key={key}
                label={label}
                metricKey={key}
                percentile={percentileRows.find((row) => row.key === key)?.value}
                suffix={suffix}
                summary={summary}
              />
            ))}
          </div>
        </section>

        <aside className="profile-side-stack">
          <section className="panel side-card">
            <div className="panel-heading">
              <div>
                <h2>Home vs Away Splits</h2>
                <p>Per-game comparison</p>
              </div>
            </div>
            <HomeAwaySplits splits={splits} />
          </section>

          <section className="panel side-card rest-day-panel">
            <div className="panel-heading">
              <div>
                <h2>Rest-Day Splits</h2>
                <p>Previous game spacing</p>
              </div>
            </div>
            <RestSplitsTable splits={restSplits} />
          </section>
        </aside>

        <section className="panel chart-panel">
          <div className="panel-heading split">
            <div>
              <h2>Offensive Game Log Graph</h2>
              <p>Each point matches the selected game-log row</p>
            </div>
            <GraphRangeControls
              ariaLabel="Offensive graph range"
              onFullSeason={() => setExpandedGraph("offense")}
              onRangeChange={setOffensiveWindow}
              value={offensiveWindow}
            />
          </div>
          {offensiveSeries.length > 0 ? (
            <OffensiveChart data={offensiveSeries} theme={getTeamTheme(player?.team)} />
          ) : (
            <EmptyState title="No game logs" text="Run ingestion to populate chart values." />
          )}
        </section>

        <section className="panel defense-chart-panel">
          <div className="panel-heading split">
            <div>
              <h2>Defensive Game Log Graph</h2>
              <p>Rebounds, steals, and blocks by game</p>
            </div>
            <GraphRangeControls
              ariaLabel="Defensive graph range"
              onFullSeason={() => setExpandedGraph("defense")}
              onRangeChange={setDefensiveWindow}
              value={defensiveWindow}
            />
          </div>
          {defensiveSeries.length > 0 ? (
            <DefensiveChart data={defensiveSeries} theme={getTeamTheme(player?.team)} />
          ) : (
            <EmptyState title="No defensive logs" text="Run ingestion to populate chart values." />
          )}
        </section>

        <section className="panel percentile-panel">
          <div className="panel-heading split">
            <div>
              <h2>{selectedSeason} Percentile Rankings</h2>
              <p>{player?.position ?? "Position"} benchmark</p>
            </div>
          </div>
          <PercentileBars rows={percentileRows} />
        </section>

        <section className="panel game-log-panel">
          <div className="panel-heading split">
            <div>
              <h2>Game Log</h2>
              <p>{gameLogCaption}</p>
            </div>
            <div className="segmented" role="group" aria-label="Game log range">
              <button className="active" type="button">
                Recent 10
              </button>
              <button
                aria-label="View full season game log"
                onClick={() => setIsGameLogExpanded(true)}
                title="View full game log"
                type="button"
              >
                Full Season
              </button>
            </div>
          </div>
          {displayedGames.length > 0 ? (
            <GameLogTable games={displayedGames} isFullSeason={false} />
          ) : (
            <EmptyState
              title="No recent games"
              text="This player has no stored logs for the season."
            />
          )}
        </section>

        <section className="panel report-panel similar-panel">
          <div className="panel-heading split">
            <div>
              <h2>Similar Players</h2>
              <p>Nearest statistical matches</p>
            </div>
          </div>
          <SimilarPlayersPanel mainSummary={summary} players={similarPlayers} />
        </section>
      </div>
      {expandedGraph ? (
        <GraphModal
          onClose={() => setExpandedGraph(null)}
          subtitle={`Full ${selectedSeason} season-to-date averages`}
          title={
            expandedGraph === "offense"
              ? "Full Season Offensive Game Log Graph"
              : "Full Season Defensive Game Log Graph"
          }
        >
          {expandedGraph === "offense" ? (
            <OffensiveChart
              data={fullSeasonAverageSeries}
              isExpanded
              theme={getTeamTheme(player?.team)}
            />
          ) : (
            <DefensiveChart
              data={fullSeasonAverageSeries}
              isExpanded
              theme={getTeamTheme(player?.team)}
            />
          )}
        </GraphModal>
      ) : null}
      {isGameLogExpanded ? (
        <GraphModal
          onClose={() => setIsGameLogExpanded(false)}
          subtitle={`Full ${selectedSeason} season game log`}
          title="Full Season Game Log"
        >
          <GameLogTable games={sortedGames} isFullSeason />
        </GraphModal>
      ) : null}
    </AppShell>
  );
}

function GraphRangeControls({
  ariaLabel,
  onFullSeason,
  onRangeChange,
  value,
}: {
  ariaLabel: string;
  onFullSeason: () => void;
  onRangeChange: (window: RollingWindow) => void;
  value: RollingWindow;
}) {
  return (
    <div className="segmented" role="group" aria-label={ariaLabel}>
      <button
        className={value === "rolling5" ? "active" : ""}
        onClick={() => onRangeChange("rolling5")}
        type="button"
      >
        Last 5
      </button>
      <button
        className={value === "rolling10" ? "active" : ""}
        onClick={() => onRangeChange("rolling10")}
        type="button"
      >
        Last 10
      </button>
      <button onClick={onFullSeason} type="button">
        Full Season
      </button>
    </div>
  );
}

function selectChartGames(games: GameLogItem[], window: RollingWindow): GameLogItem[] {
  const limit = window === "rolling5" ? 5 : 10;
  return [...games]
    .sort((left, right) => {
      const dateComparison = right.game_date.localeCompare(left.game_date);
      return dateComparison !== 0 ? dateComparison : right.id - left.id;
    })
    .slice(0, limit);
}

function GraphModal({
  children,
  onClose,
  subtitle,
  title,
}: {
  children: ReactNode;
  onClose: () => void;
  subtitle: string;
  title: string;
}) {
  return (
    <div
      aria-label={title}
      aria-modal="true"
      className="graph-modal-backdrop"
      onClick={onClose}
      role="dialog"
    >
      <section className="graph-modal" onClick={(event) => event.stopPropagation()}>
        <div className="graph-modal-heading">
          <div>
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
          <button aria-label="Close full season graph" onClick={onClose} type="button">
            Close
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function SummaryCard({
  label,
  metricKey,
  percentile,
  suffix,
  summary,
}: {
  label: string;
  metricKey: (typeof summaryCards)[number][0];
  percentile?: number | null;
  suffix: string;
  summary: PlayerSeasonSummary | undefined;
}) {
  const value = summary?.[metricKey];
  const formattedValue =
    metricKey === "true_shooting_percentage" ? formatPercent(value) : formatNumber(value);

  return (
    <article className="stat-card">
      <div>
        <p>{label}</p>
        <strong>{formattedValue}</strong>
        <small>
          {percentile !== undefined && percentile !== null
            ? `${formatPercentile(percentile)} percentile`
            : suffix}
        </small>
      </div>
    </article>
  );
}

function ProfileMetadata({
  player,
  summary,
}: {
  player: PlayerDetail;
  summary: PlayerSeasonSummary | undefined;
}) {
  const rows = [
    ["Born", formatDate(player.birthdate)],
    ["Position", player.position ?? "--"],
    ["Team", player.team ? `${player.team.city} ${player.team.name}` : "--"],
    ["Status", player.active ? "Active" : "Inactive"],
    ["Games", formatInteger(summary?.games_played)],
    ["Plus / Minus", formatSignedNumber(summary?.plus_minus_per_game)],
  ] as const;

  return (
    <dl className="profile-metadata">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function OffensiveChart({
  data,
  isExpanded = false,
  theme,
}: {
  data: PerformancePoint[];
  isExpanded?: boolean;
  theme: TeamTheme;
}) {
  return (
    <figure
      className={isExpanded ? "rolling-chart expanded" : "rolling-chart"}
      aria-label="Offensive game log chart with points assists TS% FG% and 3P%"
    >
      <ResponsiveContainer height={isExpanded ? 560 : 318} width="100%">
        <LineChart data={data} margin={{ bottom: 10, left: 0, right: 16, top: 20 }}>
          <CartesianGrid stroke="rgba(129, 156, 196, 0.16)" strokeDasharray="4 6" />
          <XAxis dataKey="label" stroke="#9aa8bc" tickLine={false} />
          <YAxis stroke="#9aa8bc" tickLine={false} width={36} />
          <Tooltip
            contentStyle={{
              background: "#081525",
              border: "1px solid rgba(129, 156, 196, 0.34)",
              borderRadius: "8px",
              color: "#f5f8ff",
            }}
            formatter={(value, name) => [
              typeof value === "number" ? formatNumber(value, 2) : "--",
              String(name),
            ]}
            labelFormatter={(label) => `Game date: ${label}`}
          />
          <Legend />
          <Line
            connectNulls
            dataKey="points"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="Points"
            stroke={getGraphStroke(theme.primary)}
            strokeWidth={3}
            type="monotone"
          />
          <Line
            connectNulls
            dataKey="assists"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="Assists"
            stroke={getAlternateGraphStroke(theme.primary)}
            strokeWidth={3}
            type="monotone"
          />
          <Line
            connectNulls
            dataKey="trueShootingPercentage"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="TS%"
            stroke={getGraphStroke(theme.accent)}
            strokeWidth={3}
            type="monotone"
          />
          <Line
            connectNulls
            dataKey="fieldGoalPercentage"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="FG%"
            stroke={getGraphStroke(theme.graphThird)}
            strokeWidth={3}
            type="monotone"
          />
          <Line
            connectNulls
            dataKey="threePointPercentage"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="3P%"
            stroke={getAlternateGraphStroke(theme.accent)}
            strokeWidth={3}
            type="monotone"
          />
        </LineChart>
      </ResponsiveContainer>
      <figcaption className="sr-only">
        Chart includes text labels and tooltips for actual game points, assists, calculated true
        shooting, field-goal percentage, and three-point percentage.
      </figcaption>
    </figure>
  );
}

function DefensiveChart({
  data,
  isExpanded = false,
  theme,
}: {
  data: PerformancePoint[];
  isExpanded?: boolean;
  theme: TeamTheme;
}) {
  return (
    <figure
      className={isExpanded ? "rolling-chart expanded" : "rolling-chart"}
      aria-label="Defensive game log chart with rebounds steals and blocks"
    >
      <ResponsiveContainer height={isExpanded ? 560 : 318} width="100%">
        <LineChart data={data} margin={{ bottom: 10, left: 0, right: 16, top: 20 }}>
          <CartesianGrid stroke="rgba(129, 156, 196, 0.16)" strokeDasharray="4 6" />
          <XAxis dataKey="label" stroke="#9aa8bc" tickLine={false} />
          <YAxis stroke="#9aa8bc" tickLine={false} width={36} />
          <Tooltip
            contentStyle={{
              background: "#081525",
              border: "1px solid rgba(129, 156, 196, 0.34)",
              borderRadius: "8px",
              color: "#f5f8ff",
            }}
            formatter={(value, name) => [
              typeof value === "number" ? formatNumber(value, 2) : "--",
              String(name),
            ]}
            labelFormatter={(label) => `Game date: ${label}`}
          />
          <Legend />
          <Line
            connectNulls
            dataKey="rebounds"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="Rebounds"
            stroke={getGraphStroke(theme.primary)}
            strokeWidth={3}
            type="monotone"
          />
          <Line
            connectNulls
            dataKey="steals"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="Steals"
            stroke={getGraphStroke(theme.accent)}
            strokeWidth={3}
            type="monotone"
          />
          <Line
            connectNulls
            dataKey="blocks"
            dot={{ r: 2 }}
            isAnimationActive={false}
            name="Blocks"
            stroke={getGraphStroke(theme.graphThird)}
            strokeWidth={3}
            type="monotone"
          />
        </LineChart>
      </ResponsiveContainer>
      <figcaption className="sr-only">
        Chart includes text labels and tooltips for rebounds, steals, and blocks in each selected
        game.
      </figcaption>
    </figure>
  );
}

function GameLogTable({ games, isFullSeason }: { games: GameLogItem[]; isFullSeason: boolean }) {
  return (
    <div className="table-scroll">
      <table aria-label={isFullSeason ? "Full season player game log" : "Recent player game log"}>
        <thead>
          <tr>
            <th>Date</th>
            <th>Matchup</th>
            <th>Result</th>
            <th>Min</th>
            <th>Pts</th>
            <th>Reb</th>
            <th>Ast</th>
            <th>Stl</th>
            <th>Blk</th>
            <th>FG%</th>
            <th>3P%</th>
            <th>FT</th>
            <th>TS%</th>
            <th>Tov</th>
          </tr>
        </thead>
        <tbody>
          {games.map((game) => (
            <tr key={game.id}>
              <td>{formatShortDate(game.game_date)}</td>
              <td>
                <GameLogMatchup game={game} />
              </td>
              <td>
                <span className={game.result === "W" ? "result-pill win" : "result-pill loss"}>
                  {game.result ?? "--"}
                </span>
              </td>
              <td>{formatNumber(game.minutes)}</td>
              <td>{game.points}</td>
              <td>{game.rebounds}</td>
              <td>{game.assists}</td>
              <td>{game.steals}</td>
              <td>{game.blocks}</td>
              <td>{formatPercent(calculateFieldGoalPercentage(game))}</td>
              <td>{formatPercent(calculateThreePointPercentage(game))}</td>
              <td>{formatMadeAttempted(game.free_throws_made, game.free_throws_attempted)}</td>
              <td>{formatPercent(game.calculated_true_shooting_percentage)}</td>
              <td>{game.turnovers}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function calculateFieldGoalPercentage(game: GameLogItem): number | null {
  if (game.field_goals_attempted === 0) {
    return null;
  }
  return game.field_goals_made / game.field_goals_attempted;
}

function calculateThreePointPercentage(game: GameLogItem): number | null {
  if (game.three_pointers_attempted === 0) {
    return null;
  }
  return game.three_pointers_made / game.three_pointers_attempted;
}

function formatMadeAttempted(made: number, attempted: number): string {
  return `${made}-${attempted}`;
}

function GameLogMatchup({ game }: { game: GameLogItem }) {
  const prefix = game.location === "away" ? "@" : "v.s.";
  const abbreviation = game.opponent?.abbreviation ?? "--";

  return (
    <span className="game-log-matchup">
      <span>
        {prefix} {abbreviation}
      </span>
    </span>
  );
}

function HomeAwaySplits({ splits }: { splits: PlayerSplits | undefined }) {
  const homeGames = splits?.home?.games ?? 0;
  const awayGames = splits?.away?.games ?? 0;
  const homePoints = perGame(splits?.home?.points, homeGames);
  const awayPoints = perGame(splits?.away?.points, awayGames);
  const homeAssists = perGame(splits?.home?.assists, homeGames);
  const awayAssists = perGame(splits?.away?.assists, awayGames);
  const homeMinutes = perGame(splits?.home?.minutes, homeGames);
  const awayMinutes = perGame(splits?.away?.minutes, awayGames);
  const rows = [
    ["Points / Game", homePoints, awayPoints, "number"],
    ["Assists / Game", homeAssists, awayAssists, "number"],
    ["Minutes / Game", homeMinutes, awayMinutes, "number"],
    [
      "TS%",
      splits?.home?.true_shooting_percentage,
      splits?.away?.true_shooting_percentage,
      "percent",
    ],
  ] as const;

  return (
    <div className="comparison-table">
      <div className="comparison-head">
        <span>Stat</span>
        <span>Home</span>
        <span>Away</span>
        <span>Diff</span>
      </div>
      <div className="comparison-head muted">
        <span>Games</span>
        <span>{homeGames || "--"}</span>
        <span>{awayGames || "--"}</span>
        <span>{formatSignedNumber(homeGames && awayGames ? homeGames - awayGames : null, 0)}</span>
      </div>
      {rows.map(([label, home, away, format]) => (
        <div className="comparison-row" key={label}>
          <span>{label}</span>
          <span>{format === "percent" ? formatPercent(home) : formatNumber(home)}</span>
          <span>{format === "percent" ? formatPercent(away) : formatNumber(away)}</span>
          <span className="positive">
            {format === "percent"
              ? formatSignedPercent(diff(home, away))
              : formatSignedNumber(diff(home, away))}
          </span>
        </div>
      ))}
    </div>
  );
}

function RestSplitsTable({ splits }: { splits: RestSplit[] }) {
  const splitByKey = new Map(splits.map((split) => [split.key, split]));
  const columns = [
    ["first_game", "First"],
    ["back_to_back", "B2B"],
    ["one_day_rest", "1 Day"],
    ["two_or_more_days_rest", "2+"],
  ] as const;
  const rows = [
    ["Games", (split: RestSplit | undefined) => (split?.games ? formatInteger(split.games) : "--")],
    ["Points / Game", (split: RestSplit | undefined) => formatNumber(split?.pointsPerGame)],
    ["Assists / Game", (split: RestSplit | undefined) => formatNumber(split?.assistsPerGame)],
    ["Minutes / Game", (split: RestSplit | undefined) => formatNumber(split?.minutesPerGame)],
    ["TS%", (split: RestSplit | undefined) => formatPercent(split?.trueShootingPercentage)],
  ] as const;

  return (
    <div className="comparison-table rest-comparison-table">
      <div className="comparison-head rest-comparison-row">
        <span>Stat</span>
        {columns.map(([, label]) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      {rows.map(([label, formatter]) => (
        <div className="comparison-row rest-comparison-row" key={label}>
          <span>{label}</span>
          {columns.map(([key]) => (
            <span key={key}>{formatter(splitByKey.get(key))}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

function PercentileBars({ rows }: { rows: ReturnType<typeof getPositionPercentiles> }) {
  return (
    <div className="percentile-list">
      {rows.map((row) => (
        <div className="percentile-row" key={row.key}>
          <span>{row.label}</span>
          <div
            className="percentile-track"
            aria-label={`${row.label} ${formatPercentile(row.value)}`}
          >
            <i style={{ width: `${row.value ?? 0}%` }} />
          </div>
          <strong>{formatPercentile(row.value)}</strong>
          <em>{row.higherIsBetter ? "higher" : "lower"} is better</em>
        </div>
      ))}
    </div>
  );
}

function SimilarPlayersPanel({
  mainSummary,
  players,
}: {
  mainSummary: PlayerSeasonSummary | undefined;
  players: SimilarPlayer[];
}) {
  const [hoveredPlayerId, setHoveredPlayerId] = useState<number | null>(null);
  const [hoverPosition, setHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const showTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      clearHoverTimer(showTimer);
      clearHoverTimer(hideTimer);
    },
    [],
  );

  if (players.length === 0) {
    return (
      <EmptyState
        title="No similar players"
        text="Stored season summaries are needed to rank statistical matches."
      />
    );
  }

  const hoveredPlayer = hoveredPlayerId
    ? players.find((item) => item.player.id === hoveredPlayerId)
    : undefined;

  function previewPlayer(playerId: number, target: HTMLElement) {
    clearHoverTimer(showTimer);
    clearHoverTimer(hideTimer);
    const rect = target.getBoundingClientRect();
    showTimer.current = setTimeout(() => {
      setHoveredPlayerId(playerId);
      setHoverPosition({
        top: Math.max(12, Math.min(rect.top, window.innerHeight - 200)),
        left: Math.max(12, Math.min(rect.right + 14, window.innerWidth - 336)),
      });
    }, 300);
  }

  function hidePreview() {
    clearHoverTimer(showTimer);
    clearHoverTimer(hideTimer);
    hideTimer.current = setTimeout(() => {
      setHoveredPlayerId(null);
    }, 140);
  }

  function keepPreviewOpen() {
    clearHoverTimer(hideTimer);
  }

  return (
    <div className="similar-player-list">
      {players.map((item) => (
        <a
          className="similar-player-row"
          href={`/players/${item.player.nba_player_id}`}
          key={item.player.id}
          onMouseEnter={(event) => previewPlayer(item.player.id, event.currentTarget)}
          onMouseLeave={hidePreview}
          style={getThemeStyle(item.player.team)}
        >
          <div className="similar-player-main">
            <div>
              <strong>{item.player.full_name}</strong>
              <span>
                {item.player.team?.abbreviation ?? "FA"} / {item.player.position ?? "Position TBD"}
              </span>
            </div>
            <div
              className="similar-stat-strip"
              aria-label={`${item.player.full_name} similar-player stats`}
            >
              <span>{formatNumber(item.summary.points_per_game)} PPG</span>
              <span>{formatNumber(item.summary.rebounds_per_game)} RPG</span>
              <span>{formatNumber(item.summary.assists_per_game)} APG</span>
              <span>{formatPercent(item.summary.true_shooting_percentage)} TS</span>
            </div>
          </div>
          <div className="similar-player-visual">
            <PlayerPortrait player={item.player} size="tiny" />
          </div>
          <div className="similar-score">
            <strong>{formatNumber(item.similarity_score, 1)}</strong>
            <span>match</span>
            <em>
              {item.shared_position
                ? "Same position"
                : `${formatNumber(item.minutes_difference)} MPG diff`}
            </em>
          </div>
        </a>
      ))}
      {hoveredPlayer && hoverPosition ? (
        <SimilarPlayerHoverCard
          item={hoveredPlayer}
          mainSummary={mainSummary}
          onMouseEnter={keepPreviewOpen}
          onMouseLeave={hidePreview}
          position={hoverPosition}
        />
      ) : null}
    </div>
  );
}

function SimilarPlayerHoverCard({
  item,
  mainSummary,
  onMouseEnter,
  onMouseLeave,
  position,
}: {
  item: SimilarPlayer;
  mainSummary: PlayerSeasonSummary | undefined;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  position: { top: number; left: number };
}) {
  return (
    <aside
      className="similar-player-hover-panel"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{ top: position.top, left: position.left }}
    >
      <div className="similar-player-hover-card" style={getThemeStyle(item.player.team)}>
        <strong>{item.player.full_name}</strong>
        <p>{buildSimilarityNote(mainSummary, item)}</p>
      </div>
    </aside>
  );
}

function buildSimilarityNote(
  mainSummary: PlayerSeasonSummary | undefined,
  item: SimilarPlayer,
): string {
  const comparisons = [
    {
      label: "scoring",
      main: mainSummary?.points_per_game,
      candidate: item.summary.points_per_game,
      scale: 30,
      suffix: "PPG",
      isPercent: false,
    },
    {
      label: "rebounding",
      main: mainSummary?.rebounds_per_game,
      candidate: item.summary.rebounds_per_game,
      scale: 12,
      suffix: "RPG",
      isPercent: false,
    },
    {
      label: "playmaking",
      main: mainSummary?.assists_per_game,
      candidate: item.summary.assists_per_game,
      scale: 10,
      suffix: "APG",
      isPercent: false,
    },
    {
      label: "shot efficiency",
      main: mainSummary?.true_shooting_percentage,
      candidate: item.summary.true_shooting_percentage,
      scale: 0.7,
      suffix: "",
      isPercent: true,
    },
  ];

  const ranked = comparisons
    .filter(
      (row): row is typeof row & { main: number; candidate: number } =>
        typeof row.main === "number" && typeof row.candidate === "number",
    )
    .map((row) => ({ ...row, gap: Math.abs(row.main - row.candidate) / row.scale }))
    .sort((left, right) => left.gap - right.gap);

  const statPhrase = ranked
    .slice(0, 2)
    .map((row) => {
      const mainValue = row.isPercent
        ? formatPercent(row.main)
        : `${formatNumber(row.main)} ${row.suffix}`;
      const candidateValue = row.isPercent
        ? formatPercent(row.candidate)
        : `${formatNumber(row.candidate)} ${row.suffix}`;
      return `${row.label} (${mainValue} vs ${candidateValue})`;
    })
    .join(" and ");

  const positionPhrase = item.shared_position
    ? "They play the same position"
    : "They play a different position";
  const minutesPhrase =
    typeof item.minutes_difference === "number"
      ? `, with a similar role (${formatNumber(item.minutes_difference)} MPG apart)`
      : "";
  const statSentence =
    statPhrase.length > 0
      ? ` The closest statistical overlap is ${statPhrase}.`
      : " Not enough stored data to compare individual stats yet.";

  return `${positionPhrase}${minutesPhrase}.${statSentence}`;
}

function clearHoverTimer(timer: MutableRefObject<ReturnType<typeof setTimeout> | null>) {
  if (timer.current) {
    clearTimeout(timer.current);
    timer.current = null;
  }
}

function TrendBadge({ label, value }: { label: string; value: string | null | undefined }) {
  const normalized = value ?? "insufficient_sample";
  const symbol = normalized === "improving" ? "Up" : normalized === "declining" ? "Down" : "Flat";
  const text = normalized.replaceAll("_", " ");

  return (
    <span className={`trend-badge ${normalized}`}>
      {label ? <strong>{label}</strong> : null}
      <span>{symbol}</span>
      <em>{text}</em>
    </span>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}

function ProfileHeaderSkeleton() {
  return (
    <>
      <span className="skeleton-avatar large" />
      <div className="profile-title">
        <span className="skeleton-line small" />
        <span className="skeleton-line title" />
        <span className="skeleton-line" />
      </div>
    </>
  );
}

function perGame(total: number | null | undefined, games: number): number | null {
  if (typeof total !== "number" || games <= 0) {
    return null;
  }
  return total / games;
}

function diff(left: number | null | undefined, right: number | null | undefined): number | null {
  if (typeof left !== "number" || typeof right !== "number") {
    return null;
  }
  return left - right;
}

function formatSignedNumber(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }
  const formatted = value.toFixed(digits);
  return value > 0 ? `+${formatted}` : formatted;
}

function formatSignedPercent(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }
  const formatted = `${(value * 100).toFixed(digits)}%`;
  return value > 0 ? `+${formatted}` : formatted;
}
