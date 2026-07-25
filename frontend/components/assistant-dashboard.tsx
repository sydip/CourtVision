"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  getAwardPrediction,
  getStandingsPrediction,
  sendAssistantMessage,
} from "@/lib/api/hoopsiq";
import type { AssistantSource, AwardPrediction, StandingsPrediction } from "@/lib/api/schemas";

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  text: string;
  sources?: AssistantSource[];
};

type ActiveInsight =
  | { kind: "award"; value: AwardPrediction }
  | { kind: "standings"; value: StandingsPrediction }
  | null;

const starterQuestions = [
  "Who is your MVP favorite for 2025-26?",
  "Who is your Rookie of the Year favorite for 2026-27?",
  "Predict the Western Conference standings.",
  "Compare Stephen Curry and LeBron James.",
  "What can you do?",
];

const awardOptions = ["MVP", "DPOY", "MIP", "ROY", "SIXTH_MAN"] as const;

export function AssistantDashboard() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      text:
        "Ask me about any stored player or team, compare performances, or run an " +
        "explainable award or standings projection.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string>();
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string>();
  const [insight, setInsight] = useState<ActiveInsight>(null);
  const [isLoadingInsight, setIsLoadingInsight] = useState(false);
  const messageSequence = useRef(0);

  function makeMessage(
    role: ChatMessage["role"],
    text: string,
    sources?: AssistantSource[],
  ): ChatMessage {
    messageSequence.current += 1;
    return { id: `message-${messageSequence.current}`, role, text, sources };
  }

  async function submitMessage(value: string) {
    const message = value.trim();
    if (!message || isSending) {
      return;
    }
    setMessages((current) => [...current, makeMessage("user", message)]);
    setInput("");
    setError(undefined);
    setIsSending(true);
    try {
      const response = await sendAssistantMessage(message, sessionId);
      setSessionId(response.session_id);
      setMessages((current) => [
        ...current,
        makeMessage("assistant", response.message, response.sources),
      ]);
      const detected = detectInsight(response.data);
      if (detected) {
        setInsight(detected);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Jordan is unavailable.");
    } finally {
      setIsSending(false);
    }
  }

  async function loadAward(award: string) {
    setIsLoadingInsight(true);
    setError(undefined);
    try {
      const targetSeason = award === "ROY" ? "2026-27" : "2025-26";
      setInsight({ kind: "award", value: await getAwardPrediction(award, targetSeason, 5) });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Projection unavailable.");
    } finally {
      setIsLoadingInsight(false);
    }
  }

  async function loadStandings(conference: "East" | "West") {
    setIsLoadingInsight(true);
    setError(undefined);
    try {
      setInsight({
        kind: "standings",
        value: await getStandingsPrediction("2025-26", conference),
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Projection unavailable.");
    } finally {
      setIsLoadingInsight(false);
    }
  }

  const sourceCount = useMemo(
    () => messages.reduce((total, message) => total + (message.sources?.length ?? 0), 0),
    [messages],
  );

  return (
    <div className="assistant-page">
      <header className="assistant-heading">
        <div>
          <span className="assistant-eyebrow">NBA intelligence assistant</span>
          <h1>Jordan</h1>
          <p>Grounded answers. Transparent projections. No invented stats.</p>
        </div>
        <div className="assistant-status" aria-label="Assistant status">
          <span />
          <strong>Database connected</strong>
          <em>{sourceCount} tool calls this session</em>
        </div>
      </header>

      <div className="assistant-layout">
        <aside className="assistant-rail" aria-label="Prediction shortcuts">
          <section>
            <span className="assistant-section-label">Award models</span>
            <div className="assistant-award-list">
              {awardOptions.map((award) => (
                <button
                  disabled={isLoadingInsight}
                  key={award}
                  onClick={() => void loadAward(award)}
                  type="button"
                >
                  <span>{award.replace("_", " ")}</span>
                  <i aria-hidden="true">›</i>
                </button>
              ))}
            </div>
          </section>
          <section>
            <span className="assistant-section-label">Standings</span>
            <div className="assistant-conference-actions">
              <button onClick={() => void loadStandings("East")} type="button">
                Eastern
              </button>
              <button onClick={() => void loadStandings("West")} type="button">
                Western
              </button>
            </div>
          </section>
          <div className="assistant-grounding-note">
            <span aria-hidden="true">✓</span>
            <div>
              <strong>Grounding enforced</strong>
              <p>Responses cite the database tools used to produce them.</p>
            </div>
          </div>
        </aside>

        <section className="assistant-chat-panel">
          <div className="assistant-chat-title">
            <div>
              <span className="assistant-avatar" aria-hidden="true">
                J
              </span>
              <div>
                <strong>Jordan</strong>
                <em>HoopsIQ analysis agent</em>
              </div>
            </div>
            <span className="assistant-mode">Structured data only</span>
          </div>

          <div className="assistant-messages" aria-live="polite">
            {messages.map((message) => (
              <article className={`assistant-message ${message.role}`} key={message.id}>
                <span className="assistant-message-role">
                  {message.role === "assistant" ? "J" : "You"}
                </span>
                <div>
                  <p>{message.text}</p>
                  {message.sources?.length ? (
                    <div className="assistant-sources">
                      {message.sources.map((source, index) => (
                        <span key={`${message.id}-${source.tool}-${index}`}>
                          {formatToolName(source.tool)}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              </article>
            ))}
            {isSending ? (
              <article className="assistant-message assistant pending">
                <span className="assistant-message-role">J</span>
                <div className="assistant-thinking" aria-label="Jordan is analyzing">
                  <i />
                  <i />
                  <i />
                </div>
              </article>
            ) : null}
          </div>

          {messages.length === 1 ? (
            <div className="assistant-starters">
              {starterQuestions.map((question) => (
                <button key={question} onClick={() => void submitMessage(question)} type="button">
                  {question}
                </button>
              ))}
            </div>
          ) : null}

          {error ? <p className="assistant-error">{error}</p> : null}

          <form
            className="assistant-composer"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              void submitMessage(input);
            }}
          >
            <textarea
              aria-label="Message Jordan"
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void submitMessage(input);
                }
              }}
              placeholder="Ask about a player, team, award, or projection..."
              rows={2}
              value={input}
            />
            <button disabled={isSending || !input.trim()} type="submit" aria-label="Send message">
              <span aria-hidden="true">↑</span>
            </button>
          </form>
        </section>

        <aside className="assistant-insight-panel" aria-label="Projection detail">
          <InsightPanel insight={insight} isLoading={isLoadingInsight} />
        </aside>
      </div>
    </div>
  );
}

function InsightPanel({ insight, isLoading }: { insight: ActiveInsight; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="assistant-insight-empty">
        <span className="assistant-insight-pulse" />
        <strong>Running model</strong>
        <p>Calculating normalized features and probabilities.</p>
      </div>
    );
  }
  if (!insight) {
    return (
      <div className="assistant-insight-empty">
        <span className="assistant-insight-orbit" aria-hidden="true">
          <i />
        </span>
        <strong>Projection workspace</strong>
        <p>Select an award or conference to inspect the model output and its drivers.</p>
      </div>
    );
  }
  if (insight.kind === "award") {
    const chartData = insight.value.candidates.map((candidate) => ({
      name: candidate.name.split(" ").at(-1),
      probability: Math.round(candidate.probability * 1000) / 10,
    }));
    const leader = insight.value.candidates[0];
    return (
      <>
        <div className="assistant-insight-heading">
          <div>
            <span>Model projection</span>
            <h2>{insight.value.award_type.replace("_", " ")}</h2>
          </div>
          <em>{insight.value.target_season}</em>
        </div>
        {leader ? (
          <div className="assistant-leader">
            <span>1</span>
            <div>
              <strong>{leader.name}</strong>
              <em>{leader.team}</em>
            </div>
            <b>{(leader.probability * 100).toFixed(1)}%</b>
          </div>
        ) : null}
        <div className="assistant-chart" aria-label="Award probability chart">
          <ResponsiveContainer height="100%" width="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 4, right: 12 }}>
              <CartesianGrid horizontal={false} stroke="rgba(133, 158, 190, 0.13)" />
              <XAxis domain={[0, "dataMax"]} hide type="number" />
              <YAxis
                axisLine={false}
                dataKey="name"
                tick={{ fill: "#aab9ca", fontSize: 12 }}
                tickLine={false}
                type="category"
                width={62}
              />
              <Tooltip
                contentStyle={{
                  background: "#07131f",
                  border: "1px solid #244157",
                  borderRadius: 6,
                }}
                formatter={(value) => [`${Number(value).toFixed(1)}%`, "Probability"]}
              />
              <Bar dataKey="probability" fill="#31d6b4" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        {leader ? <AttributionList attributions={leader.feature_attributions.slice(0, 4)} /> : null}
        <p className="assistant-methodology">{insight.value.methodology}</p>
      </>
    );
  }

  return (
    <>
      <div className="assistant-insight-heading">
        <div>
          <span>Projected standings</span>
          <h2>{insight.value.conference ?? "NBA"}</h2>
        </div>
        <em>{insight.value.target_season}</em>
      </div>
      <div className="assistant-standings-list">
        {insight.value.teams.slice(0, 10).map((team) => (
          <div key={team.team_id}>
            <span>{team.conference_rank ?? team.rank}</span>
            <strong>{team.abbreviation}</strong>
            <em>{team.team_name}</em>
            <b>
              {team.projected_wins}-{team.projected_losses}
            </b>
          </div>
        ))}
      </div>
      <p className="assistant-methodology">{insight.value.methodology}</p>
    </>
  );
}

function AttributionList({
  attributions,
}: {
  attributions: AwardPrediction["candidates"][number]["feature_attributions"];
}) {
  return (
    <div className="assistant-attributions">
      <span className="assistant-section-label">Why the model leads here</span>
      {attributions.map((item) => (
        <div key={item.feature}>
          <span>{item.feature.replaceAll("_", " ")}</span>
          <strong>{formatMetric(item.raw_value, item.feature)}</strong>
        </div>
      ))}
    </div>
  );
}

function detectInsight(data: Record<string, unknown> | null): ActiveInsight {
  if (!data) {
    return null;
  }
  if (typeof data.award_type === "string" && Array.isArray(data.candidates)) {
    return { kind: "award", value: data as AwardPrediction };
  }
  if (Array.isArray(data.teams) && typeof data.model_version === "string") {
    return { kind: "standings", value: data as StandingsPrediction };
  }
  return null;
}

function formatToolName(tool: string) {
  return tool.replaceAll("_", " ");
}

function formatMetric(value: number, feature: string) {
  if (feature.includes("percentage") || feature.includes("rate") || feature === "health_factor") {
    return `${(value * 100).toFixed(1)}%`;
  }
  return value.toFixed(1);
}
