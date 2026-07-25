from __future__ import annotations

from dataclasses import replace
from typing import Final

from sqlalchemy.orm import Session

from app.analytics.features import load_team_projection_features, z_scores
from app.analytics.prediction_types import (
    ProjectedTeam,
    StandingsPredictionResult,
    TeamProjectionFeatures,
)
from app.models import Prediction

STANDINGS_MODEL_VERSION: Final = "hoopsiq-standings-heuristic-v1"


def predict_standings(
    session: Session,
    target_season: str,
    conference: str | None = None,
    *,
    persist: bool = True,
) -> StandingsPredictionResult:
    source_season, features = load_team_projection_features(session, target_season)
    result = score_standings(
        features,
        target_season=target_season,
        source_season=source_season,
        conference=conference,
    )
    if not persist:
        return result
    prediction = Prediction(
        target_season=target_season,
        prediction_type="standings",
        payload=result.as_dict(),
        model_version=STANDINGS_MODEL_VERSION,
        random_seed=None,
        notes=f"Grounded in stored {source_season} rosters and season summaries.",
    )
    session.add(prediction)
    session.flush()
    persisted = replace(result, prediction_id=prediction.id)
    prediction.payload = persisted.as_dict()
    return persisted


def score_standings(
    features: list[TeamProjectionFeatures],
    *,
    target_season: str,
    source_season: str,
    conference: str | None,
) -> StandingsPredictionResult:
    normalized_conference = _normalize_conference(conference)
    selected = [
        team
        for team in features
        if normalized_conference is None
        or _normalize_conference(team.conference) == normalized_conference
    ]
    if not selected:
        raise ValueError("No teams with stored player summaries match the requested conference.")
    plus_minus_z = z_scores([team.weighted_plus_minus for team in selected])
    production_z = z_scores([team.weighted_production for team in selected])
    efficiency_z = z_scores([team.weighted_true_shooting for team in selected])
    scored: list[
        tuple[TeamProjectionFeatures, float, list[dict[str, float | str]]]
    ] = []
    for index, team in enumerate(selected):
        factors: list[dict[str, float | str]] = [
            {
                "feature": "weighted_plus_minus",
                "raw_value": round(team.weighted_plus_minus, 3),
                "contribution": round(plus_minus_z[index] * 2.4, 3),
            },
            {
                "feature": "rotation_production",
                "raw_value": round(team.weighted_production, 3),
                "contribution": round(production_z[index] * 1.4, 3),
            },
            {
                "feature": "true_shooting",
                "raw_value": round(team.weighted_true_shooting, 4),
                "contribution": round(efficiency_z[index] * 1.1, 3),
            },
            {
                "feature": "continuity",
                "raw_value": round(team.continuity, 4),
                "contribution": round((team.continuity - 0.65) * 2.0, 3),
            },
            {
                "feature": "health",
                "raw_value": round(team.health_factor, 4),
                "contribution": round((team.health_factor - 0.85) * 2.5, 3),
            },
        ]
        point_differential = sum(float(factor["contribution"]) for factor in factors)
        scored.append((team, point_differential, factors))
    scored.sort(key=lambda row: (-row[1], row[0].team_name))

    conference_counts: dict[str, int] = {}
    projected: list[ProjectedTeam] = []
    for rank, (team, point_differential, factors) in enumerate(scored, start=1):
        wins = round(max(15, min(67, 41 + point_differential * 2.7)))
        conference_key = _normalize_conference(team.conference) or "unknown"
        conference_counts[conference_key] = conference_counts.get(conference_key, 0) + 1
        projected.append(
            ProjectedTeam(
                rank=rank,
                conference_rank=conference_counts[conference_key],
                team_id=team.team_id,
                nba_team_id=team.nba_team_id,
                team_name=team.team_name,
                abbreviation=team.abbreviation,
                conference=team.conference,
                division=team.division,
                projected_wins=wins,
                projected_losses=82 - wins,
                projected_point_differential=round(point_differential, 2),
                confidence=round(min(0.9, 0.45 + team.rotation_size / 25), 3),
                factors=sorted(
                    factors,
                    key=lambda factor: abs(float(factor["contribution"])),
                    reverse=True,
                ),
                warnings=(
                    ["Projection includes synthetic input data."] if team.is_synthetic else []
                ),
            )
        )
    warnings: list[str] = []
    if source_season != target_season:
        warnings.append(
            f"{target_season} is not loaded; the projection uses {source_season} inputs."
        )
    if len(projected) < 30 and normalized_conference is None:
        warnings.append(
            f"Only {len(projected)} teams have enough stored roster data for a projection."
        )
    return StandingsPredictionResult(
        prediction_id=None,
        target_season=target_season,
        source_season=source_season,
        conference=normalized_conference,
        model_version=STANDINGS_MODEL_VERSION,
        teams=projected,
        warnings=warnings,
        methodology=(
            "Transparent roster-aggregation model using rotation plus-minus, production, "
            "true shooting, continuity, and available injury context. Projected point "
            "differential is mapped to wins; results are estimates, not guarantees."
        ),
    )


def _normalize_conference(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    if normalized in {"east", "eastern"}:
        return "East"
    if normalized in {"west", "western"}:
        return "West"
    return value.strip()
