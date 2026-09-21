from __future__ import annotations

from typing import Any


def render_answer(intent: str, evidence: list[dict[str, Any]], season: str) -> str:
    if not evidence:
        if intent in {"player_game_stats_exact", "player_game_log_filter"}:
            return "I do not have that game in the CourtVision database."
        return f"I do not have matching {season} data in the CourtVision database."
    first = evidence[0]
    if intent == "player_game_stats_exact":
        return (
            f"{first['player']} scored {first['points']} points against the "
            f"{first['opponent']} on {_date(first['gameDate'])}."
        )
    if intent == "player_game_log_filter":
        noun = "entry" if len(evidence) == 1 else "entries"
        return f"I found {len(evidence)} matching {season} game log {noun} for {first['player']}."
    if intent == "player_season_stats":
        ts = first.get("trueShootingPercentage")
        ts_text = "unavailable" if ts is None else f"{ts * 100:.1f}%"
        return (
            f"In {season}, {first['player']} averaged {first['pointsPerGame']} points, "
            f"{first['reboundsPerGame']} rebounds, and {first['assistsPerGame']} assists "
            f"per game. True shooting: {ts_text}."
        )
    if intent == "team_season_summary":
        return (
            f"The {first['team']} finished {season} with a "
            f"{first['wins']}-{first['losses']} record."
        )
    if intent == "standings_lookup":
        return (
            f"The top stored {first['conference']} teams in {season} were: "
            + ", ".join(
                f"{row['rank']}. {row['team']} ({row['wins']}-{row['losses']})" for row in evidence
            )
            + "."
        )
    if intent == "roster_lookup":
        return (
            f"The stored {season} {first['team']} roster includes: "
            + ", ".join(row["player"] for row in evidence)
            + "."
        )
    if intent == "team_leaders":
        label = first["stat"].replace("_per_game", "").replace("_", " ")
        return (
            f"{first['player']} led the {first['team']} in {label} during {season} "
            f"at {first['value']} per game."
        )
    if intent == "player_comparison":
        return (
            "For "
            + season
            + ": "
            + "; ".join(
                f"{row['player']} — {row['pointsPerGame']} PPG, "
                f"{row['reboundsPerGame']} RPG, {row['assistsPerGame']} APG"
                for row in evidence
            )
            + "."
        )
    if intent == "similar_players":
        return (
            f"The closest stored {season} comparisons for {first['comparedTo']} are "
            + ", ".join(row["player"] for row in evidence)
            + "."
        )
    return "I found matching CourtVision database records."


def _date(value: str) -> str:
    from datetime import date

    parsed = date.fromisoformat(value)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
