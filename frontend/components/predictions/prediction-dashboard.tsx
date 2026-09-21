"use client";

import { useEffect, useState } from "react";

import {
  getAllNbaPrediction,
  getFinalsWinnerPrediction,
  getPredictionAvailability,
  getSeasonStandingsPrediction,
} from "@/lib/api/courtvision";
import type {
  AllNbaPrediction,
  FinalsWinnerPrediction,
  PredictionAvailability,
  SeasonStandingsPrediction,
} from "@/lib/api/schemas";

type PredictionState = {
  availability?: PredictionAvailability;
  allNba?: AllNbaPrediction;
  standings?: SeasonStandingsPrediction;
  finals?: FinalsWinnerPrediction;
  errors: Partial<Record<"availability" | "allNba" | "standings" | "finals", string>>;
};

export function PredictionDashboard() {
  const [state, setState] = useState<PredictionState>();

  useEffect(() => {
    let active = true;
    setState(undefined);
    Promise.allSettled([
      getPredictionAvailability(),
      getAllNbaPrediction(),
      getSeasonStandingsPrediction(),
      getFinalsWinnerPrediction(),
    ]).then(([availability, allNba, standings, finals]) => {
      if (!active) return;
      setState({
        availability: settledValue(availability),
        allNba: settledValue(allNba),
        standings: settledValue(standings),
        finals: settledValue(finals),
        errors: {
          availability: settledError(availability),
          allNba: settledError(allNba),
          standings: settledError(standings),
          finals: settledError(finals),
        },
      });
    });
    return () => {
      active = false;
    };
  }, []);

  if (!state) {
    return (
      <section className="prediction-state" role="status">
        <i />
        <strong>Loading 2026–27 model estimates…</strong>
      </section>
    );
  }

  return (
    <section className="prediction-workspace" aria-label="2026-27 predictions">
      <header className="prediction-availability">
        <div>
          <span>Following-season forecast</span>
          <strong>2026–27 model estimates</strong>
        </div>
        <p>Shown in the 2025–26 Jordan tab and grounded in stored historical training data.</p>
      </header>
      <div className="prediction-card-grid">
        {state.allNba ? (
          <AllNbaCard prediction={state.allNba} />
        ) : (
          <UnavailableCard
            detail={state.errors.allNba}
            eyebrow="Player model"
            title="All-NBA projection"
          />
        )}
        {state.finals ? (
          <FinalsCard prediction={state.finals} />
        ) : (
          <UnavailableCard
            detail={state.errors.finals}
            eyebrow="Championship model"
            title="Finals winner"
          />
        )}
      </div>
      {state.standings ? (
        <StandingsCard prediction={state.standings} />
      ) : (
        <UnavailableCard
          className="prediction-standings"
          detail={state.errors.standings}
          eyebrow="Team model"
          title="Projected standings"
        />
      )}
      <div className="prediction-info-grid">
        {state.allNba ? (
          <MethodologyPanel model={state.allNba.model} />
        ) : (
          <article className="prediction-info">
            <span>Methodology</span>
            <h3>Grounded models only</h3>
            <p>
              CourtVision displays a model only after its historical training labels and stored
              artifact are available. Missing model inputs are never fabricated.
            </p>
          </article>
        )}
        <DisclaimerPanel
          disclaimer={
            state.allNba?.disclaimer ??
            state.standings?.disclaimer ??
            state.finals?.disclaimer ??
            "Experimental model estimate, not an official prediction or betting recommendation."
          }
        />
      </div>
    </section>
  );
}

function UnavailableCard({
  className = "",
  detail,
  eyebrow,
  title,
}: {
  className?: string;
  detail?: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <article className={`prediction-card ${className}`.trim()} role="alert">
      <CardHeader eyebrow={eyebrow} title={title} />
      <div className="prediction-empty prediction-model-unavailable">
        <strong>Model not ready</strong>
        <span>{detail ?? "No completed grounded model run is available."}</span>
      </div>
    </article>
  );
}

function AllNbaCard({ prediction }: { prediction: AllNbaPrediction }) {
  return (
    <article className="prediction-card prediction-all-nba">
      <CardHeader eyebrow="Player model" title="All-NBA projection" />
      {prediction.data.length ? (
        <div className="prediction-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Player</th>
                <th>Probability</th>
                <th>Team</th>
              </tr>
            </thead>
            <tbody>
              {prediction.data.map((player) => (
                <tr key={player.playerId}>
                  <td>{player.predictedRank ?? "—"}</td>
                  <td>
                    <strong>{player.playerName}</strong>
                    <span>{player.team ?? "Team unavailable"}</span>
                    {player.topFactors.length ? (
                      <small title={player.topFactors.join(", ")}>{player.topFactors[0]}</small>
                    ) : null}
                  </td>
                  <td>
                    {percent(player.probability)}
                    {lowConfidence(player.probability) ? <em>Low confidence</em> : null}
                  </td>
                  <td>{player.projectedTeam ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <PredictionEmpty label="No All-NBA prediction results are available." />
      )}
    </article>
  );
}

function StandingsCard({ prediction }: { prediction: SeasonStandingsPrediction }) {
  return (
    <article className="prediction-card prediction-standings">
      <CardHeader eyebrow="Team model" title="Projected standings" />
      <div className="prediction-conferences">
        <ConferenceTable label="Eastern Conference" teams={prediction.east} />
        <ConferenceTable label="Western Conference" teams={prediction.west} />
      </div>
      <p className="prediction-card-disclaimer">{prediction.disclaimer}</p>
    </article>
  );
}

function ConferenceTable({
  label,
  teams,
}: {
  label: string;
  teams: SeasonStandingsPrediction["east"];
}) {
  if (!teams.length)
    return (
      <div>
        <h3>{label}</h3>
        <PredictionEmpty label={`No ${label} results are available.`} />
      </div>
    );
  return (
    <div>
      <h3>{label}</h3>
      <div className="prediction-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Team</th>
              <th>W–L</th>
              <th>Playoffs</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team) => (
              <tr key={team.teamId}>
                <td>{team.rank ?? "—"}</td>
                <td>
                  <strong title={team.topFactors.join(", ") || "No factor details available"}>
                    {team.teamName}
                  </strong>
                </td>
                <td>
                  {team.predictedWins ?? "—"}–{team.predictedLosses ?? "—"}
                </td>
                <td>{percent(team.playoffProbability)}</td>
                <td>{percent(team.confidence)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FinalsCard({ prediction }: { prediction: FinalsWinnerPrediction }) {
  const champion = prediction.predictedChampion;
  return (
    <article className="prediction-card prediction-finals">
      <CardHeader eyebrow="Championship model" title="Finals winner" />
      {champion ? (
        <div className="prediction-champion">
          <span>Predicted champion</span>
          <strong>{champion.teamName}</strong>
          <b>{percent(champion.probability)}</b>
          <small>Estimated title probability</small>
        </div>
      ) : (
        <PredictionEmpty label="No Finals winner result is available." />
      )}
      {prediction.contenders.length ? (
        <div className="prediction-contenders">
          <span>Top contenders</span>
          {prediction.contenders.slice(0, 5).map((team) => (
            <div key={team.teamId}>
              <strong>{team.teamName}</strong>
              <em>{percent(team.probability)}</em>
            </div>
          ))}
        </div>
      ) : null}
      <p>{prediction.disclaimer}</p>
    </article>
  );
}

function MethodologyPanel({ model }: { model: AllNbaPrediction["model"] }) {
  return (
    <article className="prediction-info">
      <span>Methodology</span>
      <h3>How estimates are produced</h3>
      <p>
        A logistic-regression-style model uses stored player and team features from{" "}
        {model.trainingSeasons.join(", ")}. Inputs include performance, availability, minutes, and
        team-strength signals.
      </p>
      <small>
        {model.name} · v{model.version}
      </small>
    </article>
  );
}

function DisclaimerPanel({ disclaimer }: { disclaimer: string }) {
  return (
    <article className="prediction-info prediction-disclaimer">
      <span>Important</span>
      <h3>Model estimates, not facts</h3>
      <p>
        {disclaimer} Outputs may be affected by small samples, incomplete projected rosters,
        injuries, and changing roles.
      </p>
      <strong>No betting usage.</strong>
    </article>
  );
}

function CardHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <header className="prediction-card-header">
      <div>
        <span>{eyebrow}</span>
        <h2>{title}</h2>
      </div>
      <em>2026–27</em>
    </header>
  );
}
function PredictionEmpty({ label }: { label: string }) {
  return (
    <div className="prediction-empty">
      <strong>No model results</strong>
      <span>{label}</span>
    </div>
  );
}
function percent(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}
function lowConfidence(value: number | null) {
  return value !== null && value < 0.5;
}

function settledValue<T>(result: PromiseSettledResult<T>): T | undefined {
  return result.status === "fulfilled" ? result.value : undefined;
}

function settledError<T>(result: PromiseSettledResult<T>): string | undefined {
  if (result.status === "fulfilled") return undefined;
  return result.reason instanceof Error ? result.reason.message : "Model results are unavailable.";
}
