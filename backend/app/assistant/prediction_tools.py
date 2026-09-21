from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.guardrails import is_prediction_request
from app.predictions.service import PredictionNotReadyError, latest_prediction


def is_prediction_question(question: str) -> bool:
    return is_prediction_request(question)


def answer_prediction_question(session: Session, question: str, season: str) -> dict[str, Any]:
    target = _target(question)
    try:
        result = latest_prediction(session, target, season)
    except ValueError:
        return {
            "answer": (
                "Prediction capabilities are only available for the 2026-27 season. "
                "Historical seasons can be analyzed, but not predicted."
            ),
            "intent": "unsupported_request",
            "season": season,
            "evidence": [],
            "requiresClarification": False,
        }
    except PredictionNotReadyError:
        return {
            "answer": f"No completed {target.replace('_', ' ')} model run is available yet.",
            "intent": "prediction_lookup",
            "season": season,
            "evidence": [],
            "requiresClarification": False,
        }
    disclaimer = str(result.get("disclaimer") or "Experimental model estimate.")
    return {
        "answer": f"{_answer(target, result, question)} {disclaimer}",
        "intent": "prediction_lookup",
        "season": season,
        "evidence": [{"type": target, "source": "prediction_model", **result}],
        "requiresClarification": False,
    }


def _target(question: str) -> str:
    value = question.casefold()
    if "all-nba" in value or "all nba" in value or "player" in value:
        return "all_nba"
    if "final" in value or "champion" in value or "winner" in value:
        return "finals_winner"
    return "standings"


def _answer(target: str, result: dict[str, Any], question: str) -> str:
    explain = any(word in question.casefold() for word in ("why", "factor", "helped"))
    if target == "all_nba":
        players = list(result.get("data") or [])
        if not players:
            return "The experimental All-NBA model has no eligible player results."
        leader = players[0]
        if explain:
            factors = ", ".join(leader.get("topFactors") or []) or "the stored model features"
            return (
                f"{leader['playerName']} ranks first in the experimental All-NBA "
                f"estimate because of {factors}."
            )
        return (
            "The experimental 2026-27 All-NBA model ranks: "
            + ", ".join(player["playerName"] for player in players[:15])
            + "."
        )
    if target == "standings":
        teams = list(result.get("east") or []) + list(result.get("west") or [])
        if not teams:
            return "The experimental standings model has no team results."
        leader = teams[0]
        if explain:
            factors = ", ".join(leader.get("topFactors") or []) or "the stored model features"
            return f"{leader['teamName']} is projected first because of {factors}."
        return "The experimental 2026-27 standings estimate is available in the attached evidence."
    champion = result.get("predictedChampion")
    if not isinstance(champion, dict):
        return "The experimental Finals model has no contender results."
    factors = ", ".join(champion.get("topFactors") or [])
    suffix = f" The leading factors are {factors}." if explain and factors else ""
    probability = float(champion["probability"]) * 100
    return (
        f"The experimental model's highest-ranked 2026-27 Finals estimate is "
        f"{champion['teamName']} at {probability:.1f}%.{suffix}"
    )
