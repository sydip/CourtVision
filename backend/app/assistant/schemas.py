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


class PredictionLogItemResponse(BaseModel):
    id: int
    created_at: str
    target_season: str
    prediction_type: str
    model_version: str
    notes: str | None
    payload: dict[str, Any]


class PredictionLogResponse(BaseModel):
    predictions: list[PredictionLogItemResponse]
