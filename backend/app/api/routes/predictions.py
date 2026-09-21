from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.predictions.guardrails import PREDICTION_SEASON
from app.predictions.schemas import (
    PredictionApiResponse,
    PredictionAvailabilityResponse,
    PredictionRunRequest,
    PredictionRunResponse,
)
from app.predictions.service import (
    PredictionNotReadyError,
    availability,
    format_run,
    get_run,
    latest_prediction,
    run_prediction,
)

router = APIRouter(prefix="/predictions", tags=["2026-27 predictions"])


@router.get("/availability", response_model=PredictionAvailabilityResponse)
async def prediction_availability() -> dict[str, Any]:
    return availability()


@router.get("/{season}/all-nba", response_model=PredictionApiResponse)
async def all_nba_prediction(
    season: str, session: Annotated[Session, Depends(get_db_session)]
) -> dict[str, Any]:
    return _latest(session, "all_nba", season)


@router.get("/{season}/standings", response_model=PredictionApiResponse)
async def season_standings_prediction(
    season: str, session: Annotated[Session, Depends(get_db_session)]
) -> dict[str, Any]:
    return _latest(session, "standings", season)


@router.get("/{season}/finals-winner", response_model=PredictionApiResponse)
async def finals_winner_prediction(
    season: str, session: Annotated[Session, Depends(get_db_session)]
) -> dict[str, Any]:
    return _latest(session, "finals_winner", season)


@router.post("/{season}/run", response_model=PredictionRunResponse)
async def execute_prediction_run(
    request: PredictionRunRequest, season: str, session: Annotated[Session, Depends(get_db_session)]
) -> dict[str, Any]:
    _gate(season)
    try:
        run = run_prediction(session, request.predictionType, season)
        session.commit()
        session.refresh(run)
        return format_run(run)
    except PredictionNotReadyError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=PredictionRunResponse)
async def prediction_run(
    run_id: Annotated[int, Path(ge=1)], session: Annotated[Session, Depends(get_db_session)]
) -> dict[str, Any]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Prediction run was not found.")
    _gate(run.season)
    return format_run(run)


def _latest(session: Session, target: str, season: str) -> dict[str, Any]:
    _gate(season)
    try:
        return latest_prediction(session, target, season)
    except PredictionNotReadyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _gate(season: str) -> None:
    if season != PREDICTION_SEASON:
        raise HTTPException(
            status_code=403,
            detail="Prediction capabilities are only available for the 2026-27 season.",
        )
