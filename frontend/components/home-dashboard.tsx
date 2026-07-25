"use client";

import { useMemo } from "react";

import { AppShell } from "@/components/app-shell";
import { PlayerNumberMark } from "@/components/player-number-mark";
import { useDataStatus } from "@/lib/api/hooks";
import type { DataStatus, PlayerListItem, Team } from "@/lib/api/schemas";
import { formatTimeStamp, pluralize } from "@/lib/format";

const primaryCards = [
  {
    title: "Standings",
    description: "View the latest NBA standings, including conference rankings and team records.",
    action: "View Standings",
    href: "/",
    tone: "blue",
  },
  {
    title: "Compare Players",
    description:
      "Compare any two players side by side across advanced stats, trends, and performance.",
    action: "Compare Players",
    href: "/",
    tone: "purple",
  },
  {
    title: "Rosters",
    description: "Browse current NBA rosters for all teams and explore player details.",
    action: "View Rosters",
    href: "/rosters",
    tone: "green",
  },
] as const;

type HomeDashboardViewProps = {
  dataStatus: DataStatus | undefined;
  isDataStatusLoading: boolean;
  hasDataStatusError: boolean;
};

export function HomeDashboard() {
  const dataStatusQuery = useDataStatus();

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
  const reliabilityText = playerCount
    ? `Regular data updates for ${playerCount}.`
    : "Regular data updates for accurate insights.";

  return (
    <AppShell active="Home" variant="home">
      <div className="home-landing">
        <section className="home-welcome-hero">
          <div className="nba-logo-frame">
            <BasketballIcon />
          </div>

          <div className="home-welcome-copy">
            <h1>
              Welcome to <span>CourtVision</span>
            </h1>
            <strong>Your all-in-one NBA analytics platform.</strong>
            <p>
              Explore in-depth player insights, compare performance, track standings, and browse
              rosters - all powered by data.
            </p>
          </div>
        </section>

        <section className="home-primary-card-grid" aria-label="Primary dashboard actions">
          {primaryCards.map((card) => (
            <HomePrimaryCard
              action={card.action}
              description={card.description}
              href={card.href}
              key={card.title}
              title={card.title}
              tone={card.tone}
            />
          ))}
        </section>

        <section className="home-insight-strip" aria-label="Platform highlights">
          <InsightItem
            description="Advanced metrics and meaningful analytics."
            title="Data-Driven Insights"
            tone="blue"
          />
          <InsightItem description={reliabilityText} title="Reliable & Updated" tone="shield" />
          <InsightItem
            description="Track recent form and long-term player performance."
            title="Performance Trends"
            tone="trend"
          />
          <InsightItem
            description={syncText}
            title="Built for Fans"
            tone={hasDataStatusError ? "warning" : "star"}
          />
        </section>
      </div>
    </AppShell>
  );
}

function HomePrimaryCard({
  action,
  description,
  href,
  title,
  tone,
}: {
  action: string;
  description: string;
  href: string;
  title: string;
  tone: "blue" | "green" | "purple";
}) {
  return (
    <a className={`home-primary-card ${tone}`} href={href}>
      <span className={`home-primary-icon ${tone}`} aria-hidden="true">
        <i />
      </span>
      <span className="home-primary-copy">
        <strong>{title}</strong>
        <em>{description}</em>
      </span>
      <span className="home-primary-button">
        {action}
        <i aria-hidden="true">&gt;</i>
      </span>
    </a>
  );
}

function InsightItem({
  description,
  title,
  tone,
}: {
  description: string;
  title: string;
  tone: "blue" | "shield" | "star" | "trend" | "warning";
}) {
  return (
    <article className="home-insight-item">
      <span className={`home-insight-icon ${tone}`} aria-hidden="true">
        <i />
      </span>
      <span>
        <strong>{title}</strong>
        <em>{description}</em>
      </span>
    </article>
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
