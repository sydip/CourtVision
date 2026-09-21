from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Player, PredictionResult, PredictionRun, Team
from app.predictions.datasets import build_inference_rows
from app.predictions.guardrails import (
    PREDICTION_SEASON,
    TRAINING_SEASONS,
    require_prediction_season,
    require_target,
)
from app.predictions.inference import infer_all_nba, infer_finals, infer_standings
from app.predictions.models import load_bundle

ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "model_artifacts"
DISCLAIMER = "Experimental model estimate, not an official prediction or betting recommendation."


class PredictionNotReadyError(RuntimeError):
    pass


def availability() -> dict[str, Any]:
    return {
        "predictionSeason": PREDICTION_SEASON,
        "enabled": True,
        "supportedPredictionTypes": ["all_nba", "standings", "finals_winner"],
        "blockedSeasons": list(TRAINING_SEASONS),
        "message": "Predictions are only available for the 2026-27 season.",
    }


def run_prediction(session: Session, target: str, season: str) -> PredictionRun:
    require_prediction_season(season)
    require_target(target)
    artifact = ARTIFACT_ROOT / target / "model.joblib"
    if not artifact.exists():
        raise PredictionNotReadyError(f"The {target} model artifact has not been trained yet.")
    bundle = load_bundle(artifact)
    if bundle.target != target:
        raise PredictionNotReadyError("The model artifact target does not match the request.")
    rows = build_inference_rows(session, target, season)
    if not rows:
        raise PredictionNotReadyError(
            f"No eligible {season} feature rows are available for {target}."
        )
    run = PredictionRun(
        season=season,
        prediction_type=target,
        model_name=f"logistic_regression_{target}",
        model_version="0.1.0",
        training_seasons=list(bundle.training_seasons),
        feature_set_version="features-v1",
        status="running",
        started_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    if target == "all_nba":
        values = infer_all_nba(bundle, rows, season)[:15]
    elif target == "standings":
        values = infer_standings(bundle, rows, season)
    else:
        values = infer_finals(bundle, rows, season)["contenders"]
    for value in values:
        rank = int(value["predicted_rank"])
        session.add(
            PredictionResult(
                prediction_run_id=run.id,
                season=season,
                prediction_type=target,
                entity_type="player" if target == "all_nba" else "team",
                entity_id=int(value["entity_id"]),
                predicted_rank=rank,
                predicted_label=_predicted_label(target, rank),
                probability=Decimal(str(value["probability"])),
                score=Decimal(str(value["probability"])),
                explanation_json=value,
            )
        )
    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    session.flush()
    return run


def latest_prediction(session: Session, target: str, season: str) -> dict[str, Any]:
    require_prediction_season(season)
    require_target(target)
    run = session.scalar(
        select(PredictionRun)
        .options(selectinload(PredictionRun.results))
        .where(
            PredictionRun.season == season,
            PredictionRun.prediction_type == target,
            PredictionRun.status == "completed",
        )
        .order_by(PredictionRun.created_at.desc(), PredictionRun.id.desc())
        .limit(1)
    )
    if run is None:
        raise PredictionNotReadyError(f"No completed {target} prediction run is available.")
    return format_prediction(session, run)


def get_run(session: Session, run_id: int) -> PredictionRun | None:
    return session.scalar(
        select(PredictionRun)
        .options(selectinload(PredictionRun.results))
        .where(PredictionRun.id == run_id)
    )


def format_run(run: PredictionRun) -> dict[str, Any]:
    return {
        "runId": run.id,
        "season": run.season,
        "predictionType": run.prediction_type,
        "status": run.status,
        "modelName": run.model_name,
        "modelVersion": run.model_version,
        "trainingSeasons": run.training_seasons,
        "createdAt": run.created_at.isoformat(),
        "completedAt": run.completed_at.isoformat() if run.completed_at else None,
        "errorMessage": run.error_message,
        "resultCount": len(run.results),
    }


def format_prediction(session: Session, run: PredictionRun) -> dict[str, Any]:
    ordered = sorted(
        run.results, key=lambda result: (result.predicted_rank or 999, result.entity_id)
    )
    model = {
        "name": run.model_name,
        "version": run.model_version,
        "trainingSeasons": run.training_seasons,
    }
    if run.prediction_type == "all_nba":
        data = [_all_nba_item(session, result) for result in ordered]
        return {
            "season": run.season,
            "predictionType": "all_nba",
            "model": model,
            "data": data,
            "disclaimer": DISCLAIMER,
        }
    if run.prediction_type == "standings":
        items = [_standings_item(session, result) for result in ordered]
        return {
            "season": run.season,
            "predictionType": "standings",
            "east": [item for item in items if item["conference"] == "East"],
            "west": [item for item in items if item["conference"] == "West"],
            "disclaimer": DISCLAIMER,
        }
    contenders = [_finals_item(session, result) for result in ordered]
    return {
        "season": run.season,
        "predictionType": "finals_winner",
        "predictedChampion": contenders[0] if contenders else None,
        "contenders": contenders,
        "disclaimer": DISCLAIMER,
    }


def _all_nba_item(session: Session, result: PredictionResult) -> dict[str, Any]:
    player = session.get(Player, result.entity_id)
    explanation = result.explanation_json or {}
    return {
        "playerId": result.entity_id,
        "playerName": player.full_name if player else f"Player {result.entity_id}",
        "team": _player_team(player),
        "predictedRank": result.predicted_rank,
        "probability": _float(result.probability),
        "projectedTeam": result.predicted_label,
        "topFactors": _factors(explanation),
        "warnings": explanation.get("warnings", []),
    }


def _standings_item(session: Session, result: PredictionResult) -> dict[str, Any]:
    team = session.get(Team, result.entity_id)
    explanation = result.explanation_json or {}
    return {
        "rank": explanation.get("conference_rank", result.predicted_rank),
        "teamId": result.entity_id,
        "teamName": _team_name(team),
        "conference": explanation.get("conference") or (team.conference if team else None),
        "predictedWins": explanation.get("predicted_wins"),
        "predictedLosses": explanation.get("predicted_losses"),
        "playoffProbability": explanation.get("playoff_probability", _float(result.probability)),
        "confidence": explanation.get("confidence"),
        "topFactors": _factors(explanation),
    }


def _finals_item(session: Session, result: PredictionResult) -> dict[str, Any]:
    team = session.get(Team, result.entity_id)
    return {
        "teamId": result.entity_id,
        "teamName": _team_name(team),
        "probability": _float(result.probability),
        "topFactors": _factors(result.explanation_json or {}),
    }


def _factors(explanation: dict[str, object]) -> list[str]:
    values = explanation.get("top_features", [])
    if not isinstance(values, list):
        return []
    return [
        str(item.get("feature", "factor")).replace("_", " ").title()
        for item in values
        if isinstance(item, dict)
    ]


def _predicted_label(target: str, rank: int) -> str | None:
    if target != "all_nba":
        return None
    return "First Team" if rank <= 5 else "Second Team" if rank <= 10 else "Third Team"


def _player_team(player: Player | None) -> str | None:
    return _team_name(player.team) if player else None


def _team_name(team: Team | None) -> str:
    return f"{team.city} {team.name}" if team else "Unknown team"


def _float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
