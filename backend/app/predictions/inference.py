from __future__ import annotations

from typing import Any

from app.predictions.explanations import explain_row
from app.predictions.features import FeatureRow
from app.predictions.guardrails import require_prediction_season
from app.predictions.models import ModelBundle


def rank_predictions(
    bundle: ModelBundle, rows: list[FeatureRow], season: str
) -> list[dict[str, Any]]:
    require_prediction_season(season)
    if not rows:
        return []
    matrix = [[row.values.get(name) for name in bundle.feature_names] for row in rows]
    probabilities = bundle.pipeline.predict_proba(matrix)[:, 1]
    ranked = sorted(
        zip(rows, probabilities, matrix, strict=True),
        key=lambda item: (-float(item[1]), item[0].entity_name),
    )
    return [
        {
            "entity_id": row.entity_id,
            "entity_name": row.entity_name,
            "season": season,
            "predicted_rank": rank,
            "probability": round(float(probability), 6),
            "experimental": True,
            "label": "Model estimate",
            "top_features": explain_row(bundle, values),
            "warnings": list(row.warnings),
        }
        for rank, (row, probability, values) in enumerate(ranked, 1)
    ]


def infer_all_nba(bundle: ModelBundle, rows: list[FeatureRow], season: str) -> list[dict[str, Any]]:
    return rank_predictions(bundle, rows, season)


def infer_standings(
    bundle: ModelBundle, rows: list[FeatureRow], season: str
) -> list[dict[str, Any]]:
    ranked = rank_predictions(bundle, rows, season)
    groups = {row.entity_id: row.group for row in rows}
    conference_ranks: dict[str, int] = {}
    for result in ranked:
        probability = float(result["probability"])
        wins = max(0, min(82, round(24 + probability * 38)))
        conference = groups.get(int(result["entity_id"])) or "Unknown"
        conference_ranks[conference] = conference_ranks.get(conference, 0) + 1
        result.update(
            {
                "predicted_wins": wins,
                "predicted_losses": 82 - wins,
                "playoff_probability": probability,
                "play_in_probability": round(1 - abs(probability - 0.5) * 2, 6),
                "confidence": round(abs(probability - 0.5) * 2, 6),
                "conference": conference,
                "conference_rank": conference_ranks[conference],
            }
        )
    return ranked


def infer_finals(bundle: ModelBundle, rows: list[FeatureRow], season: str) -> dict[str, Any]:
    contenders = rank_predictions(bundle, rows, season)
    return {
        "season": season,
        "predicted_champion": contenders[0] if contenders else None,
        "contenders": contenders,
        "experimental": True,
        "label": "Model estimate",
        "betting_advice": False,
    }
