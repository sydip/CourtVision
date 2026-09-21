from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.analytics.backtest import run_backtest
from app.assistant.chat import answer_message
from app.assistant.guardrails import JORDAN_PREDICTION_SEASON
from app.assistant.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantQueryRequest,
    AssistantQueryResponse,
    PredictionLogResponse,
)
from app.assistant.service import answer_query
from app.assistant.tools import (
    list_capabilities,
    list_predictions,
    predict_award,
    predict_league_standings,
)
from app.db.session import get_db_session

router = APIRouter(tags=["intelligence assistant"])


@router.post(
    "/assistant/query",
    response_model=AssistantQueryResponse,
    summary="Query stored CourtVision data",
    description="Classifies and executes safe repository-backed factual retrievals.",
)
async def assistant_query(
    request: AssistantQueryRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return answer_query(session, request.question, request.season)


@router.post(
    "/assistant/chat",
    response_model=AssistantChatResponse,
    summary="Chat with Jordan",
    description=(
        "Routes the message through grounded database and deterministic prediction tools. "
        "Uses Claude tool calling when configured and a local grounded router otherwise."
    ),
)
async def assistant_chat(
    request: AssistantChatRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    try:
        return answer_message(session, request.message, request.session_id)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/assistant/capabilities",
    summary="List grounded assistant capabilities",
)
async def assistant_capabilities(
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return list_capabilities(session)


@router.get(
    "/predictions/awards/{award_type}",
    summary="Project an NBA award",
)
async def award_prediction(
    award_type: Annotated[str, Path(min_length=2, max_length=32)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str, Query(min_length=4, max_length=16)] = "2025-26",
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> dict[str, Any]:
    _require_jordan_season(season)
    try:
        result = predict_award(session, award_type, season, limit=limit)
        session.commit()
        return result
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/predictions/standings",
    summary="Project NBA standings",
)
async def standings_prediction(
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str, Query(min_length=4, max_length=16)] = "2025-26",
    conference: Annotated[str | None, Query(max_length=16)] = None,
) -> dict[str, Any]:
    _require_jordan_season(season)
    try:
        result = predict_league_standings(session, season, conference)
        session.commit()
        return result
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/predictions",
    response_model=PredictionLogResponse,
    summary="List saved prediction runs",
)
async def prediction_log(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    return list_predictions(session, limit)


@router.get(
    "/predictions/backtest/{season}",
    summary="Backtest stored prediction outcomes",
)
async def prediction_backtest(
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return {
        **run_backtest(session, season).as_dict(),
        "disclaimer": "Historical model evaluation, not a prediction or betting recommendation.",
    }


def _require_jordan_season(season: str) -> None:
    if season != JORDAN_PREDICTION_SEASON:
        raise HTTPException(
            status_code=403,
            detail="Jordan prediction mode is only available for the 2025-26 season.",
        )
