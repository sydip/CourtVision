from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AwardHistory, PlayoffSeries, TeamSeasonSummary
from app.predictions.features import (
    ALL_NBA_FEATURES,
    FINALS_FEATURES,
    STANDINGS_FEATURES,
    FeatureRow,
    all_nba_rows,
    finals_rows,
    projected_active_player_ids,
    standings_rows,
)
from app.predictions.guardrails import (
    PREDICTION_SEASON,
    TRAINING_SEASONS,
    require_prediction_season,
    require_target,
)


@dataclass(frozen=True)
class PredictionDataset:
    target: str
    feature_names: tuple[str, ...]
    rows: list[FeatureRow]
    labels: list[int]
    training_seasons: tuple[str, ...]

    def matrix(self) -> list[list[float | None]]:
        return [[row.values.get(name) for name in self.feature_names] for row in self.rows]

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "feature_names": list(self.feature_names),
            "training_seasons": list(self.training_seasons),
            "rows": [
                {**asdict(row), "label": label}
                for row, label in zip(self.rows, self.labels, strict=True)
            ],
        }


def build_dataset(
    session: Session, target: str, seasons: tuple[str, ...] = TRAINING_SEASONS
) -> PredictionDataset:
    require_target(target)
    rows: list[FeatureRow] = []
    labels: list[int] = []
    feature_names: tuple[str, ...]
    for season in seasons:
        if target == "all_nba":
            season_rows = all_nba_rows(session, season)
            winners = set(
                session.scalars(
                    select(AwardHistory.player_id).where(
                        AwardHistory.season == season, AwardHistory.award_type.like("ALL_NBA%")
                    )
                )
            )
            feature_names = ALL_NBA_FEATURES
            season_labels = [int(row.entity_id in winners) for row in season_rows]
        elif target == "standings":
            season_rows = standings_rows(session, season)
            results = {
                row.team_id: (row.wins or 0)
                for row in session.scalars(
                    select(TeamSeasonSummary).where(TeamSeasonSummary.season == season)
                )
            }
            feature_names = STANDINGS_FEATURES
            season_labels = [int(results.get(row.entity_id, 0) >= 40) for row in season_rows]
        else:
            season_rows = finals_rows(session, season)
            champions = set(
                session.scalars(
                    select(PlayoffSeries.winner_team_id).where(
                        PlayoffSeries.season == season,
                        func.lower(PlayoffSeries.round_name).in_(("nba finals", "finals", "final")),
                    )
                )
            )
            feature_names = FINALS_FEATURES
            season_labels = [int(row.entity_id in champions) for row in season_rows]
        rows.extend(season_rows)
        labels.extend(season_labels)
    return PredictionDataset(target, feature_names, rows, labels, seasons)


def assert_no_future_leakage(dataset: PredictionDataset) -> None:
    for row in dataset.rows:
        if row.feature_season > row.label_season or row.feature_season == "2026-27":
            raise ValueError(
                f"Feature leakage detected for {row.entity_name} in {row.label_season}."
            )


def build_inference_rows(
    session: Session, target: str, season: str = PREDICTION_SEASON
) -> list[FeatureRow]:
    require_target(target)
    require_prediction_season(season)
    if target == "all_nba":
        active = projected_active_player_ids(session)
        return [row for row in all_nba_rows(session, season, "2025-26") if row.entity_id in active]
    if target == "standings":
        return standings_rows(session, season, "2025-26")
    return finals_rows(session, season, "2025-26")
