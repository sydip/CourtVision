"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { getTeamTheme, getTeamThemeStyle } from "@/components/rosters-dashboard";
import { getDraft } from "@/lib/api/hoopsiq";
import type { DraftPick, DraftResponse } from "@/lib/api/schemas";

type DraftRound = 1 | 2;

export function DraftDashboard() {
  const [activeRound, setActiveRound] = useState<DraftRound>(1);
  const [draft, setDraft] = useState<DraftResponse>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
    getDraft(2026)
      .then((response) => {
        if (active) {
          setDraft(response);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "The 2026 draft board is unavailable.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const picks = useMemo(
    () => draft?.picks.filter((pick) => pick.round === activeRound) ?? [],
    [activeRound, draft],
  );
  const firstPick = draft?.picks[0];

  return (
    <AppShell active="Draft" variant="topbar">
      <div className="draft-page">
        <header className="draft-hero">
          <div className="draft-hero-copy">
            <span className="draft-kicker">Official results</span>
            <h1>2026 NBA Draft</h1>
            <p>
              Every selection, updated to the team that landed the player after draft-night trades.
            </p>
            <div className="draft-event-meta" aria-label="Draft event details">
              <span>
                <strong>Dates</strong>
                {draft?.event_dates ?? "June 23-24, 2026"}
              </span>
              <span>
                <strong>Venue</strong>
                {draft?.venue ?? "Barclays Center"}
              </span>
              <span>
                <strong>Location</strong>
                {draft?.location ?? "Brooklyn, New York"}
              </span>
            </div>
          </div>
          <div className="draft-hero-mark" aria-hidden="true">
            <span>26</span>
            <i />
          </div>
          {firstPick ? (
            <div className="draft-first-call">
              <span>No. 1 selection</span>
              <strong>{firstPick.player_name}</strong>
              <em>{teamName(firstPick)}</em>
            </div>
          ) : null}
        </header>

        <section className="draft-board" aria-labelledby="draft-board-title">
          <div className="draft-board-heading">
            <div>
              <span className="draft-kicker">Complete board</span>
              <h2 id="draft-board-title">Round {activeRound}</h2>
            </div>
            <div className="draft-round-tabs" role="tablist" aria-label="Draft round">
              {[1, 2].map((round) => (
                <button
                  aria-controls={`draft-round-${round}`}
                  aria-selected={activeRound === round}
                  className={activeRound === round ? "active" : ""}
                  key={round}
                  onClick={() => setActiveRound(round as DraftRound)}
                  role="tab"
                  type="button"
                >
                  <span>Round {round}</span>
                  <em>Picks {round === 1 ? "1-30" : "31-60"}</em>
                </button>
              ))}
            </div>
          </div>

          {error ? (
            <div className="draft-state error" role="alert">
              <strong>Draft board unavailable</strong>
              <p>{error}</p>
            </div>
          ) : !draft ? (
            <DraftSkeleton />
          ) : picks.length === 0 ? (
            <div className="draft-state">
              <strong>No selections stored</strong>
              <p>There are no picks available for this round.</p>
            </div>
          ) : (
            <div className="draft-table-wrap" id={`draft-round-${activeRound}`} role="tabpanel">
              <div className="draft-table-header" aria-hidden="true">
                <span>Pick</span>
                <span>Player</span>
                <span>School / Country</span>
                <span>Final team</span>
                <span>Draft-night path</span>
              </div>
              <ol className="draft-pick-list" start={activeRound === 1 ? 1 : 31}>
                {picks.map((pick) => (
                  <DraftPickRow key={pick.id} pick={pick} />
                ))}
              </ol>
            </div>
          )}
        </section>

        <footer className="draft-note">
          Team reflects the final destination after draft-night transactions. Round 2 selections may
          have passed through multiple teams.
        </footer>
      </div>
    </AppShell>
  );
}

function DraftPickRow({ pick }: { pick: DraftPick }) {
  const style = getTeamThemeStyle(getTeamTheme(pick.team)) as CSSProperties;
  return (
    <li className="draft-pick-row" style={style}>
      <span className="draft-pick-number">{pick.overall_pick}</span>
      <span className="draft-player">
        <strong>{pick.player_name}</strong>
        <em>Round {pick.round}</em>
      </span>
      <span className="draft-school">{pick.school_country}</span>
      <a
        className="draft-team"
        href={`/rosters?team=${pick.team.nba_team_id}`}
        aria-label={`Open ${teamName(pick)} roster`}
      >
        <i aria-hidden="true">{pick.team.abbreviation}</i>
        <span>
          <strong>{teamName(pick)}</strong>
          <em>{pick.team.conference} Conference</em>
        </span>
      </a>
      <span className={pick.transaction_note ? "draft-trade-note" : "draft-trade-note direct"}>
        {pick.transaction_note ?? "Original selection"}
      </span>
    </li>
  );
}

function DraftSkeleton() {
  return (
    <div className="draft-skeleton" aria-label="Loading draft selections">
      {Array.from({ length: 8 }, (_, index) => (
        <span key={index} />
      ))}
    </div>
  );
}

function teamName(pick: DraftPick): string {
  return `${pick.team.city} ${pick.team.name}`;
}
