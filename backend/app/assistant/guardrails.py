from __future__ import annotations

from app.analytics.prediction_types import (
    JORDAN_PREDICTION_DISCLAIMER,
    JORDAN_PREDICTION_SEASON,
)

__all__ = [
    "JORDAN_PREDICTION_DISCLAIMER",
    "JORDAN_PREDICTION_SEASON",
]

PREDICTION_SEASON = "2026-27"


def is_betting_request(question: str) -> bool:
    value = question.casefold()
    return any(
        phrase in value
        for phrase in (
            "bet",
            "wager",
            "parlay",
            "gambling advice",
            "sportsbook",
            "point spread",
            "moneyline",
            "betting odds",
        )
    )


def is_prediction_request(question: str) -> bool:
    value = question.casefold()
    return any(
        phrase in value
        for phrase in (
            "predict",
            "projected",
            "projection",
            "who will win",
            "model favorite",
            "model's favorite",
            "model estimate",
            "likely to win",
            "would have made",
            "would win",
            "will make",
            "will finish",
            "does the model",
            "model predict",
            "model project",
            "all-nba model",
            "all nba model",
            "standings model",
            "finals model",
        )
    )


def require_jordan_prediction_season(season: str) -> None:
    if season != JORDAN_PREDICTION_SEASON:
        raise ValueError(
            f"Jordan prediction mode is only available for the {JORDAN_PREDICTION_SEASON} season."
        )


def blocked_answer(question: str, season: str) -> str | None:
    if is_betting_request(question):
        return "CourtVision does not provide betting advice."
    if is_prediction_request(question):
        if season != PREDICTION_SEASON:
            return (
                "Prediction capabilities are only available for the 2026-27 season. "
                "Historical seasons can be analyzed, but not predicted."
            )
        return None
    return None
