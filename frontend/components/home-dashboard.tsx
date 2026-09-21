"use client";

import { useMemo } from "react";

import { AppShell } from "@/components/app-shell";
import { PlayerNumberMark } from "@/components/player-number-mark";
import { useDataStatus } from "@/lib/api/hooks";
import type { DataStatus, PlayerListItem, Team } from "@/lib/api/schemas";
import { formatTimeStamp, pluralize } from "@/lib/format";
import { useSeason } from "@/lib/state/season-context";

/* The six database entry points. Every card resolves to a section that
   actually exists in this app - no placeholder destinations. */
const databaseCards = [
  {
    title: "Players",
    description: "Search and explore player profiles and information.",
    href: "/players",
    glyph: "player",
  },
  {
    title: "Teams",
    description: "Browse teams, rosters, and organization history.",
    href: "/rosters",
    glyph: "team",
  },
  {
    title: "Standings",
    description: "Conference tables, records, streaks, and splits.",
    href: "/standings",
    glyph: "table",
  },
  {
    title: "Playoffs",
    description: "View playoff brackets, series, and history.",
    href: "/playoffs",
    glyph: "trophy",
  },
  {
    title: "Draft",
    description: "Explore draft classes, picks, and prospects.",
    href: "/draft",
    glyph: "draft",
  },
  {
    title: "Compare",
    description: "Measure any two players across advanced stats.",
    href: "/compare",
    glyph: "compare",
  },
] as const;

const categoryCards = [
  {
    title: "Regular Season",
    description: "Explore all regular season records and results.",
    href: "/standings",
    tone: "court",
  },
  {
    title: "Playoff History",
    description: "Relive past playoff runs and championships.",
    href: "/playoffs",
    tone: "banner",
  },
  {
    title: "NBA Draft",
    description: "Browse draft history and future prospects.",
    href: "/draft",
    tone: "draft",
  },
  {
    title: "Team History",
    description: "Discover team records, trades, and timelines.",
    href: "/rosters",
    tone: "legacy",
  },
] as const;

type HomeDashboardViewProps = {
  dataStatus: DataStatus | undefined;
  isDataStatusLoading: boolean;
  hasDataStatusError: boolean;
};

export function HomeDashboard() {
  const { season } = useSeason();
  const dataStatusQuery = useDataStatus(season);

  return (
    <HomeDashboardView
      dataStatus={dataStatusQuery.data}
      hasDataStatusError={dataStatusQuery.isError}
      isDataStatusLoading={dataStatusQuery.isLoading}
    />
  );
}

export function HomeDashboardView({
  dataStatus,
  isDataStatusLoading,
  hasDataStatusError,
}: HomeDashboardViewProps) {
  const freshness = useMemo(
    () => formatTimeStamp(dataStatus?.last_successful_sync?.finished_at),
    [dataStatus?.last_successful_sync?.finished_at],
  );
  const playerCount = dataStatus ? pluralize(dataStatus.player_count, "stored player") : null;
  const syncText = isDataStatusLoading
    ? "Checking latest sync"
    : hasDataStatusError
      ? "Data status unavailable"
      : `Updated ${freshness}`;
  const seasonLabel = dataStatus?.season ?? dataStatus?.current_season ?? "2025-26";

  return (
    <AppShell active="Home" variant="topbar">
      <div className="home-landing">
        <section className="home-hero" aria-label="Welcome">
          <div className="home-hero-art" aria-hidden="true">
            <CourtGraphic />
            <span className="home-hero-mark">
              <BasketballIcon />
            </span>
          </div>

          <div className="home-hero-body">
            <span className="home-hero-eyebrow">{seasonLabel} Season</span>
            <h1>
              Explore. Analyze. <span>Elevate.</span>
            </h1>
            <p>Your all-in-one NBA database for in-depth research and analysis.</p>
            <a className="home-hero-cta" href="/players">
              Explore Players
              <i aria-hidden="true">&gt;</i>
            </a>

            <dl className="home-hero-stats">
              <HeroStat label="Season" value={seasonLabel} />
              <HeroStat label="Players" value={playerCount ?? "—"} />
              <HeroStat label="Sync" value={syncText} tone={hasDataStatusError ? "warn" : "ok"} />
            </dl>
          </div>
        </section>

        <section className="home-section" aria-labelledby="home-explore-heading">
          <h2 className="home-section-heading" id="home-explore-heading">
            Explore the Database
          </h2>
          <div className="home-database-grid">
            {databaseCards.map((card) => (
              <a className="home-database-card" href={card.href} key={card.title}>
                <span className="home-database-art" aria-hidden="true">
                  <span className={`home-database-glyph ${card.glyph}`}>
                    <i />
                  </span>
                </span>
                <strong>{card.title}</strong>
                <em>{card.description}</em>
              </a>
            ))}
          </div>
        </section>

        <section className="home-section" aria-labelledby="home-category-heading">
          <h2 className="home-section-heading" id="home-category-heading">
            Browse by Category
          </h2>
          <div className="home-category-grid">
            {categoryCards.map((card) => (
              <a className={`home-category-card ${card.tone}`} href={card.href} key={card.title}>
                <span className="home-category-art" aria-hidden="true" />
                <span className="home-category-body">
                  <span>
                    <strong>{card.title}</strong>
                    <em>{card.description}</em>
                  </span>
                  <i className="home-category-arrow" aria-hidden="true">
                    &rarr;
                  </i>
                </span>
              </a>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function HeroStat({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" }) {
  return (
    <div className={`home-hero-stat${tone ? ` ${tone}` : ""}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function PlayerPortrait({
  player,
  size = "large",
}: {
  player: Pick<PlayerListItem, "full_name" | "jersey_number"> & { team?: Team | null };
  size?: "large" | "small" | "tiny";
}) {
  return (
    <div className={`player-portrait ${size}`}>
      <PlayerNumberMark player={player} />
    </div>
  );
}

/* Half-court line work behind the hero. Drawn rather than photographed so the
   page ships no external image assets and stays on the app palette. */
function CourtGraphic() {
  return (
    <svg
      aria-hidden="true"
      className="home-court-graphic"
      preserveAspectRatio="xMidYMid slice"
      viewBox="0 0 400 220"
    >
      <g fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.55">
        <rect x="8" y="8" width="384" height="204" rx="2" />
        <line x1="200" y1="8" x2="200" y2="212" />
        <circle cx="200" cy="110" r="34" />
        <rect x="8" y="62" width="70" height="96" />
        <rect x="322" y="62" width="70" height="96" />
        <path d="M78 62 A54 54 0 0 1 78 158" />
        <path d="M322 62 A54 54 0 0 0 322 158" />
      </g>
    </svg>
  );
}

function BasketballIcon() {
  return (
    <svg aria-hidden="true" className="basketball-icon" viewBox="0 0 100 100">
      <circle
        cx="50"
        cy="50"
        r="46"
        fill="url(#basketballGradient)"
        stroke="#3a1c05"
        strokeWidth="2.5"
      />
      <path
        d="M50 4 V96 M4 50 H96 M15 15 Q50 50 15 85 M85 15 Q50 50 85 85"
        fill="none"
        stroke="#3a1c05"
        strokeWidth="2.5"
      />
      <defs>
        <linearGradient id="basketballGradient" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stopColor="#ff9a4d" />
          <stop offset="100%" stopColor="#e2601c" />
        </linearGradient>
      </defs>
    </svg>
  );
}
