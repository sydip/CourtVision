"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { getDataStatus, queryAssistant } from "@/lib/api/courtvision";
import type { AssistantEvidence, AssistantQueryResponse, DataStatus } from "@/lib/api/schemas";
import { PredictionDashboard } from "@/components/predictions/prediction-dashboard";
import { formatTimeStamp } from "@/lib/format";
import { useSeason } from "@/lib/state/season-context";

type Exchange = { id: number; question: string; response?: AssistantQueryResponse; error?: string };

const predictionPrompts = [
  "Predict the 2026-27 All-NBA teams.",
  "Which teams are projected to finish top 5 in the West?",
  "Who is the model's predicted NBA Finals winner?",
  "Why is this player projected for All-NBA?",
  "What factors are driving the standings projection?",
];

const historicalPrompts = (season: string) => [
  `Who led the league in points in ${season}?`,
  `Show the ${season} Eastern Conference standings.`,
  `Compare Luka Doncic and Nikola Jokic in ${season}.`,
  `What were Devin Booker's stats in a specific ${season} game?`,
];

export function DataAssistant() {
  const { season, seasons } = useSeason();
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<Exchange[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<DataStatus>();
  const sequence = useRef(0);

  useEffect(() => {
    void getDataStatus(season)
      .then(setStatus)
      .catch(() => setStatus(undefined));
  }, [season]);

  async function submit(rawQuestion: string) {
    const question = rawQuestion.trim();
    if (!question || isLoading) return;
    sequence.current += 1;
    const id = sequence.current;
    setHistory((items) => [...items, { id, question }]);
    setInput("");
    setIsLoading(true);
    try {
      const querySeason =
        season === "2025-26" && isPredictionQuestion(question) ? "2026-27" : season;
      const response = await queryAssistant(question, querySeason);
      setHistory((items) => items.map((item) => (item.id === id ? { ...item, response } : item)));
    } catch (error) {
      const message = error instanceof Error ? error.message : "The assistant request failed.";
      setHistory((items) =>
        items.map((item) => (item.id === id ? { ...item, error: message } : item)),
      );
    } finally {
      setIsLoading(false);
    }
  }

  const predictionMode = season === "2025-26";
  const suggestedPrompts = predictionMode ? predictionPrompts : historicalPrompts(season);
  return (
    <div className="data-assistant-page">
      <header className="data-assistant-header">
        <div>
          <span className="assistant-eyebrow">Grounded database retrieval</span>
          <h1>CourtVision AI Assistant</h1>
          <p>Ask questions across players, teams, rosters, standings, and historical seasons.</p>
        </div>
        <div className="assistant-forecast-context" aria-label="Jordan forecast context">
          <span>Selected tab</span>
          <strong>{season}</strong>
          <em>{predictionMode ? "Forecast target: 2026–27" : "Historical analysis"}</em>
        </div>
      </header>

      {predictionMode ? <PredictionDashboard /> : <HistoricalMode season={season} />}

      <div className="data-assistant-grid">
        <main className="data-assistant-query-card">
          <section className="data-assistant-suggestions" aria-label="Suggested prompts">
            <span>Try asking</span>
            <div>
              {suggestedPrompts.map((prompt) => (
                <button key={prompt} onClick={() => setInput(prompt)} type="button">
                  {prompt}
                </button>
              ))}
            </div>
          </section>

          <div className="data-assistant-history" aria-live="polite">
            {history.length === 0 ? <EmptyWelcome season={season} /> : null}
            {history.map((exchange) => (
              <article className="data-assistant-exchange" key={exchange.id}>
                <p className="data-assistant-question">
                  <strong>You</strong>
                  {exchange.question}
                </p>
                {exchange.response ? (
                  <Answer
                    response={exchange.response}
                    originalQuestion={exchange.question}
                    onClarify={submit}
                  />
                ) : null}
                {exchange.error ? (
                  <p className="data-assistant-error" role="alert">
                    {exchange.error}
                  </p>
                ) : null}
              </article>
            ))}
            {isLoading ? (
              <div className="data-assistant-loading" role="status">
                <i />
                <i />
                <i />
                <span>Searching CourtVision records…</span>
              </div>
            ) : null}
          </div>

          <form
            className="data-assistant-composer"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              void submit(input);
            }}
          >
            <textarea
              aria-label="Ask CourtVision"
              placeholder={
                predictionMode
                  ? "Ask about 2025–26 data or next-season model estimates…"
                  : `Ask a factual question about ${season}…`
              }
              rows={3}
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
            <button disabled={isLoading || !input.trim()} type="submit">
              Ask CourtVision
            </button>
          </form>
        </main>

        <aside className="data-assistant-availability" aria-label="Data availability">
          <div className="data-assistant-panel-title">
            <span>Database</span>
            <strong>Data availability</strong>
          </div>
          <AvailabilityMetric label="Season" value={season} />
          <AvailabilityMetric
            label="Players"
            value={status?.players ?? status?.player_count ?? "—"}
          />
          <AvailabilityMetric label="Teams" value={status?.teams ?? "—"} />
          <AvailabilityMetric label="Games" value={status?.games ?? status?.game_count ?? "—"} />
          <AvailabilityMetric
            label="Last sync"
            value={formatTimeStamp(status?.last_successful_sync?.finished_at)}
          />
          <div className="data-assistant-season-list">
            <span>Available seasons</span>
            {seasons.map((value) => (
              <em className={value === season ? "active" : ""} key={value}>
                {value}
              </em>
            ))}
          </div>
          <p>
            <i /> Answers are produced from stored database records. Missing records remain visible
            as empty states.
          </p>
        </aside>
      </div>
    </div>
  );
}

function EmptyWelcome({ season }: { season: string }) {
  return (
    <div className="data-assistant-empty">
      <span aria-hidden="true">CV</span>
      <strong>Ask CourtVision</strong>
      <p>
        {season === "2025-26"
          ? "Explore 2025–26 records and CourtVision's model estimates for the following season."
          : `Search exact games, season summaries, standings, rosters, and comparisons for ${season}.`}
      </p>
    </div>
  );
}

function HistoricalMode({ season }: { season: string }) {
  return (
    <section className="historical-mode" aria-label="Historical analysis mode">
      <div>
        <span>Historical analysis mode</span>
        <strong>{season} database records</strong>
      </div>
      <p>Jordan forecasts are available from the 2025–26 tab.</p>
    </section>
  );
}

function isPredictionQuestion(question: string) {
  const normalized = question.toLowerCase();
  return [
    "predict",
    "projected",
    "projection",
    "model estimate",
    "model's predicted",
    "model predict",
    "finals winner",
    "who will win",
    "model favorite",
    "likely to win",
    "all-nba model",
    "standings projection",
  ].some((phrase) => normalized.includes(phrase));
}

function Answer({
  response,
  originalQuestion,
  onClarify,
}: {
  response: AssistantQueryResponse;
  originalQuestion: string;
  onClarify: (question: string) => Promise<void>;
}) {
  const choices = response.requiresClarification ? clarificationChoices(response.answer) : [];
  return (
    <div className="data-assistant-answer">
      <div className="data-assistant-answer-copy">
        <span>CV</span>
        <p>{response.answer}</p>
      </div>
      {choices.length ? (
        <div className="data-assistant-clarifications">
          <span>Select a player</span>
          {choices.map((choice) => (
            <button
              key={choice}
              onClick={() =>
                void onClarify(
                  originalQuestion.replace(/\b[A-Z][a-z]+\b(?=\s+(?:average|stats))/i, choice),
                )
              }
              type="button"
            >
              {choice}
            </button>
          ))}
        </div>
      ) : null}
      <EvidencePanel
        evidence={response.evidence}
        intent={response.intent}
        season={response.season}
      />
    </div>
  );
}

function EvidencePanel({
  evidence,
  intent,
  season,
}: {
  evidence: AssistantEvidence[];
  intent: string;
  season: string;
}) {
  if (!evidence.length)
    return (
      <div className="data-assistant-no-evidence">
        <strong>No database records found</strong>
        <span>The assistant did not fabricate an answer.</span>
      </div>
    );
  if (intent === "standings_lookup")
    return (
      <section className="data-assistant-evidence">
        <EvidenceHeader season={season} />
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Team</th>
              <th>Record</th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((row, index) => (
              <tr key={index}>
                <td>{text(row.rank)}</td>
                <td>{text(row.team)}</td>
                <td>
                  {text(row.wins)}–{text(row.losses)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  if (intent === "player_comparison")
    return (
      <section className="data-assistant-evidence">
        <EvidenceHeader season={season} />
        <div className="data-assistant-comparison">
          {evidence.map((row, index) => (
            <StatSummary key={index} row={row} />
          ))}
        </div>
      </section>
    );
  return (
    <section className="data-assistant-evidence">
      <EvidenceHeader season={season} />
      <div className="data-assistant-evidence-cards">
        {evidence.map((row, index) => (
          <StatSummary key={index} row={row} />
        ))}
      </div>
    </section>
  );
}

function StatSummary({ row }: { row: AssistantEvidence }) {
  const hidden = new Set(["type", "source", "season"]);
  return (
    <article>
      <strong>{text(row.player ?? row.team ?? row.type)}</strong>
      <div>
        {Object.entries(row)
          .filter(
            ([key, value]) =>
              !hidden.has(key) &&
              key !== "player" &&
              key !== "team" &&
              value !== null &&
              typeof value !== "object",
          )
          .map(([key, value]) => (
            <span key={key}>
              <em>{label(key)}</em>
              <b>{text(value)}</b>
            </span>
          ))}
      </div>
      <small>Source: database</small>
    </article>
  );
}

function EvidenceHeader({ season }: { season: string }) {
  return (
    <header>
      <div>
        <span>Records used</span>
        <strong>Evidence</strong>
      </div>
      <em>{season} · Database</em>
    </header>
  );
}
function AvailabilityMetric({ label: name, value }: { label: string; value: string | number }) {
  return (
    <div className="data-assistant-metric">
      <span>{name}</span>
      <strong>{value}</strong>
    </div>
  );
}
function clarificationChoices(answer: string) {
  const value = answer.split(":")[1]?.replace("?", "") ?? "";
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
function label(value: string) {
  return value
    .replace(/([A-Z])/g, " $1")
    .replaceAll("_", " ")
    .trim();
}
function text(value: unknown) {
  return value === undefined || value === null ? "—" : String(value);
}
