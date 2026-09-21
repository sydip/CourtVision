from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant import sql_tools
from app.assistant.answer_renderer import render_answer
from app.assistant.entity_resolver import resolve_players, resolve_teams
from app.assistant.guardrails import blocked_answer
from app.assistant.intent_classifier import classify_intent
from app.assistant.prediction_tools import answer_prediction_question, is_prediction_question
from app.assistant.query_parser import parse_query


def answer_query(
    session: Session, question: str, selected_season: str | None = None
) -> dict[str, Any]:
    parsed = parse_query(question, selected_season)
    intent = classify_intent(question)
    blocked = blocked_answer(question, parsed.season)
    if blocked:
        return _response(blocked, "unsupported_request", parsed.season, [])
    if is_prediction_question(question):
        return answer_prediction_question(session, question, parsed.season)
    if intent == "methodology_explanation":
        method_evidence: list[dict[str, Any]] = [
            {
                "type": "methodology",
                "trueShootingFormula": "PTS / (2 × (FGA + 0.44 × FTA))",
                "source": "courtvision_methodology",
            }
        ]
        return _response(
            "CourtVision calculates true shooting as PTS / (2 × (FGA + 0.44 × FTA)).",
            intent,
            parsed.season,
            method_evidence,
        )
    if intent == "data_availability":
        seasons = sql_tools.available_seasons(session)
        availability_evidence: list[dict[str, Any]] = [
            {"type": "data_availability", "seasons": seasons, "source": "database"}
        ]
        return _response(
            f"CourtVision has stored player analytics for: {', '.join(seasons) or 'no seasons'}.",
            intent,
            parsed.season,
            availability_evidence,
        )

    player_resolution = resolve_players(session, question)
    team_resolution = resolve_teams(session, question)
    if player_resolution.ambiguous:
        names = [player.full_name for player in player_resolution.matches]
        return _response(
            f"Which player did you mean: {', '.join(names)}?", intent, parsed.season, [], True
        )
    evidence: list[dict[str, Any]] = []
    players = player_resolution.matches
    teams = team_resolution.matches
    if intent == "player_game_stats_exact" and players:
        evidence = sql_tools.player_games(
            session, players[0], parsed.season, parsed.game_date, teams[0] if teams else None
        )
    elif intent == "player_game_log_filter" and players:
        evidence = sql_tools.player_games(
            session, players[0], parsed.season, opponent=teams[0] if teams else None
        )
    elif intent == "player_season_stats" and players:
        evidence = sql_tools.player_season_stats(session, players[0], parsed.season)
    elif intent == "player_comparison" and len(players) >= 2:
        evidence = sql_tools.compare(session, players[:2], parsed.season)
    elif intent == "similar_players" and players:
        evidence = sql_tools.similar(session, players[0], parsed.season)
    elif intent == "team_season_summary" and teams:
        evidence = sql_tools.team_summary(session, teams[0], parsed.season)
    elif intent == "standings_lookup":
        evidence = sql_tools.standings(session, parsed.season, parsed.conference, parsed.limit)
    elif intent == "roster_lookup" and teams:
        evidence = sql_tools.roster(session, teams[0], parsed.season)
    elif intent == "team_leaders" and teams:
        evidence = sql_tools.team_leader(session, teams[0], parsed.season, parsed.stat)
    answer = render_answer(intent, evidence, parsed.season)
    return _response(answer, intent, parsed.season, evidence)


def _response(
    answer: str,
    intent: str,
    season: str,
    evidence: list[dict[str, Any]],
    clarification: bool = False,
) -> dict[str, Any]:
    return {
        "answer": answer,
        "intent": intent,
        "season": season,
        "evidence": evidence,
        "requiresClarification": clarification,
    }
