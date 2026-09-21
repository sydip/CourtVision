from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.assistant.intent_classifier import classify_intent
from app.assistant.query_parser import parse_query
from app.db.session import get_db_session
from app.main import create_app
from app.models import Game, Player, PlayerGameStat, PlayerSeasonSummary, Team


def test_intent_classification_and_query_parsing() -> None:
    question = "How many points did Devin Booker score on March 3, 2025?"
    assert classify_intent(question) == "player_game_stats_exact"
    parsed = parse_query(question, "2024-25")
    assert parsed.season == "2024-25"
    assert parsed.game_date == "2025-03-03"
    assert parsed.stat == "points"
    assert classify_intent("Predict the 2024-25 champion") == "unsupported_request"


def test_assistant_query_returns_exact_database_evidence(db_session: Session) -> None:
    suns = Team(nba_team_id=1, abbreviation="PHX", city="Phoenix", name="Suns")
    lakers = Team(nba_team_id=2, abbreviation="LAL", city="Los Angeles", name="Lakers")
    booker = Player(nba_player_id=201942, slug="devin-booker", full_name="Devin Booker", team=suns)
    game = Game(
        nba_game_id="game-1",
        season="2024-25",
        game_date=date(2025, 3, 3),
        home_team=suns,
        away_team=lakers,
    )
    db_session.add_all([suns, lakers, booker, game])
    db_session.flush()
    db_session.add(
        PlayerGameStat(
            player=booker, team=suns, game=game, season="2024-25", points=28, rebounds=5, assists=7
        )
    )
    db_session.commit()
    client = _client(db_session)

    response = client.post(
        "/api/assistant/query",
        json={
            "question": (
                "How many points did Devin Booker score against the Lakers on March 3, 2025?"
            ),
            "season": "2024-25",
            "context": {"currentPage": "player", "playerId": None, "teamId": None},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert (
        body["answer"]
        == "Devin Booker scored 28 points against the Los Angeles Lakers on March 3, 2025."
    )
    assert body["intent"] == "player_game_stats_exact"
    assert body["evidence"][0]["points"] == 28
    assert body["evidence"][0]["source"] == "database"


def test_assistant_respects_season_and_never_invents_missing_game(db_session: Session) -> None:
    team = Team(nba_team_id=3, abbreviation="DEN", city="Denver", name="Nuggets")
    player = Player(nba_player_id=203999, slug="nikola-jokic", full_name="Nikola Jokic", team=team)
    db_session.add_all([team, player])
    db_session.flush()
    db_session.add_all(
        [
            PlayerSeasonSummary(
                player=player,
                team=team,
                season="2021-22",
                games_played=74,
                points_per_game=27.1,
                true_shooting_percentage=0.661,
            ),
            PlayerSeasonSummary(
                player=player,
                team=team,
                season="2025-26",
                games_played=70,
                points_per_game=30.2,
                true_shooting_percentage=0.702,
            ),
        ]
    )
    db_session.commit()
    client = _client(db_session)

    season = client.post(
        "/api/assistant/query",
        json={
            "question": "What was Nikola Jokic's true shooting percentage in 2021-22?",
            "season": "2025-26",
        },
    ).json()
    assert season["season"] == "2021-22"
    assert season["evidence"][0]["trueShootingPercentage"] == 0.661
    missing = client.post(
        "/api/assistant/query",
        json={
            "question": "How many points did Nikola Jokic score on March 3, 2025?",
            "season": "2024-25",
        },
    ).json()
    assert missing["answer"] == "I do not have that game in the CourtVision database."
    assert missing["evidence"] == []


def test_prediction_and_ambiguous_player_guardrails(db_session: Session) -> None:
    db_session.add_all(
        [
            Player(nba_player_id=10, slug="jaylin-williams", full_name="Jaylin Williams"),
            Player(nba_player_id=11, slug="jalen-williams", full_name="Jalen Williams"),
        ]
    )
    db_session.commit()
    client = _client(db_session)
    prediction = client.post(
        "/api/assistant/query", json={"question": "Predict the champion", "season": "2025-26"}
    ).json()
    assert prediction["answer"] == (
        "Prediction capabilities are only available for the 2026-27 season. "
        "Historical seasons can be analyzed, but not predicted."
    )
    ambiguous = client.post(
        "/api/assistant/query", json={"question": "What did Williams average?", "season": "2025-26"}
    ).json()
    assert ambiguous["requiresClarification"] is True


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)
