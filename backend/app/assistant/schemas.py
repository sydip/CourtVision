from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=100)


class AssistantContextResponse(BaseModel):
    last_entity_type: str | None
    last_entity_name: str | None


class AssistantSourceResponse(BaseModel):
    tool: str
    arguments: dict[str, Any]


class AssistantChatResponse(BaseModel):
    session_id: str
    message: str
    mode: str
    sources: list[AssistantSourceResponse]
    context: AssistantContextResponse
    data: dict[str, Any] | None = None


class AssistantQueryContext(BaseModel):
    currentPage: str | None = Field(default=None, max_length=80)
    playerId: int | None = None
    teamId: int | None = None


class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    season: str | None = Field(default=None, pattern=r"^20\d{2}-\d{2}$")
    context: AssistantQueryContext | None = None


class AssistantQueryResponse(BaseModel):
    answer: str
    intent: str
    season: str
    evidence: list[dict[str, Any]]
    requiresClarification: bool


class PredictionLogItemResponse(BaseModel):
    id: int
    created_at: str
    target_season: str
    prediction_type: str
    model_version: str
    notes: str | None
    payload: dict[str, Any]


class PredictionLogResponse(BaseModel):
    disclaimer: str
    predictions: list[PredictionLogItemResponse]
