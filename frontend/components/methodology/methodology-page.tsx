const seasons = ["2021–22", "2022–23", "2023–24", "2024–25", "2025–26"];

const methods = [
  {
    number: "01",
    title: "Historical statistics",
    copy: "CourtVision groups stored game logs by player and season, orders games by date, and calculates totals, per-game and per-36 production, rolling 5- and 10-game windows, home/away splits, rest splits, true shooting, effective field goal percentage, and season-specific percentiles. Missing inputs remain missing instead of being estimated.",
  },
  {
    number: "02",
    title: "Standings",
    copy: "Historical standings come from stored season snapshots and team summaries. Records, conference ranks, division ranks, and point differentials are always filtered by season. A current, final, or projected snapshot is identified explicitly; projected standings are never presented as historical results.",
  },
  {
    number: "03",
    title: "Rosters",
    copy: "Roster memberships connect global player and team identities to a season, status, dates, jersey number, position, and depth information. Multiple team memberships are allowed in one season so trades and other roster changes are not collapsed into a single team.",
  },
  {
    number: "04",
    title: "Player comparison",
    copy: "Both players are compared inside the same selected season. CourtVision uses stored season summaries and season-scoped benchmarks, so a comparison never combines one player's historical season with another player's current-season values.",
  },
  {
    number: "05",
    title: "Similar players",
    copy: "Similarity uses deterministic, season-specific feature vectors built from production, efficiency, role, and playing-time measures. Candidates are restricted to the selected season and ranked by distance between comparable normalized features. Results describe statistical similarity, not player quality or future potential.",
  },
];

export function MethodologyPage() {
  return (
    <main className="methodology-page">
      <header className="methodology-hero">
        <div>
          <span>CourtVision reference</span>
          <h1>Data &amp; Methodology</h1>
          <p>
            How multi-season records, deterministic analytics, grounded assistant answers, and
            experimental 2026–27 estimates are produced.
          </p>
        </div>
        <aside>
          <strong>Database first</strong>
          <p>
            Normal page requests read PostgreSQL. External NBA data is fetched only by explicit
            batch ingestion jobs.
          </p>
        </aside>
      </header>

      <section className="methodology-section" aria-labelledby="data-sources">
        <SectionHeading
          eyebrow="Data foundation"
          id="data-sources"
          title="Sources, seasons, and selection"
        />
        <div className="methodology-source-grid">
          <article>
            <h3>NBA data ingestion</h3>
            <p>
              Batch jobs retrieve available NBA records through the configured <code>nba_api</code>{" "}
              provider. Raw responses are timestamped and cached before validation, normalization,
              and idempotent PostgreSQL upserts. CourtVision does not call NBA.com during ordinary
              page loads.
            </p>
          </article>
          <article>
            <h3>Season selector</h3>
            <p>
              The global selector writes a canonical <code>YYYY-YY</code> season to the URL and
              local storage. API requests and client cache keys include that season, keeping lists,
              profiles, standings, rosters, comparisons, and assistant questions isolated.
            </p>
          </article>
        </div>
        <div className="methodology-season-row">
          {seasons.map((season) => (
            <span key={season}>
              {season}
              <small>Historical analytics</small>
            </span>
          ))}
          <span className="prediction">
            <b>2026–27</b>
            <small>Prediction season only</small>
          </span>
        </div>
      </section>

      <section className="methodology-section" aria-labelledby="analytics">
        <SectionHeading
          eyebrow="Deterministic analytics"
          id="analytics"
          title="Historical calculations"
        />
        <div className="methodology-method-grid">
          {methods.map((method) => (
            <article key={method.number}>
              <span>{method.number}</span>
              <h3>{method.title}</h3>
              <p>{method.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        className="methodology-section methodology-assistant"
        aria-labelledby="assistant-method"
      >
        <SectionHeading
          eyebrow="Grounded retrieval"
          id="assistant-method"
          title="AI Assistant data access"
        />
        <div className="methodology-split">
          <div>
            <p>
              The assistant parses a question into a supported retrieval intent, resolves player and
              team names, abbreviations, seasons, dates, opponents, and stat names, and then calls
              predefined repository tools. It does not execute arbitrary model-generated SQL.
            </p>
            <p>
              Exact game questions can be answered when the matching game and player-game record
              exist. Answers include database evidence when possible. When a record is absent or an
              entity is ambiguous, the assistant returns a missing-data or clarification response
              instead of inventing a statistic.
            </p>
          </div>
          <ul>
            <li>PostgreSQL records are the factual authority.</li>
            <li>The selected frontend season is sent with every question.</li>
            <li>Player, team, date, opponent, and season filters are explicit.</li>
            <li>Missing facts remain visibly unavailable.</li>
          </ul>
        </div>
      </section>

      <section
        className="methodology-section methodology-predictions"
        aria-labelledby="prediction-method"
      >
        <SectionHeading
          eyebrow="Experimental estimates"
          id="prediction-method"
          title="2026–27 prediction methodology"
        />
        <div className="methodology-prediction-grid">
          <article>
            <h3>Model design</h3>
            <p>
              All-NBA, standings, and Finals estimates use logistic-regression-style classifiers
              trained on stored 2021–22 through 2025–26 records. Features include season production
              and efficiency, team results, prior honors, returning production, roster continuity,
              ratings, and other available team-strength signals. Training checks reject 2026–27
              feature leakage.
            </p>
          </article>
          <article>
            <h3>Probability, not certainty</h3>
            <p>
              Outputs are experimental model probabilities and rankings—not official selections,
              standings, or outcomes. They are exposed only for 2026–27. Historical seasons can be
              analyzed but cannot be predicted by this model family.
            </p>
          </article>
          <article className="warning">
            <h3>Important limitations</h3>
            <p>
              Five training seasons form a small dataset, especially for a single annual champion.
              Missing features, projected rosters, trades, role changes, and injuries can materially
              alter results. Finals winner estimates are especially uncertain. CourtVision
              predictions are not betting advice.
            </p>
          </article>
        </div>
      </section>

      <footer className="methodology-legal">
        <strong>Data and media notice</strong>
        <p>
          CourtVision is an independent analytics project and is not affiliated with or endorsed by
          the NBA or its teams. NBA names, team names, statistics, and related marks belong to their
          respective owners. Public distributions should use original, licensed, or
          permission-cleared imagery and should not bundle NBA logos, player photographs, broadcast
          footage, or other copyrighted media without authorization.
        </p>
      </footer>
    </main>
  );
}

function SectionHeading({ eyebrow, id, title }: { eyebrow: string; id: string; title: string }) {
  return (
    <header className="methodology-heading">
      <span>{eyebrow}</span>
      <h2 id={id}>{title}</h2>
    </header>
  );
}
