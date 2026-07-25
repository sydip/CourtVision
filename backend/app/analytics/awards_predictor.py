from __future__ import annotations

from dataclasses import replace
from math import exp
from typing import Final

from sqlalchemy.orm import Session

from app.analytics.features import load_player_projection_features, z_scores
from app.analytics.prediction_types import (
    AwardPredictionResult,
    PlayerProjectionFeatures,
    RankedCandidate,
)
from app.analytics.rookie_predictor import (
    load_rookie_projection_features,
    score_rookie_candidates,
)
from app.models import Prediction

AWARD_MODEL_VERSION: Final = "hoopsiq-awards-heuristic-v1"
SUPPORTED_AWARDS: Final = {
    "MVP",
    "DPOY",
    "ROY",
    "MIP",
    "SIXTH_MAN",
    "ALL_NBA_1",
    "ALL_NBA_2",
    "ALL_NBA_3",
    "ALL_DEFENSE_1",
    "ALL_DEFENSE_2",
    "ALL_STAR",
}

AWARD_WEIGHTS: Final[dict[str, dict[str, float]]] = {
    "MVP": {
        "points_per_game": 0.24,
        "assists_per_game": 0.12,
        "rebounds_per_game": 0.08,
        "true_shooting_percentage": 0.14,
        "plus_minus_per_game": 0.14,
        "team_strength": 0.15,
        "games_played": 0.08,
        "health_factor": 0.05,
    },
    "DPOY": {
        "steals_per_game": 0.25,
        "blocks_per_game": 0.32,
        "rebounds_per_game": 0.10,
        "plus_minus_per_game": 0.13,
        "team_strength": 0.12,
        "games_played": 0.08,
    },
    "ROY": {
        "points_per_game": 0.30,
        "assists_per_game": 0.15,
        "rebounds_per_game": 0.12,
        "true_shooting_percentage": 0.13,
        "minutes_per_game": 0.15,
        "games_played": 0.15,
    },
    "MIP": {
        "year_over_year_points_delta": 0.35,
        "year_over_year_minutes_delta": 0.18,
        "minutes_trend": 0.12,
        "points_per_game": 0.12,
        "true_shooting_percentage": 0.10,
        "team_strength": 0.08,
        "games_played": 0.05,
    },
    "SIXTH_MAN": {
        "points_per_game": 0.38,
        "assists_per_game": 0.15,
        "rebounds_per_game": 0.10,
        "true_shooting_percentage": 0.17,
        "minutes_per_game": 0.10,
        "games_played": 0.10,
    },
    "ALL_NBA": {
        "points_per_game": 0.24,
        "assists_per_game": 0.14,
        "rebounds_per_game": 0.10,
        "true_shooting_percentage": 0.13,
        "plus_minus_per_game": 0.14,
        "team_strength": 0.13,
        "games_played": 0.12,
    },
    "ALL_DEFENSE": {
        "steals_per_game": 0.24,
        "blocks_per_game": 0.30,
        "rebounds_per_game": 0.10,
        "plus_minus_per_game": 0.14,
        "team_strength": 0.12,
        "games_played": 0.10,
    },
    "ALL_STAR": {
        "points_per_game": 0.28,
        "assists_per_game": 0.14,
        "rebounds_per_game": 0.11,
        "true_shooting_percentage": 0.12,
        "plus_minus_per_game": 0.12,
        "team_strength": 0.11,
        "games_played": 0.12,
    },
}


def predict_awards(
    session: Session,
    target_season: str,
    award_type: str,
    *,
    limit: int = 10,
    persist: bool = True,
) -> AwardPredictionResult:
    normalized_award = award_type.strip().upper().replace(" ", "_")
    if normalized_award not in SUPPORTED_AWARDS:
        supported = ", ".join(sorted(SUPPORTED_AWARDS))
        raise ValueError(f"Unsupported award type '{award_type}'. Supported values: {supported}.")
    if normalized_award == "ROY":
        source_season, rookie_features = load_rookie_projection_features(
            session,
            target_season,
        )
    else:
        source_season, rookie_features = "", []
    if rookie_features:
        result = score_rookie_candidates(
            rookie_features,
            target_season=target_season,
            source_season=source_season,
            limit=limit,
        )
    else:
        source_season, features = load_player_projection_features(session, target_season)
        result = score_award_candidates(
            features,
            normalized_award,
            target_season=target_season,
            source_season=source_season,
            limit=limit,
        )
    if not persist:
        return result
    prediction = Prediction(
        target_season=target_season,
        prediction_type=f"award:{normalized_award}",
        payload=result.as_dict(),
        model_version=result.model_version,
        random_seed=None,
        notes=f"Grounded in stored {source_season} data and persisted HoopsIQ records.",
    )
    session.add(prediction)
    session.flush()
    persisted = replace(result, prediction_id=prediction.id)
    prediction.payload = persisted.as_dict()
    return persisted


def score_award_candidates(
    features: list[PlayerProjectionFeatures],
    award_type: str,
    *,
    target_season: str,
    source_season: str,
    limit: int = 10,
) -> AwardPredictionResult:
    candidates, warnings = _eligible_candidates(features, award_type)
    if not candidates:
        raise ValueError(f"No eligible candidates are available for {award_type}.")
    weights = _weights_for_award(award_type)
    normalized_by_metric = {
        metric: z_scores([float(getattr(candidate, metric)) for candidate in candidates])
        for metric in weights
    }
    scored: list[tuple[PlayerProjectionFeatures, float, list[dict[str, float | str]]]] = []
    for index, candidate in enumerate(candidates):
        attributions: list[dict[str, float | str]] = []
        score = 0.0
        for metric, weight in weights.items():
            raw_value = float(getattr(candidate, metric))
            normalized_value = normalized_by_metric[metric][index]
            contribution = weight * normalized_value
            score += contribution
            attributions.append(
                {
                    "feature": metric,
                    "raw_value": round(raw_value, 4),
                    "normalized_value": round(normalized_value, 4),
                    "weight": weight,
                    "contribution": round(contribution, 4),
                }
            )
        scored.append((candidate, score, attributions))

    contender_pool = sorted(
        scored,
        key=lambda row: (-row[1], row[0].player_name),
    )[:25]
    probabilities = _softmax(
        [score for _, score, _ in contender_pool],
        temperature=0.65,
    )
    rows = sorted(
        zip(contender_pool, probabilities, strict=True),
        key=lambda row: (-row[1], row[0][0].player_name),
    )
    ranked = [
        RankedCandidate(
            rank=rank,
            entity_id=candidate.nba_player_id,
            name=candidate.player_name,
            team=candidate.team_name,
            position=candidate.position,
            probability=round(probability, 6),
            score=round(score, 6),
            features={
                metric: round(float(getattr(candidate, metric)), 4) for metric in weights
            },
            feature_attributions=sorted(
                attributions,
                key=lambda item: abs(float(item["contribution"])),
                reverse=True,
            ),
            warnings=_candidate_warnings(candidate),
        )
        for rank, ((candidate, score, attributions), probability) in enumerate(
            rows[:limit],
            start=1,
        )
    ]
    if source_season != target_season:
        warnings.append(
            f"{target_season} is not loaded; projections use the latest available "
            f"stored season ({source_season})."
        )
    if any(candidate.is_synthetic for candidate in candidates):
        warnings.append("At least one candidate includes synthetic source data.")
    return AwardPredictionResult(
        prediction_id=None,
        award_type=award_type,
        target_season=target_season,
        source_season=source_season,
        model_version=AWARD_MODEL_VERSION,
        candidates=ranked,
        warnings=warnings,
        methodology=(
            "Transparent weighted z-score model. The 25 highest-scoring eligible contenders "
            "form the probability pool, then softmax converts their scores to estimates. "
            "Probabilities are not guarantees."
        ),
    )


def _eligible_candidates(
    features: list[PlayerProjectionFeatures],
    award_type: str,
) -> tuple[list[PlayerProjectionFeatures], list[str]]:
    candidates = [
        candidate
        for candidate in features
        if candidate.games_played >= 15 and candidate.minutes_per_game >= 10
    ]
    warnings: list[str] = []
    if award_type == "ROY":
        rookies = [
            candidate
            for candidate in candidates
            if candidate.years_pro in (0, 1)
            or (
                candidate.age is not None
                and candidate.age <= 22
                and candidate.year_over_year_points_delta == 0
            )
        ]
        if rookies:
            candidates = rookies
        else:
            warnings.append(
                "Rookie service-time metadata is incomplete; the youngest eligible "
                "players are used as a proxy."
            )
            candidates = sorted(
                candidates,
                key=lambda candidate: candidate.age if candidate.age is not None else 99,
            )[:40]
    elif award_type == "SIXTH_MAN":
        bench = [candidate for candidate in candidates if not candidate.is_starter]
        if bench:
            candidates = bench
        else:
            warnings.append(
                "Games-started data is incomplete; starter status was inferred from minutes."
            )
    elif award_type == "MIP":
        if not any(candidate.year_over_year_points_delta for candidate in candidates):
            warnings.append(
                "No prior-season summaries are loaded, so MIP improvement deltas are neutral."
            )
    return candidates, warnings


def _weights_for_award(award_type: str) -> dict[str, float]:
    if award_type.startswith("ALL_NBA"):
        return AWARD_WEIGHTS["ALL_NBA"]
    if award_type.startswith("ALL_DEFENSE"):
        return AWARD_WEIGHTS["ALL_DEFENSE"]
    return AWARD_WEIGHTS[award_type]


def _softmax(scores: list[float], temperature: float) -> list[float]:
    maximum = max(scores)
    exponents = [exp((score - maximum) / temperature) for score in scores]
    denominator = sum(exponents)
    return [value / denominator for value in exponents]


def _candidate_warnings(candidate: PlayerProjectionFeatures) -> list[str]:
    warnings: list[str] = []
    if candidate.games_played < 25:
        warnings.append(f"Small sample: {candidate.games_played} games.")
    if candidate.is_synthetic:
        warnings.append(f"Source '{candidate.data_source}' is marked synthetic.")
    return warnings
