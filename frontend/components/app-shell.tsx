"use client";

import type React from "react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { PlayerNumberMark } from "@/components/player-number-mark";
import { getPlayers, getTeams } from "@/lib/api/hoopsiq";
import type { PlayerListItem, Team } from "@/lib/api/schemas";

type AppSection =
  | "Home"
  | "Players"
  | "Teams"
  | "Compare"
  | "Playoffs"
  | "Draft"
  | "Offseason"
  | "Standings"
  | "Trend Analysis"
  | "Reports"
  | "Jordan";

type AppShellProps = {
  active: AppSection;
  children: React.ReactNode;
  showTopSearch?: boolean;
  themeStyle?: React.CSSProperties;
  variant?: "default" | "home" | "topbar";
};

const primaryLinks = [
  { label: "Home", href: "/" },
  { label: "Players", href: "/players" },
  { label: "Teams", href: "/rosters" },
  { label: "Standings", href: "/standings" },
  { label: "Compare", href: "/compare" },
  { label: "Playoffs", href: "/playoffs" },
  { label: "Draft", href: "/draft" },
  { label: "Offseason", href: "/offseason" },
  { label: "Jordan", href: "/assistant" },
] satisfies Array<{ label: AppSection; href: string }>;

const secondaryLinks = [
  { label: "Data Dictionary", href: "/" },
  { label: "Glossary", href: "/" },
];

const defaultTopLinks = primaryLinks;
const homeTopLinks = defaultTopLinks;
const topSearchLimit = 6;

export function AppShell({
  active,
  children,
  showTopSearch = true,
  themeStyle,
  variant = "default",
}: AppShellProps) {
  const isHomeVariant = variant === "home";
  const isTopbarVariant = variant === "topbar";
  const hidesSidebar = isHomeVariant || isTopbarVariant;
  const sectionLinks = isHomeVariant ? homeTopLinks : defaultTopLinks;

  return (
    <main
      className={[
        "dashboard-shell",
        isHomeVariant ? "home-shell" : "",
        isTopbarVariant ? "topbar-shell" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={themeStyle}
    >
      {!hidesSidebar ? (
        <aside className="sidebar">
          <a className="brand" href="/" aria-label="CourtVision home">
            <span className="brand-mark" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <span>CourtVision</span>
          </a>

          <nav className="side-nav" aria-label="Primary navigation">
            {primaryLinks.map((item) => (
              <a
                className={item.label === active ? "side-link active" : "side-link"}
                href={item.href}
                key={item.label}
              >
                <span className="nav-glyph" aria-hidden="true" />
                <span>{item.label}</span>
              </a>
            ))}
          </nav>

          <nav className="side-nav secondary" aria-label="Reference navigation">
            {secondaryLinks.map((item) => (
              <a className="side-link" href={item.href} key={item.label}>
                <span className="nav-glyph round" aria-hidden="true" />
                <span>{item.label}</span>
              </a>
            ))}
          </nav>

          <div className="sidebar-footer">
            <a className="side-link" href="/">
              <span className="nav-glyph round" aria-hidden="true" />
              <span>Feedback</span>
            </a>
            <a className="side-link" href="/">
              <span className="nav-glyph diamond" aria-hidden="true" />
              <span>Settings</span>
            </a>
          </div>
        </aside>
      ) : null}

      <section className="workspace">
        <header
          className={[
            "topbar",
            showTopSearch ? "" : "no-search",
            isHomeVariant ? "home-topbar" : "",
            isTopbarVariant ? "profile-topbar" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <a className="topbar-brand" href="/" aria-label="CourtVision home">
            <span className="brand-mark small" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <strong>
              Court<span className="brand-accent">Vision</span>
            </strong>
          </a>
          <nav className="top-nav" aria-label="Section navigation">
            {sectionLinks.map((item) => {
              const isJordan = item.label === "Jordan";
              return (
                <a
                  className={[
                    item.label === active ? "top-link active" : "top-link",
                    isJordan ? "top-link-jordan" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  href={item.href}
                  key={item.label}
                >
                  {isJordan ? (
                    <span className="jordan-spark" aria-hidden="true">
                      ✦
                    </span>
                  ) : null}
                  {item.label}
                </a>
              );
            })}
          </nav>
          {showTopSearch ? <TopPlayerSearch /> : null}
        </header>

        {children}
      </section>
    </main>
  );
}

const topSearchTeamLimit = 4;

function TopPlayerSearch() {
  const [search, setSearch] = useState("");
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const deferredSearch = useDeferredValue(search);
  const normalizedSearch = deferredSearch.trim();
  const isSearching = isLoading || search.trim() !== normalizedSearch;

  useEffect(() => {
    let isActive = true;
    getTeams()
      .then((response) => {
        if (isActive) {
          setTeams(response.teams);
        }
      })
      .catch(() => {
        // Team results are a nice-to-have; player search still works without them.
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (!normalizedSearch) {
      setPlayers([]);
      setHasError(false);
      setIsLoading(false);
      return;
    }

    let isActive = true;
    setIsLoading(true);
    setHasError(false);

    getPlayers({ q: normalizedSearch, limit: topSearchLimit })
      .then((response) => {
        if (isActive) {
          setPlayers(response.items);
        }
      })
      .catch(() => {
        if (isActive) {
          setPlayers([]);
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
  }, [normalizedSearch]);

  const filteredTeams = useMemo(() => {
    if (!normalizedSearch) {
      return [];
    }
    const query = normalizedSearch.toLowerCase();
    return teams
      .filter(
        (team) =>
          team.city.toLowerCase().includes(query) ||
          team.name.toLowerCase().includes(query) ||
          team.abbreviation.toLowerCase().includes(query) ||
          `${team.city} ${team.name}`.toLowerCase().includes(query),
      )
      .slice(0, topSearchTeamLimit);
  }, [normalizedSearch, teams]);

  const firstTeam = filteredTeams[0];
  const firstPlayer = players[0];

  const statusText = useMemo(() => {
    if (!search.trim()) {
      return "";
    }
    if (isSearching) {
      return "Searching players and teams";
    }
    if (hasError && filteredTeams.length === 0) {
      return "Player search unavailable";
    }
    const total = players.length + filteredTeams.length;
    if (total === 0) {
      return "No matching players or teams";
    }
    return `${total} matching results`;
  }, [filteredTeams.length, hasError, isSearching, players.length, search]);

  function openPlayer(player: PlayerListItem | undefined) {
    if (!player) {
      return;
    }
    window.location.href = `/players/${player.nba_player_id}`;
  }

  function openTeam(team: Team | undefined) {
    if (!team) {
      return;
    }
    window.location.href = `/rosters?team=${team.nba_team_id}`;
  }

  return (
    <form
      className="top-player-search"
      onSubmit={(event) => {
        event.preventDefault();
        if (firstTeam) {
          openTeam(firstTeam);
        } else {
          openPlayer(firstPlayer);
        }
      }}
      role="search"
    >
      <label className="top-search-control">
        <span className="top-search-icon" aria-hidden="true" />
        <input
          aria-label="Global player and team lookup"
          autoComplete="off"
          onBlur={() => {
            window.setTimeout(() => setIsOpen(false), 130);
          }}
          onChange={(event) => {
            setSearch(event.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Search players or teams"
          value={search}
        />
      </label>

      {isOpen && search.trim() ? (
        <div
          className="top-search-results"
          role="listbox"
          aria-label="Player and team search results"
        >
          {isSearching ? (
            <span className="top-search-message">Searching players and teams</span>
          ) : filteredTeams.length === 0 && players.length === 0 ? (
            hasError ? (
              <span className="top-search-message warning">Player search unavailable</span>
            ) : (
              <span className="top-search-message">No matching players or teams</span>
            )
          ) : (
            <>
              {filteredTeams.map((team) => (
                <a
                  aria-selected="false"
                  className="top-search-result"
                  href={`/rosters?team=${team.nba_team_id}`}
                  key={`team-${team.id}`}
                  role="option"
                >
                  <TopSearchTeamLogo team={team} />
                  <span>
                    <strong>
                      {team.city} {team.name}
                    </strong>
                  </span>
                </a>
              ))}
              {players.map((player) => (
                <a
                  aria-selected="false"
                  className="top-search-result"
                  href={`/players/${player.nba_player_id}`}
                  key={player.id}
                  role="option"
                >
                  <TopSearchPortrait player={player} />
                  <span>
                    <strong>{player.full_name}</strong>
                    <em>
                      {player.team?.abbreviation ?? "FA"} / {player.position ?? "Position TBD"}
                    </em>
                  </span>
                </a>
              ))}
            </>
          )}
        </div>
      ) : null}

      <span className="sr-only" aria-live="polite">
        {statusText}
      </span>
    </form>
  );
}

function TopSearchPortrait({ player }: { player: PlayerListItem }) {
  return (
    <span className="top-search-portrait" aria-hidden="true">
      <PlayerNumberMark player={player} />
    </span>
  );
}

function TopSearchTeamLogo({ team }: { team: Team }) {
  return (
    <span className="top-search-portrait top-search-team-logo" aria-hidden="true">
      {team.abbreviation}
    </span>
  );
}
