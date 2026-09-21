from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.awards_predictor import predict_awards
from app.analytics.standings_predictor import predict_standings
from app.assistant.tools import execute_tool
from app.db.session import get_db_session
from app.main import create_app
from app.models import Player, PlayerSeasonSummary, PredictionResult, PredictionRun, Team


def test_prediction_availability_and_season_gating(db_session: Session) -> None:
    client = _client(db_session)
    response = client.get("/api/predictions/availability")
    assert response.status_code == 200
    assert response.json()["predictionSeason"] == "2026-27"
    assert response.json()["supportedPredictionTypes"] == [
        "all_nba",
        "standings",
        "finals_winner",
    ]

    for season in ("2025-26", "2024-25"):
        blocked = client.get(f"/api/predictions/{season}/all-nba")
        assert blocked.status_code == 403
        assert blocked.json()["error"]["message"] == (
            "Prediction capabilities are only available for the 2026-27 season."
        )
        blocked_run = client.post(
            f"/api/predictions/{season}/run", json={"predictionType": "all_nba"}
        )
        assert blocked_run.status_code == 403


def test_legacy_predictor_functions_reject_non_jordan_seasons(
    db_session: Session,
) -> None:
    for season in ("2024-25", "2026-27"):
        with pytest.raises(ValueError, match="only available for the 2025-26 season"):
            predict_awards(db_session, season, "MVP", persist=False)
        with pytest.raises(ValueError, match="only available for the 2025-26 season"):
            predict_standings(db_session, season, persist=False)

    with pytest.raises(ValueError, match="only available for the 2025-26 season"):
        predict_awards(
            db_session,
            "2024-25",
            "MVP",
            persist=True,
            _historical_backtest=True,
        )


def test_prediction_result_endpoints_and_run_lookup(db_session: Session) -> None:
    runs = _seed_prediction_runs(db_session)
    client = _client(db_session)

    all_nba = client.get("/api/predictions/2026-27/all-nba")
    assert all_nba.status_code == 200
    assert all_nba.json()["data"][0]["playerName"] == "Example Player"
    assert all_nba.json()["data"][0]["projectedTeam"] == "First Team"
    assert "Experimental model estimate" in all_nba.json()["disclaimer"]

    standings = client.get("/api/predictions/2026-27/standings")
    assert standings.status_code == 200
    assert standings.json()["east"][0]["predictedWins"] == 56
    assert standings.json()["west"] == []
    assert "betting recommendation" in standings.json()["disclaimer"]

    finals = client.get("/api/predictions/2026-27/finals-winner")
    assert finals.status_code == 200
    assert finals.json()["predictedChampion"]["teamName"] == "Boston Celtics"
    assert "betting recommendation" in finals.json()["disclaimer"]

    run = client.get(f"/api/predictions/runs/{runs['all_nba'].id}")
    assert run.status_code == 200
    assert run.json()["resultCount"] == 1


def test_assistant_prediction_routing_blocking_and_jordan_isolation(db_session: Session) -> None:
    _seed_prediction_runs(db_session)
    client = _client(db_session)

    answer = client.post(
        "/api/assistant/query",
        json={"question": "Who is the predicted 2026-27 NBA Finals winner?", "season": "2026-27"},
    )
    assert answer.status_code == 200
    assert "Boston Celtics" in answer.json()["answer"]
    assert answer.json()["intent"] == "prediction_lookup"
    assert answer.json()["evidence"][0]["source"] == "prediction_model"
    assert "not an official prediction or betting recommendation" in answer.json()["answer"]

    blocked = client.post(
        "/api/assistant/query",
        json={"question": "Predict the 2024-25 Finals winner.", "season": "2024-25"},
    )
    assert blocked.json()["answer"] == (
        "Prediction capabilities are only available for the 2026-27 season. "
        "Historical seasons can be analyzed, but not predicted."
    )

    alternate_wording = client.post(
        "/api/assistant/query",
        json={"question": "Who is the model favorite in 2024-25?", "season": "2024-25"},
    )
    assert alternate_wording.json()["intent"] == "unsupported_request"
    assert alternate_wording.json()["evidence"] == []

    betting = client.post(
        "/api/assistant/query",
        json={"question": "What team should I bet on?", "season": "2026-27"},
    )
    assert betting.json()["answer"] == "CourtVision does not provide betting advice."

    jordan = client.get("/api/predictions/awards/MVP?season=2026-27")
    assert jordan.status_code == 403
    assert "Jordan prediction mode" in jordan.json()["error"]["message"]

    jordan_allowed = client.get("/api/predictions/awards/MVP?season=2025-26")
    assert jordan_allowed.status_code == 200
    assert jordan_allowed.json()["target_season"] == "2025-26"
    assert "not a guaranteed outcome or betting recommendation" in jordan_allowed.json()[
        "disclaimer"
    ]

    try:
        execute_tool(
            db_session,
            "predict_award",
            {"award_type": "MVP", "season": "2024-25"},
        )
    except ValueError as exc:
        assert "Jordan prediction mode" in str(exc)
    else:
        raise AssertionError("Direct Jordan tool execution accepted an unsupported season.")

    jordan_chat = client.post(
        "/api/assistant/chat",
        json={"message": "Predict the 2026-27 MVP."},
    )
    assert jordan_chat.status_code == 200
    assert jordan_chat.json()["mode"] == "jordan-season-guard"

    historical_jordan_favorite = client.post(
        "/api/assistant/chat",
        json={"message": "Who is your MVP favorite for 2024-25?"},
    )
    assert historical_jordan_favorite.json()["mode"] == "jordan-season-guard"

    supported_jordan_chat = client.post(
        "/api/assistant/chat",
        json={"message": "Who is your MVP favorite for 2025-26?"},
    )
    assert supported_jordan_chat.status_code == 200
    assert supported_jordan_chat.json()["sources"][0]["tool"] == "predict_award"
    assert "not a guaranteed outcome or betting recommendation" in supported_jordan_chat.json()[
        "message"
    ]

    default_roy = client.post(
        "/api/assistant/chat",
        json={"message": "Who is your ROY favorite?"},
    )
    assert default_roy.status_code == 200
    assert default_roy.json()["sources"][0]["arguments"]["season"] == "2025-26"

    historical_standings = client.post(
        "/api/assistant/chat",
        json={"message": "Show the 2024-25 standings."},
    )
    assert historical_standings.status_code == 200
    assert all(
        source["tool"] != "predict_standings" for source in historical_standings.json()["sources"]
    )


def test_run_endpoint_returns_an_auditable_run(db_session: Session, monkeypatch) -> None:
    runs = _seed_prediction_runs(db_session)
    monkeypatch.setattr(
        "app.api.routes.predictions.run_prediction",
        lambda _session, _target, _season: runs["all_nba"],
    )
    response = _client(db_session).post(
        "/api/predictions/2026-27/run", json={"predictionType": "all_nba"}
    )
    assert response.status_code == 200
    assert response.json()["predictionType"] == "all_nba"
    assert response.json()["status"] == "completed"


def _seed_prediction_runs(db_session: Session) -> dict[str, PredictionRun]:
    team = Team(
        nba_team_id=1,
        abbreviation="BOS",
        city="Boston",
        name="Celtics",
        conference="East",
    )
    player = Player(
        nba_player_id=123,
        slug="example-player",
        full_name="Example Player",
        team=team,
    )
    db_session.add_all([team, player])
    db_session.flush()
    db_session.add(
        PlayerSeasonSummary(
            player_id=player.id,
            team_id=team.id,
            season="2025-26",
            games_played=70,
            minutes_per_game=Decimal("34.0"),
            points_per_game=Decimal("27.0"),
            rebounds_per_game=Decimal("7.0"),
            assists_per_game=Decimal("6.0"),
            turnovers_per_game=Decimal("3.0"),
            true_shooting_percentage=Decimal("0.610"),
            usage_rate=Decimal("0.280"),
            plus_minus_per_game=Decimal("5.0"),
            points_per_36=Decimal("28.6"),
            rebounds_per_36=Decimal("7.4"),
            assists_per_36=Decimal("6.4"),
        )
    )
    runs: dict[str, PredictionRun] = {}
    for target in ("all_nba", "standings", "finals_winner"):
        run = PredictionRun(
            season="2026-27",
            prediction_type=target,
            model_name=f"logistic_regression_{target}",
            model_version="0.1.0",
            training_seasons=["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"],
            feature_set_version="features-v1",
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db_session.add(run)
        db_session.flush()
        entity_id = player.id if target == "all_nba" else team.id
        explanation = {
            "top_features": [{"feature": "team_wins", "contribution": 0.8}],
            "warnings": [],
        }
        if target == "standings":
            explanation.update(
                {
                    "conference": "East",
                    "conference_rank": 1,
                    "predicted_wins": 56,
                    "predicted_losses": 26,
                    "playoff_probability": 0.91,
                    "confidence": 0.68,
                }
            )
        db_session.add(
            PredictionResult(
                prediction_run_id=run.id,
                season="2026-27",
                prediction_type=target,
                entity_type="player" if target == "all_nba" else "team",
                entity_id=entity_id,
                predicted_rank=1,
                predicted_label="First Team" if target == "all_nba" else None,
                probability=Decimal("0.72") if target == "all_nba" else Decimal("0.18"),
                score=Decimal("0.72"),
                explanation_json=explanation,
            )
        )
        runs[target] = run
    db_session.commit()
    return runs


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)
