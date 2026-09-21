from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import (
    AwardHistory,
    Player,
    PlayerSeasonSummary,
    RosterMembership,
    Team,
    TeamSeasonSummary,
)
from app.predictions.datasets import (
    PredictionDataset,
    assert_no_future_leakage,
    build_dataset,
    build_inference_rows,
)
from app.predictions.features import (
    ALL_NBA_FEATURES,
    FINALS_FEATURES,
    STANDINGS_FEATURES,
    FeatureRow,
)
from app.predictions.guardrails import require_prediction_season
from app.predictions.inference import infer_all_nba, infer_finals, infer_standings
from app.predictions.training import train_model


def test_feature_dataset_uses_stored_labels_and_filters_projected_roster(
    db_session: Session,
) -> None:
    team = Team(nba_team_id=1, abbreviation="BOS", city="Boston", name="Celtics", conference="East")
    selected = Player(nba_player_id=1, slug="selected", full_name="Selected Player", team=team)
    other = Player(nba_player_id=2, slug="other", full_name="Other Player", team=team)
    db_session.add_all([team, selected, other])
    db_session.flush()
    db_session.add(
        TeamSeasonSummary(
            team=team,
            season="2025-26",
            wins=55,
            losses=27,
            win_pct=Decimal("0.671"),
            conference_rank=1,
            data_source="fixture",
        )
    )
    for player, points in ((selected, 28), (other, 15)):
        db_session.add(
            PlayerSeasonSummary(
                player=player,
                team=team,
                season="2025-26",
                games_played=70,
                minutes_per_game=Decimal("32"),
                points_per_game=Decimal(points),
                rebounds_per_game=Decimal("6"),
                assists_per_game=Decimal("5"),
            )
        )
    db_session.add(
        AwardHistory(
            season="2025-26",
            award_type="ALL_NBA_1",
            player_id=selected.id,
            team_id=team.id,
            data_source="fixture",
        )
    )
    db_session.add(
        RosterMembership(
            player=selected,
            team=team,
            season="2026-27",
            roster_status="active",
            is_projected_starter=True,
            source="fixture",
        )
    )
    db_session.commit()

    dataset = build_dataset(db_session, "all_nba", ("2025-26",))
    assert dataset.labels == [1, 0]
    assert dataset.feature_names == ALL_NBA_FEATURES
    assert_no_future_leakage(dataset)
    inference = build_inference_rows(db_session, "all_nba")
    assert [row.entity_name for row in inference] == ["Selected Player"]
    assert all(
        row.feature_season == "2025-26" and row.label_season == "2026-27" for row in inference
    )


def test_leakage_and_season_guardrails() -> None:
    leaked = PredictionDataset(
        "all_nba",
        ("x",),
        [FeatureRow(1, "Player", "2026-27", "2025-26", {"x": 1.0})],
        [1],
        ("2025-26",),
    )
    with pytest.raises(ValueError, match="leakage"):
        assert_no_future_leakage(leaked)
    with pytest.raises(ValueError, match="only available"):
        require_prediction_season("2025-26")


@pytest.mark.parametrize(
    "target,features",
    [
        ("all_nba", ALL_NBA_FEATURES),
        ("standings", STANDINGS_FEATURES),
        ("finals_winner", FINALS_FEATURES),
    ],
)
def test_logistic_training_and_inference_shapes(target: str, features: tuple[str, ...]) -> None:
    rows = [_row(index, features, positive=index % 2 == 0) for index in range(8)]
    labels = [int(index % 2 == 0) for index in range(8)]
    bundle = train_model(PredictionDataset(target, features, rows, labels, ("2021-22", "2022-23")))
    if target == "all_nba":
        result = infer_all_nba(bundle, rows[:3], "2026-27")
        assert result[0].keys() >= {"probability", "predicted_rank", "top_features", "warnings"}
    elif target == "standings":
        result = infer_standings(bundle, rows[:3], "2026-27")
        assert result[0].keys() >= {
            "predicted_wins",
            "predicted_losses",
            "playoff_probability",
            "confidence",
        }
    else:
        result = infer_finals(bundle, rows[:3], "2026-27")
        assert result["predicted_champion"] is not None
        assert result["label"] == "Model estimate"


def _row(index: int, features: tuple[str, ...], positive: bool) -> FeatureRow:
    base = 2.0 if positive else -2.0
    values = {name: base + index * 0.01 + offset * 0.001 for offset, name in enumerate(features)}
    return FeatureRow(index + 1, f"Entity {index}", "2025-26", "2026-27", values)
