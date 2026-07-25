"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { getThemeStyle } from "@/components/player-profile";
import { PlayerPortrait } from "@/components/home-dashboard";
import { getAllPlayers, getDataStatus, getSeasonSummaries } from "@/lib/api/hoopsiq";
import type { PlayerListItem, PlayerSeasonSummary, Team } from "@/lib/api/schemas";
import { formatInteger, formatNumber, formatPercent } from "@/lib/format";

type PositionCategory = "Guard" | "Wing" | "Forward" | "Center";

const minEfficiencyMinutes = 1500;

type PlayerRow = {
  player: PlayerListItem;
  summary: PlayerSeasonSummary | undefined;
};

type RankedRow = {
  player: PlayerListItem;
  summary: PlayerSeasonSummary;
};

export function PlayersDashboard() {
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [summaries, setSummaries] = useState<Record<number, PlayerSeasonSummary>>({});
  const [season, setSeason] = useState("2025-26");
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isStatsLoading, setIsStatsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let isActive = true;
    setIsInitialLoading(true);
    setHasError(false);

    Promise.all([getAllPlayers(), getDataStatus()])
      .then(([allPlayers, statusResponse]) => {
        if (!isActive) {
          return;
        }
        setPlayers(allPlayers.filter((player) => player.active));
        setSeason(statusResponse.current_season);
      })
      .catch(() => {
        if (isActive) {
          setHasError(true);
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
    let isActive = true;
    setIsStatsLoading(true);

    getSeasonSummaries(season)
      .then((response) => {
        if (!isActive) {
          return;
        }
        const byPlayerId: Record<number, PlayerSeasonSummary> = {};
        response.items.forEach((item) => {
          byPlayerId[item.nba_player_id] = item;
        });
        setSummaries(byPlayerId);
      })
      .finally(() => {
        if (isActive) {
          setIsStatsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [season]);

  const rows = useMemo<PlayerRow[]>(
    () => players.map((player) => ({ player, summary: summaries[player.nba_player_id] })),
    [players, summaries],
  );

  const positionCounts = useMemo(() => {
    const counts: Record<PositionCategory, number> = { Guard: 0, Wing: 0, Forward: 0, Center: 0 };
    players.forEach((player) => {
      const category = classifyPosition(player.position);
      if (category) {
        counts[category] += 1;
      }
    });
    return counts;
  }, [players]);

  const avgMinutes = useMemo(() => {
    const values = rows
      .map((row) => row.summary?.minutes_per_game)
      .filter((value): value is number => typeof value === "number");
    return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
  }, [rows]);

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    if (normalizedSearch.length === 0) {
      return rows;
    }
    return rows.filter(
      ({ player }) =>
        player.full_name.toLowerCase().includes(normalizedSearch) ||
        (player.team?.abbreviation.toLowerCase().includes(normalizedSearch) ?? false) ||
        (player.team ? getTeamName(player.team).toLowerCase().includes(normalizedSearch) : false),
    );
  }, [rows, search]);

  const sortedRows = useMemo(
    () =>
      [...filteredRows].sort(
        (left, right) => (right.summary?.points_per_game ?? -1) - (left.summary?.points_per_game ?? -1),
      ),
    [filteredRows],
  );

  const defaultDisplayCap = 8;
  const visibleRows =
    search.trim().length > 0 ? sortedRows : sortedRows.slice(0, defaultDisplayCap);

  const rankedRows = useMemo(
    () =>
      rows.filter(
        (row): row is RankedRow => row.summary !== undefined && typeof row.summary === "object",
      ),
    [rows],
  );

  const topByCategory = useMemo(
    () => ({
      points: topRanked(rankedRows, "points_per_game", 5),
      assists: topRanked(rankedRows, "assists_per_game", 5),
      rebounds: topRanked(rankedRows, "rebounds_per_game", 5),
      efficiency: topRanked(rankedRows, "true_shooting_percentage", 5, minEfficiencyMinutes),
    }),
    [rankedRows],
  );

  const spotlightRow = topByCategory.points[0];

  if (hasError) {
    return (
      <AppShell active="Players" variant="topbar">
        <div className="players-page-layout">
          <div className="rosters-empty">Player data is unavailable right now.</div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell active="Players" variant="topbar">
      <div className="players-page-layout">
        <section className="players-main">
          <div className="players-heading-row">
            <div>
              <h1>NBA Players</h1>
              <p>Browse players, explore trends, and compare performance across the league.</p>
            </div>
          </div>

          <div className="players-stat-cards">
            <StatCard label="Active Players" value={formatInteger(players.length)} />
            <StatCard
              label="Guards"
              value={formatInteger(positionCounts.Guard)}
              sub={leaguePercent(positionCounts.Guard, players.length)}
            />
            <StatCard
              label="Forwards"
              value={formatInteger(positionCounts.Forward)}
              sub={leaguePercent(positionCounts.Forward, players.length)}
            />
            <StatCard
              label="Centers"
              value={formatInteger(positionCounts.Center)}
              sub={leaguePercent(positionCounts.Center, players.length)}
            />
            <StatCard label="Avg Minutes" value={formatNumber(avgMinutes)} sub="MPG league-wide" />
          </div>

          <div className="players-control-row">
            <label className="players-search-field">
              <span className="sr-only">Search players</span>
              <input
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search players"
                value={search}
              />
            </label>
          </div>

          {isInitialLoading || isStatsLoading ? (
            <div className="rosters-empty">Loading players...</div>
          ) : (
            <div className="player-card-grid">
              {visibleRows.map((row) => (
                <PlayerCard key={row.player.id} row={row} />
              ))}
            </div>
          )}
        </section>

        <aside className="players-sidebar">
          <PlayerSpotlightCard row={spotlightRow} />
          <QuickCompareCard players={players} />
        </aside>

        <TopByCategoryCard topByCategory={topByCategory} />
      </div>
    </AppShell>
  );
}

function StatCard({ label, sub, value }: { label: string; sub?: string; value: string }) {
  return (
    <article className="players-stat-card">
      <strong>{value}</strong>
      <span>{label}</span>
      {sub ? <em>{sub}</em> : null}
    </article>
  );
}

function PlayerCard({ row }: { row: PlayerRow }) {
  const { player, summary } = row;

  return (
    <a className="player-card" href={`/players/${player.nba_player_id}`} style={getThemeStyle(player.team)}>
      <div className="player-card-top">
        <div className="player-card-heading">
          <strong>{player.full_name}</strong>
          <span>
            {player.team?.abbreviation ?? "FA"} / {player.position ?? "Position TBD"}
          </span>
        </div>
        <div className="player-card-visual">
          <PlayerPortrait player={player} size="small" />
        </div>
      </div>
      <div className="player-card-stats">
        <span>
          <strong>{formatNumber(summary?.points_per_game)}</strong>
          PPG
        </span>
        <span>
          <strong>{formatNumber(summary?.assists_per_game)}</strong>
          APG
        </span>
        <span>
          <strong>{formatNumber(summary?.rebounds_per_game)}</strong>
          RPG
        </span>
        <span>
          <strong>{formatPercent(summary?.true_shooting_percentage)}</strong>
          TS%
        </span>
      </div>
    </a>
  );
}

function PlayerSpotlightCard({ row }: { row: RankedRow | undefined }) {
  return (
    <section className="players-sidebar-card spotlight-card" style={getThemeStyle(row?.player.team)}>
      <div className="players-sidebar-heading">
        <h2>Player Spotlight</h2>
      </div>
      {row ? (
        <>
          <div className="spotlight-hero">
            <div className="spotlight-hero-info">
              <strong>{row.player.full_name}</strong>
              <span>
                {row.player.team?.abbreviation ?? "FA"} / {row.player.position ?? "Position TBD"}
              </span>
            </div>
            <div className="player-card-visual">
              <PlayerPortrait player={row.player} size="large" />
            </div>
          </div>
          <p className="spotlight-copy">{buildSpotlightBlurb(row)}</p>
          <div className="spotlight-stat-grid">
            <span>
              <strong>{formatNumber(row.summary.points_per_game)}</strong>
              PPG
            </span>
            <span>
              <strong>{formatNumber(row.summary.assists_per_game)}</strong>
              APG
            </span>
            <span>
              <strong>{formatNumber(row.summary.rebounds_per_game)}</strong>
              RPG
            </span>
            <span>
              <strong>{formatPercent(row.summary.true_shooting_percentage)}</strong>
              TS%
            </span>
          </div>
        </>
      ) : (
        <p className="spotlight-copy">Stored season stats are needed to feature a player here.</p>
      )}
    </section>
  );
}

function QuickCompareCard({ players }: { players: PlayerListItem[] }) {
  const router = useRouter();
  const [firstId, setFirstId] = useState("");
  const [secondId, setSecondId] = useState("");
  const sortedPlayers = useMemo(
    () => [...players].sort((left, right) => left.full_name.localeCompare(right.full_name)),
    [players],
  );
  const canCompare = firstId !== "" && secondId !== "" && firstId !== secondId;

  return (
    <section className="players-sidebar-card quick-compare-card">
      <h2>Quick Compare</h2>
      <div className="quick-compare-row">
        <select
          aria-label="Select first player"
          onChange={(event) => setFirstId(event.target.value)}
          value={firstId}
        >
          <option value="">Select a player</option>
          {sortedPlayers.map((player) => (
            <option key={player.id} value={player.nba_player_id}>
              {player.full_name}
            </option>
          ))}
        </select>
        <span className="quick-compare-swap" aria-hidden="true">
          ⇄
        </span>
        <select
          aria-label="Select second player"
          onChange={(event) => setSecondId(event.target.value)}
          value={secondId}
        >
          <option value="">Select a player</option>
          {sortedPlayers.map((player) => (
            <option key={player.id} value={player.nba_player_id}>
              {player.full_name}
            </option>
          ))}
        </select>
      </div>
      <button
        className="quick-compare-button"
        disabled={!canCompare}
        onClick={() => router.push(`/compare?a=${firstId}&b=${secondId}`)}
        type="button"
      >
        Compare Players
      </button>
      <p className="quick-compare-hint">
        {firstId !== "" && secondId !== "" && firstId === secondId
          ? "Pick two different players to compare."
          : "Select two players to compare their stats side by side."}
      </p>
    </section>
  );
}

function TopByCategoryCard({
  topByCategory,
}: {
  topByCategory: Record<"points" | "assists" | "rebounds" | "efficiency", RankedRow[]>;
}) {
  const categories: Array<{
    key: "points" | "assists" | "rebounds" | "efficiency";
    label: string;
    format: (row: RankedRow) => string;
  }> = [
    { key: "points", label: "Points (PPG)", format: (row) => formatNumber(row.summary.points_per_game) },
    { key: "assists", label: "Assists (APG)", format: (row) => formatNumber(row.summary.assists_per_game) },
    {
      key: "rebounds",
      label: "Rebounds (RPG)",
      format: (row) => formatNumber(row.summary.rebounds_per_game),
    },
    {
      key: "efficiency",
      label: "Efficiency (TS%)",
      format: (row) => formatPercent(row.summary.true_shooting_percentage),
    },
  ];

  return (
    <section className="players-sidebar-card top-category-card top-category-full">
      <div className="players-sidebar-heading">
        <h2>Top by Category</h2>
        <span className="spotlight-link muted">View All</span>
      </div>
      <div className="top-category-grid">
        {categories.map((category) => (
          <div className="top-category-column" key={category.key}>
            <h3>{category.label}</h3>
            <ol>
              {topByCategory[category.key].map((row) => (
                <li key={row.player.id}>
                  <span>{row.player.full_name}</span>
                  <strong>{category.format(row)}</strong>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </section>
  );
}

function topRanked(
  rows: RankedRow[],
  key: "points_per_game" | "assists_per_game" | "rebounds_per_game" | "true_shooting_percentage",
  limit = 5,
  minTotalMinutes = 0,
): RankedRow[] {
  return [...rows]
    .filter((row) => typeof row.summary[key] === "number")
    .filter((row) => {
      if (minTotalMinutes <= 0) {
        return true;
      }
      const totalMinutes = (row.summary.minutes_per_game ?? 0) * row.summary.games_played;
      return totalMinutes >= minTotalMinutes;
    })
    .sort((left, right) => (right.summary[key] as number) - (left.summary[key] as number))
    .slice(0, limit);
}

function classifyPosition(position: string | null | undefined): PositionCategory | null {
  if (!position) {
    return null;
  }
  const normalized = position.toLowerCase();
  const isGuard = normalized.includes("guard");
  const isForward = normalized.includes("forward");
  const isCenter = normalized.includes("center");
  if (isGuard && isForward) {
    return "Wing";
  }
  if (isForward && isCenter) {
    return "Forward";
  }
  if (isGuard) {
    return "Guard";
  }
  if (isForward) {
    return "Forward";
  }
  if (isCenter) {
    return "Center";
  }
  return null;
}

function buildSpotlightBlurb(row: RankedRow): string {
  const { summary } = row;
  const parts: string[] = [`Leads the league at ${formatNumber(summary.points_per_game)} points per game`];
  if (typeof summary.assists_per_game === "number" && summary.assists_per_game >= 5) {
    parts.push(`while also setting up teammates at ${formatNumber(summary.assists_per_game)} assists per game`);
  } else if (typeof summary.rebounds_per_game === "number" && summary.rebounds_per_game >= 7) {
    parts.push(`while cleaning the glass at ${formatNumber(summary.rebounds_per_game)} rebounds per game`);
  }
  const sentence = `${parts.join(" ")}.`;
  if (typeof summary.true_shooting_percentage === "number") {
    return `${sentence} Shooting ${formatPercent(summary.true_shooting_percentage)} true shooting across ${formatInteger(summary.games_played)} games played.`;
  }
  return sentence;
}

function leaguePercent(count: number, total: number): string {
  return total > 0 ? `${((count / total) * 100).toFixed(1)}% of league` : "--";
}

function getTeamName(team: Team): string {
  return `${team.city} ${team.name}`;
}
