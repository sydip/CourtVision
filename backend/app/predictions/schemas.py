from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class PredictionRunRequest(BaseModel):
    predictionType: Literal["all_nba", "standings", "finals_winner"]


class PredictionAvailabilityResponse(BaseModel):
    predictionSeason: str
    enabled: bool
    supportedPredictionTypes: list[str]
    blockedSeasons: list[str]
    message: str


class PredictionApiResponse(BaseModel):
    season: str
    predictionType: str
    model: dict[str, Any] | None = None
    data: list[dict[str, Any]] | None = None
    east: list[dict[str, Any]] | None = None
    west: list[dict[str, Any]] | None = None
    predictedChampion: dict[str, Any] | None = None
    contenders: list[dict[str, Any]] | None = None
    disclaimer: str


class PredictionRunResponse(BaseModel):
    runId: int
    season: str
    predictionType: str
    status: str
    modelName: str
    modelVersion: str
    trainingSeasons: list[str]
    createdAt: str
    completedAt: str | None
    errorMessage: str | None
    resultCount: int
