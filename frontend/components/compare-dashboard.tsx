"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
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
import { getGraphStroke, getTeamTheme, getThemeStyle } from "@/components/player-profile";
import { PlayerNumberMark } from "@/components/player-number-mark";
import { getAllPlayers, getDataStatus, getSeasons } from "@/lib/api/hoopsiq";
import { useCompare, usePlayerGames } from "@/lib/api/hooks";
import type {
  CompareMetric,
  ComparePlayer,
  CompareResponse,
  GameLogItem,
  PlayerListItem,
  RestSplits,
  SplitSummary,
} from "@/lib/api/schemas";
import { formatInteger, formatNumber, formatPercent } from "@/lib/format";

const GAMES_PARAMS = { limit: 100 } as const;

type PlayerSlot = "player_a" | "player_b";

type Verdict = {
  playerAWins: number;
  playerBWins: number;
  ties: number;
  decided: number;
  overall: PlayerSlot | "tie";
};

const seasonMetrics = [
  ["points_per_game", "Points"],
  ["rebounds_per_game", "Rebounds"],
  ["assists_per_game", "Assists"],
  ["minutes_per_game", "Minutes"],
  ["true_shooting_percentage", "TS%"],
  ["turnovers_per_game", "Turnovers"],
] as const;

const benchmarkMetrics = [
  ["points_per_game", "Points"],
  ["assists_per_game", "Assists"],
  ["true_shooting_percentage", "TS%"],
] as const;

const restLabels = [
  ["first_game", "First"],
  ["back_to_back", "B2B"],
  ["one_day_rest", "1 Day"],
  ["two_or_more_days_rest", "2+ Days"],
] as const;

const leaderMetricKeys = [
  "points_per_game",
  "rebounds_per_game",
  "assists_per_game",
  "true_shooting_percentage",
] as const;

const categoryGroupLabels: Record<string, string> = {
  season_averages: "season averages",
  efficiency: "efficiency",
  recent_form: "recent form",
  benchmarks: "position benchmarks",
};

type RecentEntry = {
  a: number;
  b: number;
  aName: string;
  bName: string;
  aTeam: string;
  bTeam: string;
};

const STAT_TYPES = ["Per Game", "Per 36", "Totals"] as const;
const MIN_GAMES_OPTIONS = ["1", "5", "10", "20"] as const;

const POPULAR_PAIRS: [string, string][] = [
  ["Luka Dončić", "Nikola Jokić"],
  ["Shai Gilgeous-Alexander", "Anthony Edwards"],
  ["Devin Booker", "Donovan Mitchell"],
  ["Jayson Tatum", "Giannis Antetokounmpo"],
  ["Victor Wembanyama", "Chet Holmgren"],
  ["Tyrese Haliburton", "Jalen Brunson"],
  ["Paolo Banchero", "Scottie Barnes"],
  ["Cooper Flagg", "Kon Knueppel"],
];

const RECENT_KEY = "hoopsiq:recent-compares";

function Ico({ children }: { children: ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      {children}
    </svg>
  );
}

const HERO_FEATURES: { icon: ReactNode; label: string }[] = [
  { icon: <Ico><path d="M5 21V11M12 21V4M19 21v-7" /></Ico>, label: "Advanced Stats" },
  { icon: <Ico><path d="M9 6 4 12l5 6M15 6l5 6-5 6" /></Ico>, label: "Head to Head" },
  {
    icon: (
      <Ico>
        <path d="M4 8h8M16 8h4M4 16h4M12 16h8" />
        <circle cx="14" cy="8" r="2" />
        <circle cx="10" cy="16" r="2" />
      </Ico>
    ),
    label: "Custom Ranges",
  },
  {
    icon: (
      <Ico>
        <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z" />
        <circle cx="12" cy="12" r="2.6" />
      </Ico>
    ),
    label: "Visual Insights",
  },
];

const BENEFITS: { body: string; icon: ReactNode; title: string }[] = [
  {
    body: "Compare traditional and advanced stats across multiple categories.",
    icon: <Ico><path d="M4 5h6v14H4zM14 5h6v14h-6z" /></Ico>,
    title: "Side-by-Side Stats",
  },
  {
    body: "See how each player performs against the other directly.",
    icon: <Ico><path d="M9 6 4 12l5 6M15 6l5 6-5 6" /></Ico>,
    title: "Head-to-Head",
  },
  {
    body: "Visualize performance trends over time and across the season.",
    icon: (
      <Ico>
        <path d="M4 16l5-5 4 3 7-8" />
        <path d="M17 6h4v4" />
      </Ico>
    ),
    title: "Trend Analysis",
  },
  {
    body: "Deep dive into advanced analytics and on-court impact.",
    icon: (
      <Ico>
        <circle cx="12" cy="12" r="8" />
        <circle cx="12" cy="12" r="3" />
      </Ico>
    ),
    title: "Advanced Metrics",
  },
];

export function CompareDashboard() {
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [seasons, setSeasons] = useState<string[]>(["2025-26"]);
  const [selectedSeason, setSelectedSeason] = useState("2025-26");
  const [statType, setStatType] = useState<(typeof STAT_TYPES)[number]>("Per Game");
  const [minGames, setMinGames] = useState<(typeof MIN_GAMES_OPTIONS)[number]>("10");
  const [playerA, setPlayerA] = useState<PlayerListItem | null>(null);
  const [playerB, setPlayerB] = useState<PlayerListItem | null>(null);
  const [confirmedPair, setConfirmedPair] = useState<{ a: number; b: number } | null>(null);
  const [recent, setRecent] = useState<RecentEntry[]>([]);
  const [hasInitialError, setHasInitialError] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const searchParams = useSearchParams();
  const appliedParamsRef = useRef(false);

  useEffect(() => {
    let isActive = true;
    setIsInitialLoading(true);
    setHasInitialError(false);

    Promise.all([getAllPlayers(), getDataStatus(), getSeasons()])
      .then(([allPlayers, status, seasonsResponse]) => {
        if (!isActive) {
          return;
        }
        setPlayers(allPlayers.filter((player) => player.active));
        const nextSeason = status.current_season || seasonsResponse.seasons[0] || "2025-26";
        setSeasons(seasonsResponse.seasons.length > 0 ? seasonsResponse.seasons : [nextSeason]);
        setSelectedSeason(nextSeason);
      })
      .catch(() => {
        if (isActive) {
          setHasInitialError(true);
        }
      })
      .finally(() => {
        if (isActive) {
          setIsInitialLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    setRecent(loadRecent());
  }, []);

  // Preselect + auto-confirm a pair passed from Quick Compare (/compare?a=&b=).
  useEffect(() => {
    if (appliedParamsRef.current || players.length === 0) {
      return;
    }
    const aParam = Number(searchParams?.get("a"));
    const bParam = Number(searchParams?.get("b"));
    if (!aParam || !bParam || aParam === bParam) {
      return;
    }
    const a = players.find((player) => player.nba_player_id === aParam);
    const b = players.find((player) => player.nba_player_id === bParam);
    if (!a || !b) {
      return;
    }
    appliedParamsRef.current = true;
    setPlayerA(a);
    setPlayerB(b);
    setConfirmedPair({ a: aParam, b: bParam });
  }, [players, searchParams]);

  const compareQuery = useCompare(
    confirmedPair?.a ?? null,
    confirmedPair?.b ?? null,
    selectedSeason,
  );
  const compare = compareQuery.data;

  const canConfirm =
    playerA !== null && playerB !== null && playerA.nba_player_id !== playerB.nba_player_id;

  const popular = useMemo(() => resolvePopularPairs(players), [players]);

  const recordRecent = (a: PlayerListItem, b: PlayerListItem) => {
    setRecent((prev) => {
      const entry: RecentEntry = {
        a: a.nba_player_id,
        b: b.nba_player_id,
        aName: a.full_name,
        bName: b.full_name,
        aTeam: a.team?.abbreviation ?? "FA",
        bTeam: b.team?.abbreviation ?? "FA",
      };
      const next = [entry, ...prev.filter((item) => !(item.a === entry.a && item.b === entry.b))].slice(
        0,
        8,
      );
      try {
        window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      } catch {
        /* storage unavailable — keep in-memory only */
      }
      return next;
    });
  };

  const runCompare = (a: PlayerListItem, b: PlayerListItem) => {
    setPlayerA(a);
    setPlayerB(b);
    setConfirmedPair({ a: a.nba_player_id, b: b.nba_player_id });
    recordRecent(a, b);
  };

  return (
    <AppShell active="Compare" variant="topbar">
      <div className="compare-dashboard">
        {hasInitialError ? (
          <div className="panel compare-empty">Comparison data is unavailable right now.</div>
        ) : isInitialLoading ? (
          <div className="panel compare-empty">Loading players...</div>
        ) : confirmedPair !== null ? (
          <div className="compare-report">
            <button
              className="compare-back"
              onClick={() => setConfirmedPair(null)}
              type="button"
            >
              ← New Comparison
            </button>
            {compareQuery.isError ? (
              <div className="panel compare-empty">
                Stored comparison data is missing for this pair.
              </div>
            ) : compare ? (
              <CompareContent compare={compare} />
            ) : (
              <div className="panel compare-empty">Building the comparison...</div>
            )}
          </div>
        ) : (
          <CompareLanding
            canConfirm={canConfirm}
            minGames={minGames}
            onClear={(slot) => (slot === "player_a" ? setPlayerA(null) : setPlayerB(null))}
            onCompare={() => {
              if (playerA && playerB) {
                runCompare(playerA, playerB);
              }
            }}
            onMinGames={setMinGames}
            onPair={runCompare}
            onRecent={(entry) => {
              const a = players.find((player) => player.nba_player_id === entry.a);
              const b = players.find((player) => player.nba_player_id === entry.b);
              if (a && b) {
                runCompare(a, b);
              }
            }}
            onSeason={setSelectedSeason}
            onSelect={(slot, player) =>
              slot === "player_a" ? setPlayerA(player) : setPlayerB(player)
            }
            onStatType={setStatType}
            playerA={playerA}
            playerB={playerB}
            players={players}
            popular={popular}
            recent={recent}
            season={selectedSeason}
            seasons={seasons}
            statType={statType}
          />
        )}
      </div>
    </AppShell>
  );
}

type CompareLandingProps = {
  canConfirm: boolean;
  minGames: (typeof MIN_GAMES_OPTIONS)[number];
  onClear: (slot: PlayerSlot) => void;
  onCompare: () => void;
  onMinGames: (value: (typeof MIN_GAMES_OPTIONS)[number]) => void;
  onPair: (a: PlayerListItem, b: PlayerListItem) => void;
  onRecent: (entry: RecentEntry) => void;
  onSeason: (value: string) => void;
  onSelect: (slot: PlayerSlot, player: PlayerListItem) => void;
  onStatType: (value: (typeof STAT_TYPES)[number]) => void;
  playerA: PlayerListItem | null;
  playerB: PlayerListItem | null;
  players: PlayerListItem[];
  popular: [PlayerListItem, PlayerListItem][];
  recent: RecentEntry[];
  season: string;
  seasons: string[];
  statType: (typeof STAT_TYPES)[number];
};

function CompareLanding({
  canConfirm,
  minGames,
  onClear,
  onCompare,
  onMinGames,
  onPair,
  onRecent,
  onSeason,
  onSelect,
  onStatType,
  playerA,
  playerB,
  players,
  popular,
  recent,
  season,
  seasons,
  statType,
}: CompareLandingProps) {
  return (
    <div className="compare-landing">
      <section className="compare-landing-hero">
        <div className="compare-hero-text">
          <h1>
            Compare Players.
            <br />
            See Who <span className="compare-grad">Stands Out.</span>
          </h1>
          <p>Select players to compare their stats, impact, and performance side by side.</p>
          <div className="compare-hero-features">
            {HERO_FEATURES.map((feature) => (
              <span className="compare-hero-feature" key={feature.label}>
                {feature.icon}
                {feature.label}
              </span>
            ))}
          </div>
        </div>
        <div className="compare-hero-visual" aria-hidden="true">
          <HeroOrb player={playerA} />
          <span className="compare-hero-vs">VS</span>
          <HeroOrb player={playerB} />
        </div>
      </section>

      <div className="compare-landing-grid">
        <div className="compare-landing-main">
          <section className="panel compare-select-panel">
            <div className="compare-section-heading">
              <h2>Select Players</h2>
              <p>Choose 2 players to compare</p>
            </div>
            <div className="compare-slot-row">
              <CompareSlot
                excludeId={playerB?.nba_player_id}
                label="Player A"
                onClear={() => onClear("player_a")}
                onSelect={(player) => onSelect("player_a", player)}
                players={players}
                selected={playerA}
              />
              <span className="compare-slot-vs" aria-hidden="true">
                VS
              </span>
              <CompareSlot
                excludeId={playerA?.nba_player_id}
                label="Player B"
                onClear={() => onClear("player_b")}
                onSelect={(player) => onSelect("player_b", player)}
                players={players}
                selected={playerB}
              />
            </div>
            <div className="compare-filter-row">
              <label className="compare-field">
                <span>Competition</span>
                <select disabled value="NBA">
                  <option value="NBA">NBA</option>
                </select>
              </label>
              <label className="compare-field">
                <span>Season</span>
                <select onChange={(event) => onSeason(event.target.value)} value={season}>
                  {seasons.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label className="compare-field">
                <span>Stat Type</span>
                <select
                  onChange={(event) =>
                    onStatType(event.target.value as (typeof STAT_TYPES)[number])
                  }
                  value={statType}
                >
                  {STAT_TYPES.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label className="compare-field">
                <span>Minimum Games</span>
                <select
                  onChange={(event) =>
                    onMinGames(event.target.value as (typeof MIN_GAMES_OPTIONS)[number])
                  }
                  value={minGames}
                >
                  {MIN_GAMES_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="compare-run-button"
                disabled={!canConfirm}
                onClick={onCompare}
                type="button"
              >
                Compare Players
              </button>
            </div>
          </section>

          <section className="compare-benefits" aria-label="What you'll get">
            <div className="compare-section-heading">
              <h2>What You&apos;ll Get</h2>
            </div>
            <div className="compare-benefit-grid">
              {BENEFITS.map((benefit) => (
                <article className="compare-benefit" key={benefit.title}>
                  <span className="compare-benefit-icon">{benefit.icon}</span>
                  <strong>{benefit.title}</strong>
                  <p>{benefit.body}</p>
                </article>
              ))}
            </div>
          </section>

          {recent.length > 0 ? (
            <section className="panel compare-recent">
              <div className="compare-section-heading">
                <h2>Recently Compared</h2>
              </div>
              <div className="compare-recent-grid">
                {recent.slice(0, 4).map((entry) => (
                  <button
                    className="compare-recent-row"
                    key={`${entry.a}-${entry.b}`}
                    onClick={() => onRecent(entry)}
                    type="button"
                  >
                    <span className="compare-recent-names">
                      <strong>{shortName(entry.aName)}</strong>
                      <em>vs</em>
                      <strong>{shortName(entry.bName)}</strong>
                    </span>
                    <span className="compare-recent-teams">
                      {entry.aTeam} · {entry.bTeam}
                    </span>
                  </button>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <aside className="compare-landing-side">
          <section className="panel compare-popular">
            <div className="compare-section-heading">
              <h2>Popular Comparisons</h2>
            </div>
            {popular.length > 0 ? (
              <div className="compare-popular-list">
                {popular.map(([a, b]) => (
                  <button
                    className="compare-popular-row"
                    key={`${a.nba_player_id}-${b.nba_player_id}`}
                    onClick={() => onPair(a, b)}
                    type="button"
                  >
                    <span className="compare-popular-side">
                      <span className="compare-popular-orb player-portrait" style={getThemeStyle(a.team)}>
                        <PlayerNumberMark player={a} />
                      </span>
                      <span>{shortName(a.full_name)}</span>
                    </span>
                    <em className="compare-popular-vs">vs</em>
                    <span className="compare-popular-side end">
                      <span>{shortName(b.full_name)}</span>
                      <span className="compare-popular-orb player-portrait" style={getThemeStyle(b.team)}>
                        <PlayerNumberMark player={b} />
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="compare-popular-empty">
                Suggested matchups appear once player data loads.
              </p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}

function CompareSlot({
  excludeId,
  label,
  onClear,
  onSelect,
  players,
  selected,
}: {
  excludeId: number | undefined;
  label: string;
  onClear: () => void;
  onSelect: (player: PlayerListItem) => void;
  players: PlayerListItem[];
  selected: PlayerListItem | null;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const matches = useMemo(() => {
    const normalized = normalizeSearchText(query);
    if (!normalized) {
      return [];
    }
    return players
      .filter(
        (player) =>
          player.nba_player_id !== excludeId &&
          (normalizeSearchText(player.full_name).includes(normalized) ||
            (player.team?.abbreviation.toLowerCase().includes(normalized) ?? false)),
      )
      .slice(0, 7);
  }, [excludeId, players, query]);

  if (selected) {
    const meta = [
      selected.position ?? "—",
      selected.team?.name ?? "Free Agent",
      selected.jersey_number ? `#${selected.jersey_number}` : null,
    ]
      .filter(Boolean)
      .join(" • ");
    return (
      <div className="compare-slot filled" style={getThemeStyle(selected.team)}>
        <button
          aria-label={`Remove ${selected.full_name}`}
          className="compare-slot-clear"
          onClick={onClear}
          type="button"
        >
          ×
        </button>
        <span className="compare-slot-avatar player-portrait">
          <PlayerNumberMark player={selected} />
        </span>
        <strong className="compare-slot-name">{selected.full_name}</strong>
        <span className="compare-slot-meta">{meta}</span>
      </div>
    );
  }

  if (open) {
    return (
      <div className="compare-slot searching">
        <input
          aria-label={`${label} search`}
          autoFocus
          onBlur={() => {
            window.setTimeout(() => setOpen(false), 140);
          }}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search a player..."
          value={query}
        />
        {matches.length > 0 ? (
          <div aria-label={`${label} results`} className="compare-slot-results" role="listbox">
            {matches.map((player) => (
              <button
                aria-selected="false"
                key={player.id}
                onClick={() => {
                  onSelect(player);
                  setOpen(false);
                  setQuery("");
                }}
                onMouseDown={(event) => event.preventDefault()}
                role="option"
                type="button"
              >
                <strong>{player.full_name}</strong>
                <em>
                  {player.team?.abbreviation ?? "FA"} / {player.position ?? "Position TBD"}
                </em>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <button className="compare-slot empty" onClick={() => setOpen(true)} type="button">
      <span className="compare-slot-plus" aria-hidden="true">
        +
      </span>
      <strong>Add Player</strong>
      <span>Click to select</span>
    </button>
  );
}

function HeroOrb({ player }: { player: PlayerListItem | null }) {
  if (!player) {
    return (
      <span className="compare-hero-orb empty">
        <span className="compare-hero-orb-mark">?</span>
      </span>
    );
  }
  return (
    <span className="compare-hero-orb filled" style={getThemeStyle(player.team)}>
      <span className="compare-hero-orb-number">
        <PlayerNumberMark player={player} />
      </span>
      <span className="compare-hero-orb-name">{player.last_name}</span>
    </span>
  );
}

function loadRecent(): RecentEntry[] {
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as RecentEntry[]) : [];
  } catch {
    return [];
  }
}

function resolvePopularPairs(players: PlayerListItem[]): [PlayerListItem, PlayerListItem][] {
  if (players.length === 0) {
    return [];
  }
  const byName = new Map(
    players.map((player) => [normalizeSearchText(player.full_name), player]),
  );
  const pairs: [PlayerListItem, PlayerListItem][] = [];
  POPULAR_PAIRS.forEach(([aName, bName]) => {
    const a = byName.get(normalizeSearchText(aName));
    const b = byName.get(normalizeSearchText(bName));
    if (a && b) {
      pairs.push([a, b]);
    }
  });
  return pairs;
}

function shortName(fullName: string): string {
  const parts = fullName.trim().split(" ");
  if (parts.length < 2) {
    return fullName;
  }
  return `${parts[0][0]}. ${parts.slice(1).join(" ")}`;
}

function CompareContent({ compare }: { compare: CompareResponse }) {
  const verdict = useMemo(() => buildVerdict(compare), [compare]);
  const gamesA = usePlayerGames(
    compare.player_a.player.nba_player_id,
    compare.season,
    GAMES_PARAMS,
  );
  const gamesB = usePlayerGames(
    compare.player_b.player.nba_player_id,
    compare.season,
    GAMES_PARAMS,
  );
  const seriesA = useMemo(() => buildCumulativeSeries(gamesA.data?.items), [gamesA.data]);
  const seriesB = useMemo(() => buildCumulativeSeries(gamesB.data?.items), [gamesB.data]);
  const gamesLoading = gamesA.isLoading || gamesB.isLoading;

  return (
    <>
      <CategoryLeadersStrip compare={compare} verdict={verdict} />

      <div className="compare-split">
        <CompareHalf compare={compare} slot="player_a" subject={compare.player_a} />
        <CompareHalf compare={compare} slot="player_b" subject={compare.player_b} />
        <span className="compare-vs-badge" aria-hidden="true">
          VS
        </span>
      </div>

      <section className="panel compare-table-panel">
        <PanelHeading
          title="Category Winners"
          subtitle="Every tracked metric with the statistical winner."
        />
        <MetricComparisonTable
          metrics={compare.category_winners}
          playerA={compare.player_a.player.full_name}
          playerB={compare.player_b.player.full_name}
        />
      </section>

      <StatGraphsSection
        compare={compare}
        gamesLoading={gamesLoading}
        seriesA={seriesA}
        seriesB={seriesB}
      />

      <VerdictPanel compare={compare} verdict={verdict} />
    </>
  );
}

function StatGraphsSection({
  compare,
  gamesLoading,
  seriesA,
  seriesB,
}: {
  compare: CompareResponse;
  gamesLoading: boolean;
  seriesA: CumulativePoint[];
  seriesB: CumulativePoint[];
}) {
  const nameA = compare.player_a.player.full_name;
  const nameB = compare.player_b.player.full_name;
  const themeA = getTeamTheme(compare.player_a.player.team);
  const themeB = getTeamTheme(compare.player_b.player.team);

  const graphs: Array<{
    graphKey: string;
    title: string;
    isPercent?: boolean;
    lines: TrendLineConfig[];
  }> = [
    {
      graphKey: "offense",
      title: "Offensive",
      lines: [
        { field: "ppg", label: `${nameA} PPG`, stroke: getGraphStroke(themeA.primary) },
        { field: "apg", label: `${nameA} APG`, stroke: getGraphStroke(themeA.accent) },
        {
          field: "ppg",
          label: `${nameB} PPG`,
          stroke: getGraphStroke(themeB.primary),
          player: "b",
        },
        { field: "apg", label: `${nameB} APG`, stroke: getGraphStroke(themeB.accent), player: "b" },
      ],
    },
    {
      graphKey: "defense",
      title: "Defensive",
      lines: [
        { field: "spg", label: `${nameA} SPG`, stroke: getGraphStroke(themeA.primary) },
        { field: "bpg", label: `${nameA} BPG`, stroke: getGraphStroke(themeA.accent) },
        {
          field: "spg",
          label: `${nameB} SPG`,
          stroke: getGraphStroke(themeB.primary),
          player: "b",
        },
        { field: "bpg", label: `${nameB} BPG`, stroke: getGraphStroke(themeB.accent), player: "b" },
      ],
    },
    {
      graphKey: "trueshooting",
      title: "True Shooting",
      isPercent: true,
      lines: [
        { field: "tsPct", label: `${nameA} TS%`, stroke: getGraphStroke(themeA.primary) },
        {
          field: "tsPct",
          label: `${nameB} TS%`,
          stroke: getGraphStroke(themeB.primary),
          player: "b",
        },
      ],
    },
    {
      graphKey: "efficiency",
      title: "Efficiency",
      isPercent: true,
      lines: [
        { field: "fgPct", label: `${nameA} FG%`, stroke: getGraphStroke(themeA.primary) },
        { field: "tpPct", label: `${nameA} 3P%`, stroke: getGraphStroke(themeA.accent) },
        {
          field: "fgPct",
          label: `${nameB} FG%`,
          stroke: getGraphStroke(themeB.primary),
          player: "b",
        },
        {
          field: "tpPct",
          label: `${nameB} 3P%`,
          stroke: getGraphStroke(themeB.accent),
          player: "b",
        },
      ],
    },
  ];

  return (
    <section className="panel compare-graphs-panel">
      <PanelHeading
        title="Statistical Graphs"
        subtitle="Line trends colored by each player's team. Toggle Recent or full Season."
      />
      <div className="compare-graphs-grid">
        {graphs.map((graph) => (
          <CompareTrendGraph
            isLoading={gamesLoading}
            isPercent={graph.isPercent}
            key={graph.graphKey}
            lines={graph.lines}
            seriesA={seriesA}
            seriesB={seriesB}
            title={graph.title}
          />
        ))}
      </div>
    </section>
  );
}

function CategoryLeadersStrip({
  compare,
  verdict,
}: {
  compare: CompareResponse;
  verdict: Verdict;
}) {
  const leaders = leaderMetricKeys
    .map((key) => compare.category_winners.find((metric) => metric.key === key))
    .filter((metric): metric is CompareMetric => metric !== undefined);

  return (
    <section className="panel compare-leaders">
      {leaders.map((metric) => {
        const leaderName =
          metric.winner === "player_a"
            ? compare.player_a.player.full_name
            : metric.winner === "player_b"
              ? compare.player_b.player.full_name
              : "Tie";
        const leaderValue =
          metric.winner === "player_b" ? metric.player_b_value : metric.player_a_value;
        return (
          <span className="compare-leader-cell" key={metric.key}>
            <em>{metric.label}</em>
            <strong>{leaderName}</strong>
            <small>{formatMetricValue(metric.key, leaderValue)}</small>
          </span>
        );
      })}
      <span className="compare-leader-cell overall">
        <em>Overall Leader</em>
        <strong>{overallLeaderName(compare, verdict)}</strong>
        <small>
          {verdict.overall === "tie"
            ? `${verdict.playerAWins}-${verdict.playerBWins} in categories`
            : `Wins ${Math.max(verdict.playerAWins, verdict.playerBWins)} of ${verdict.decided} categories`}
        </small>
      </span>
    </section>
  );
}

function CompareHalf({
  compare,
  slot,
  subject,
}: {
  compare: CompareResponse;
  slot: PlayerSlot;
  subject: ComparePlayer;
}) {
  return (
    <div className="compare-half" style={getThemeStyle(subject.player.team)}>
      <article className="panel compare-player-card">
        <div className="compare-player-card-header">
          <span className="compare-jersey-box" aria-hidden="true">
            <PlayerNumberMark player={subject.player} />
          </span>
          <div>
            <span>{slot === "player_a" ? "Player A" : "Player B"}</span>
            <h2>{subject.player.full_name}</h2>
            <p>
              {subject.player.team
                ? `${subject.player.team.city} ${subject.player.team.name}`
                : "Free Agent"}{" "}
              / {subject.player.position ?? "Position TBD"}
              {subject.player.jersey_number ? ` / #${subject.player.jersey_number}` : ""}
            </p>
          </div>
        </div>
        <div className="compare-stat-grid">
          {seasonMetrics.map(([key, label]) => (
            <span key={key}>
              <em>{label}</em>
              <strong>
                {key === "true_shooting_percentage"
                  ? formatPercent(subject.summary[key])
                  : formatNumber(subject.summary[key])}
              </strong>
            </span>
          ))}
        </div>
      </article>

      <section className="panel compare-table-panel">
        <PanelHeading title="Recent Form" subtitle="Five-game and ten-game windows." />
        <div className="compare-metric-table compact">
          <div className="compare-metric-head three">
            <span>Window</span>
            <span>Production</span>
            <span>Games</span>
          </div>
          {(
            [
              ["Last 5", subject.recent_5],
              ["Last 10", subject.recent_10],
            ] as const
          ).map(([label, window]) => (
            <div className="compare-metric-row three" key={label}>
              <span>{label}</span>
              <strong>
                {formatNumber(window.points)} PPG / {formatNumber(window.assists)} APG
              </strong>
              <span>{formatInteger(window.games)}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel compare-table-panel">
        <PanelHeading title="Home / Away" subtitle="Per-game split context." />
        <SplitComparisonRows
          first={subject.splits.home}
          firstLabel="Home"
          second={subject.splits.away}
          secondLabel="Away"
        />
      </section>

      <section className="panel compare-table-panel">
        <PanelHeading title="Rest Splits" subtitle="Previous game spacing." />
        <div className="compare-rest-grid">
          {restLabels.map(([key, label]) => {
            const split = subject.rest_splits[key as keyof RestSplits];
            return (
              <span key={key}>
                <em>{label}</em>
                <strong>{formatInteger(split?.games)}</strong>
                <small>{formatNumber(perGame(split?.points, split?.games))} PPG</small>
              </span>
            );
          })}
        </div>
      </section>

      <section className="panel compare-table-panel">
        <PanelHeading
          title="Position Percentiles"
          subtitle={
            compare.position_match ? "Shared position benchmark." : "Own-position benchmark."
          }
        />
        <div className="compare-benchmark-list">
          {benchmarkMetrics.map(([key, label]) => {
            const value = numericValue(subject.benchmarks.position_percentiles[key]);
            return (
              <div className="compare-benchmark-row" key={key}>
                <span>{label}</span>
                <i>
                  <b style={{ width: `${value ?? 0}%` }} />
                </i>
                <strong>{formatPercentile(value)}</strong>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function VerdictPanel({ compare, verdict }: { compare: CompareResponse; verdict: Verdict }) {
  const takeaways = useMemo(() => buildTakeaways(compare), [compare]);

  return (
    <section className="panel compare-verdict">
      <div className="compare-verdict-headline">
        <em>Statistical Verdict</em>
        <h2>
          {verdict.overall === "tie"
            ? "Dead even across tracked categories"
            : `${overallLeaderName(compare, verdict)} is the better overall player`}
        </h2>
        <p>
          Based on {verdict.decided} tracked statistical categories:{" "}
          {compare.player_a.player.full_name} wins {verdict.playerAWins},{" "}
          {compare.player_b.player.full_name} wins {verdict.playerBWins}
          {verdict.ties > 0 ? `, with ${verdict.ties} tied` : ""}.
        </p>
        <p className="compare-verdict-context">{compare.position_context}</p>
      </div>
      <ul className="compare-verdict-takeaways">
        {takeaways.map((takeaway) => (
          <li key={takeaway}>{takeaway}</li>
        ))}
      </ul>
    </section>
  );
}

function MetricComparisonTable({
  metrics,
  playerA,
  playerB,
}: {
  metrics: CompareMetric[];
  playerA: string;
  playerB: string;
}) {
  return (
    <div className="compare-metric-table">
      <div className="compare-metric-head">
        <span>Metric</span>
        <span>{playerA}</span>
        <span>{playerB}</span>
        <span>Winner</span>
      </div>
      {metrics.map((metric) => (
        <div className="compare-metric-row" key={metric.key}>
          <span>{metric.label}</span>
          <strong>{formatMetricValue(metric.key, metric.player_a_value)}</strong>
          <strong>{formatMetricValue(metric.key, metric.player_b_value)}</strong>
          <WinnerBadge metric={metric} playerA={playerA} playerB={playerB} />
        </div>
      ))}
    </div>
  );
}

type TrendMode = "recent" | "season";

type TrendLineConfig = {
  field: NumericSeriesField;
  label: string;
  stroke: string;
  player?: "a" | "b";
};

const RECENT_WINDOW = 10;

function CompareTrendGraph({
  isLoading = false,
  isPercent = false,
  lines,
  seriesA,
  seriesB,
  title,
}: {
  isLoading?: boolean;
  isPercent?: boolean;
  lines: TrendLineConfig[];
  seriesA: CumulativePoint[];
  seriesB: CumulativePoint[];
  title: string;
}) {
  const [mode, setMode] = useState<TrendMode>("recent");
  const data = useMemo(
    () => buildTrendChartData(seriesA, seriesB, lines, mode),
    [lines, mode, seriesA, seriesB],
  );
  const hasValues = data.some((row) =>
    lines.some((_, index) => typeof row[`line${index}`] === "number"),
  );

  return (
    <figure className="compare-trend-graph" aria-label={`${title} trend chart`}>
      <div className="compare-graph-head">
        <figcaption>{title}</figcaption>
        <div className="segmented" role="group" aria-label={`${title} window`}>
          <button
            className={mode === "recent" ? "active" : ""}
            onClick={() => setMode("recent")}
            type="button"
          >
            Recent
          </button>
          <button
            className={mode === "season" ? "active" : ""}
            onClick={() => setMode("season")}
            type="button"
          >
            Season
          </button>
        </div>
      </div>
      {isLoading ? (
        <div className="compare-empty small">Loading game logs...</div>
      ) : !hasValues ? (
        <div className="compare-empty small">Data unavailable.</div>
      ) : (
        <ResponsiveContainer height={230} width="100%">
          <LineChart data={data} margin={{ bottom: 4, left: 0, right: 12, top: 12 }}>
            <CartesianGrid stroke="rgba(129, 156, 196, 0.16)" strokeDasharray="4 6" />
            <XAxis dataKey="label" stroke="#9aa8bc" tickLine={false} />
            <YAxis
              domain={isPercent ? [0, 100] : [0, "auto"]}
              stroke="#9aa8bc"
              tickLine={false}
              width={34}
            />
            <Tooltip
              contentStyle={{
                background: "#081525",
                border: "1px solid rgba(129, 156, 196, 0.34)",
                borderRadius: "8px",
                color: "#f5f8ff",
              }}
              formatter={(value, name) => [
                typeof value === "number"
                  ? isPercent
                    ? `${value.toFixed(1)}%`
                    : formatNumber(value, 1)
                  : "--",
                String(name),
              ]}
              labelFormatter={(label) => `Game ${String(label).replace("G", "")}`}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {lines.map((line, index) => (
              <Line
                connectNulls
                dataKey={`line${index}`}
                dot={false}
                isAnimationActive={false}
                key={line.label}
                name={line.label}
                stroke={line.stroke}
                strokeWidth={2}
                type="monotone"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </figure>
  );
}

function SplitComparisonRows({
  first,
  firstLabel,
  second,
  secondLabel,
}: {
  first: SplitSummary | null;
  firstLabel: string;
  second: SplitSummary | null;
  secondLabel: string;
}) {
  return (
    <div className="compare-metric-table compact">
      <div className="compare-metric-head">
        <span>Stat</span>
        <span>{firstLabel}</span>
        <span>{secondLabel}</span>
        <span>Diff</span>
      </div>
      {[
        ["Games", first?.games, second?.games, "number"],
        [
          "Points / Game",
          perGame(first?.points, first?.games),
          perGame(second?.points, second?.games),
          "number",
        ],
        [
          "Assists / Game",
          perGame(first?.assists, first?.games),
          perGame(second?.assists, second?.games),
          "number",
        ],
        ["TS%", first?.true_shooting_percentage, second?.true_shooting_percentage, "percent"],
      ].map(([label, firstValue, secondValue, format]) => (
        <div className="compare-metric-row" key={String(label)}>
          <span>{label}</span>
          <strong>
            {format === "percent"
              ? formatPercent(firstValue as number | null)
              : formatNumber(firstValue as number | null)}
          </strong>
          <strong>
            {format === "percent"
              ? formatPercent(secondValue as number | null)
              : formatNumber(secondValue as number | null)}
          </strong>
          <span>
            {formatSignedDiff(
              firstValue as number | null,
              secondValue as number | null,
              format === "percent",
            )}
          </span>
        </div>
      ))}
    </div>
  );
}

function PanelHeading({ subtitle, title }: { subtitle: string; title: string }) {
  return (
    <div className="compare-panel-heading">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  );
}

function WinnerBadge({
  metric,
  playerA,
  playerB,
}: {
  metric: CompareMetric;
  playerA: string;
  playerB: string;
}) {
  const label =
    metric.winner === "player_a"
      ? playerA
      : metric.winner === "player_b"
        ? playerB
        : metric.winner === "tie"
          ? "Tie"
          : "--";
  return <span className={`winner-badge ${metric.winner ?? "none"}`}>{label}</span>;
}

function buildVerdict(compare: CompareResponse): Verdict {
  let playerAWins = 0;
  let playerBWins = 0;
  let ties = 0;
  compare.category_winners.forEach((metric) => {
    if (metric.winner === "player_a") {
      playerAWins += 1;
    } else if (metric.winner === "player_b") {
      playerBWins += 1;
    } else if (metric.winner === "tie") {
      ties += 1;
    }
  });
  const decided = playerAWins + playerBWins + ties;
  const overall =
    playerAWins > playerBWins ? "player_a" : playerBWins > playerAWins ? "player_b" : "tie";
  return { playerAWins, playerBWins, ties, decided, overall };
}

function overallLeaderName(compare: CompareResponse, verdict: Verdict): string {
  if (verdict.overall === "player_a") {
    return compare.player_a.player.full_name;
  }
  if (verdict.overall === "player_b") {
    return compare.player_b.player.full_name;
  }
  return "Even";
}

function buildTakeaways(compare: CompareResponse): string[] {
  const groups = new Map<string, { a: number; b: number }>();
  compare.category_winners.forEach((metric) => {
    const group = groups.get(metric.category) ?? { a: 0, b: 0 };
    if (metric.winner === "player_a") {
      group.a += 1;
    } else if (metric.winner === "player_b") {
      group.b += 1;
    }
    groups.set(metric.category, group);
  });

  const takeaways: string[] = [];
  groups.forEach((counts, category) => {
    const label = categoryGroupLabels[category] ?? category;
    if (counts.a === counts.b) {
      takeaways.push(`The ${label} categories are split evenly (${counts.a}-${counts.b}).`);
      return;
    }
    const leader =
      counts.a > counts.b ? compare.player_a.player.full_name : compare.player_b.player.full_name;
    takeaways.push(
      `${leader} leads the ${label} categories ${Math.max(counts.a, counts.b)}-${Math.min(counts.a, counts.b)}.`,
    );
  });
  return takeaways;
}

type CumulativePoint = {
  ppg: number | null;
  apg: number | null;
  spg: number | null;
  bpg: number | null;
  fgPct: number | null;
  tpPct: number | null;
  tsPct: number | null;
};

type NumericSeriesField = keyof CumulativePoint;

// Season-to-date running average after each game, so the line shows how the
// stat trended across the whole season rather than noisy single-game spikes.
function buildCumulativeSeries(games: GameLogItem[] | undefined): CumulativePoint[] {
  if (!games || games.length === 0) {
    return [];
  }
  const ordered = [...games].sort((left, right) => left.game_date.localeCompare(right.game_date));
  let points = 0;
  let assists = 0;
  let steals = 0;
  let blocks = 0;
  let fieldGoalsMade = 0;
  let fieldGoalsAttempted = 0;
  let threePointersMade = 0;
  let threePointersAttempted = 0;
  let freeThrowsAttempted = 0;

  return ordered.map((game, index) => {
    points += game.points;
    assists += game.assists;
    steals += game.steals;
    blocks += game.blocks;
    fieldGoalsMade += game.field_goals_made;
    fieldGoalsAttempted += game.field_goals_attempted;
    threePointersMade += game.three_pointers_made;
    threePointersAttempted += game.three_pointers_attempted;
    freeThrowsAttempted += game.free_throws_attempted;
    const played = index + 1;
    const trueShootingDenominator = 2 * (fieldGoalsAttempted + 0.44 * freeThrowsAttempted);
    return {
      ppg: points / played,
      apg: assists / played,
      spg: steals / played,
      bpg: blocks / played,
      fgPct: fieldGoalsAttempted > 0 ? (fieldGoalsMade / fieldGoalsAttempted) * 100 : null,
      tpPct: threePointersAttempted > 0 ? (threePointersMade / threePointersAttempted) * 100 : null,
      tsPct: trueShootingDenominator > 0 ? (points / trueShootingDenominator) * 100 : null,
    };
  });
}

function buildTrendChartData(
  seriesA: CumulativePoint[],
  seriesB: CumulativePoint[],
  lines: TrendLineConfig[],
  mode: TrendMode,
): Array<Record<string, number | string | null>> {
  const length = Math.max(seriesA.length, seriesB.length);
  const startIndex = mode === "recent" ? Math.max(0, length - RECENT_WINDOW) : 0;
  const rows: Array<Record<string, number | string | null>> = [];
  for (let index = startIndex; index < length; index += 1) {
    const row: Record<string, number | string | null> = { label: `G${index + 1}` };
    lines.forEach((line, lineIndex) => {
      const source = line.player === "b" ? seriesB[index] : seriesA[index];
      row[`line${lineIndex}`] = source ? source[line.field] : null;
    });
    rows.push(row);
  }
  return rows;
}

function formatMetricValue(key: string, value: number | null): string {
  if (key.includes("true_shooting")) {
    return formatPercent(value);
  }
  if (key.includes("percentile")) {
    return formatPercentile(value);
  }
  return formatNumber(value);
}

function perGame(
  total: number | null | undefined,
  games: number | null | undefined,
): number | null {
  if (typeof total !== "number" || typeof games !== "number" || games <= 0) {
    return null;
  }
  return total / games;
}

function normalizeSearchText(value: string): string {
  return value.trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function numericValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatPercentile(value: number | null): string {
  return typeof value === "number" ? `${Math.round(value)}th` : "--";
}

function formatSignedDiff(
  firstValue: number | null,
  secondValue: number | null,
  isPercent: boolean,
): string {
  if (typeof firstValue !== "number" || typeof secondValue !== "number") {
    return "--";
  }
  const diff = firstValue - secondValue;
  const formatted = isPercent ? `${(diff * 100).toFixed(1)}%` : diff.toFixed(1);
  return diff > 0 ? `+${formatted}` : formatted;
}
