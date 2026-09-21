from __future__ import annotations

PREDICTION_SEASON = "2026-27"
TRAINING_SEASONS = ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26")
TARGETS = ("all_nba", "standings", "finals_winner")


def require_prediction_season(season: str) -> None:
    if season != PREDICTION_SEASON:
        raise ValueError("Prediction capabilities are only available for the 2026-27 season.")


def require_target(target: str) -> None:
    if target not in TARGETS:
        raise ValueError(f"Unsupported prediction target '{target}'.")
