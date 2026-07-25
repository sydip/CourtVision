from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.main import create_app
from app.models import Game, Player, PlayerGameStat, PlayerSeasonSummary, Team


def test_reference_routes_return_stored_dimensions(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    assert client.get("/api/seasons").json() == {"seasons": ["2025-26"]}

    teams_response = client.get("/api/teams")
    assert teams_response.status_code == 200
    assert [team["abbreviation"] for team in teams_response.json()["teams"]] == ["GSW", "LAL"]

    positions_response = client.get("/api/positions")
    assert positions_response.status_code == 200
    assert positions_response.json() == {"positions": ["F", "G"]}


def test_player_search_is_case_insensitive_and_paginated(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get("/api/players", params={"q": "CURR", "limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {
        "limit": 1,
        "offset": 0,
        "total": 1,
        "next_offset": None,
        "previous_offset": None,
    }
    assert body["items"][0]["full_name"] == "Stephen Curry"
    assert body["items"][0]["team"]["abbreviation"] == "GSW"


def test_player_detail_and_missing_player_error(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get("/api/players/201939")

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Stephen Curry"
    assert body["height"] == "6-2"
    assert body["jersey_number"] == "30"

    missing_response = client.get("/api/players/999999999")
    assert missing_response.status_code == 404
    assert missing_response.json()["error"]["code"] == "not_found"


def test_player_summary_trends_splits_and_benchmarks(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    summary_response = client.get("/api/players/201939/seasons/2025-26/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["games_played"] == 2
    assert summary["points_per_game"] == 27.0
    assert summary["true_shooting_source"] == "calculated"
    assert summary["analytics_warnings"] == [{"code": "small_sample", "message": "2 games"}]

    trends_response = client.get("/api/players/201939/seasons/2025-26/trends")
    assert trends_response.status_code == 200
    trends = trends_response.json()
    assert trends["production_trend"] == "stable"
    assert trends["payload"]["production"]["recent_5_average"] == 27.0

    splits_response = client.get("/api/players/201939/seasons/2025-26/splits")
    assert splits_response.status_code == 200
    splits = splits_response.json()
    assert splits["home"]["games"] == 1
    assert splits["away"]["games"] == 1

    benchmarks_response = client.get("/api/players/201939/seasons/2025-26/benchmarks")
    assert benchmarks_response.status_code == 200
    benchmarks = benchmarks_response.json()
    assert benchmarks["league_percentiles"]["points_per_game"] == 87.0
    assert benchmarks["position_percentiles"]["assists_per_game"] == 92.0
    assert benchmarks["minutes_tier_percentiles"]["true_shooting_percentage"] == 71.0


def test_season_summaries_returns_every_player_in_one_call(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get("/api/seasons/2025-26/summaries")

    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["nba_player_id"] for item in items} == {201939, 2544}
    curry_summary = next(item for item in items if item["nba_player_id"] == 201939)
    assert curry_summary["points_per_game"] == 27.0
    assert curry_summary["games_played"] == 2


def test_similar_players_route_uses_stored_season_summaries(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get(
        "/api/players/201939/seasons/2025-26/similar",
        params={"limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["player_id"] == 1
    assert body["season"] == "2025-26"
    assert len(body["players"]) == 1
    similar = body["players"][0]
    assert similar["player"]["full_name"] == "LeBron James"
    assert similar["summary"]["points_per_game"] == 26.0
    assert 0 <= similar["similarity_score"] <= 100
    assert similar["minutes_difference"] == 0.0


def test_player_games_filters_sorting_and_pagination(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get(
        "/api/players/201939/seasons/2025-26/games",
        params={
            "location": "away",
            "opponent": "LAL",
            "result": "L",
            "sort": "desc",
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["location"] == "away"
    assert body["items"][0]["opponent"]["abbreviation"] == "LAL"
    assert body["items"][0]["result"] == "L"
    assert body["items"][0]["calculated_true_shooting_percentage"] is not None

    paged_response = client.get(
        "/api/players/201939/seasons/2025-26/games",
        params={"limit": 1, "offset": 1},
    )
    assert paged_response.status_code == 200
    paged = paged_response.json()
    assert paged["meta"]["previous_offset"] == 0
    assert paged["items"][0]["game_date"] == "2025-10-23"


def test_compare_route_and_validation_errors(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get(
        "/api/compare",
        params={"season": "2025-26", "player_a": "201939", "player_b": "2544"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["season"] == "2025-26"
    assert body["player_a"]["player"]["full_name"] == "Stephen Curry"
    assert body["player_b"]["player"]["full_name"] == "LeBron James"
    assert body["position_match"] is False
    assert "position percentile comparisons" in body["position_context"]
    assert body["player_a"]["recent_5"]["points"] == 27.0
    assert body["player_a"]["rest_splits"]["one_day_rest"]["games"] == 1
    assert body["player_a"]["rolling_trend"][0]["points_rolling_5"] == 30.0
    points_winner = next(
        item for item in body["category_winners"] if item["key"] == "points_per_game"
    )
    assert points_winner["winner"] == "player_a"

    validation_response = client.get(
        "/api/players/201939/seasons/2025-26/games",
        params={"limit": 0},
    )
    assert validation_response.status_code == 422
    assert validation_response.json()["error"]["code"] == "validation_error"

    same_player_response = client.get(
        "/api/compare",
        params={"season": "2025-26", "player_a": "201939", "player_b": "201939"},
    )
    assert same_player_response.status_code == 422
    assert same_player_response.json()["error"]["code"] == "validation_error"


def test_deterministic_player_report_uses_structured_fields(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get("/api/players/201939/seasons/2025-26/report")

    assert response.status_code == 200
    body = response.json()
    assert body["player"]["full_name"] == "Stephen Curry"
    assert body["summary"]["points_per_game"] == 27.0
    assert body["sample_size_warnings"] == [{"code": "small_sample", "message": "2 games"}]
    sections = {section["key"]: section for section in body["sections"]}
    assert "season_overview" in sections
    assert "efficiency" in sections
    overview_sentence = sections["season_overview"]["sentences"][0]
    assert "Stephen Curry has played 2 games" in overview_sentence["text"]
    assert "summary.points_per_game" in overview_sentence["fields"]
    efficiency_sentence = sections["efficiency"]["sentences"][0]
    assert "62.5%" in efficiency_sentence["text"]
    assert "summary.true_shooting_percentage" in efficiency_sentence["fields"]


def test_openapi_includes_application_routes(db_session: Session) -> None:
    _seed_application_data(db_session)
    client = _client(db_session)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/players" in paths
    assert "/api/players/{player_id}/seasons/{season}/games" in paths
    assert "/api/players/{player_id}/seasons/{season}/similar" in paths
    assert "/api/players/{player_id}/seasons/{season}/report" in paths
    assert "/api/compare" in paths


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)


def _seed_application_data(db_session: Session) -> dict[str, Any]:
    warriors = Team(
        nba_team_id=1610612744,
        abbreviation="GSW",
        city="Golden State",
        name="Warriors",
        conference="West",
        division="Pacific",
    )
    lakers = Team(
        nba_team_id=1610612747,
        abbreviation="LAL",
        city="Los Angeles",
        name="Lakers",
        conference="West",
        division="Pacific",
    )
    curry = Player(
        nba_player_id=201939,
        slug="stephen-curry-201939",
        full_name="Stephen Curry",
        first_name="Stephen",
        last_name="Curry",
        position="G",
        jersey_number="30",
        height="6-2",
        weight_pounds=185,
        birthdate=date(1988, 3, 14),
        team=warriors,
    )
    lebron = Player(
        nba_player_id=2544,
        slug="lebron-james-2544",
        full_name="LeBron James",
        first_name="LeBron",
        last_name="James",
        position="F",
        height="6-9",
        weight_pounds=250,
        birthdate=date(1984, 12, 30),
        team=lakers,
    )
    opening_night = Game(
        nba_game_id="0022500001",
        season="2025-26",
        game_date=date(2025, 10, 21),
        home_team=warriors,
        away_team=lakers,
        home_score=120,
        away_score=112,
    )
    rematch = Game(
        nba_game_id="0022500002",
        season="2025-26",
        game_date=date(2025, 10, 23),
        home_team=lakers,
        away_team=warriors,
        home_score=109,
        away_score=104,
    )
    db_session.add_all(
        [
            warriors,
            lakers,
            curry,
            lebron,
            opening_night,
            rematch,
            PlayerGameStat(
                player=curry,
                game=opening_night,
                team=warriors,
                season="2025-26",
                matchup="GSW vs. LAL",
                is_home=True,
                result="W",
                minutes=Decimal("32.50"),
                points=30,
                rebounds=4,
                assists=7,
                steals=2,
                turnovers=3,
                field_goals_made=10,
                field_goals_attempted=20,
                three_pointers_made=5,
                three_pointers_attempted=11,
                free_throws_made=5,
                free_throws_attempted=5,
                plus_minus=Decimal("8.00"),
            ),
            PlayerGameStat(
                player=curry,
                game=rematch,
                team=warriors,
                season="2025-26",
                matchup="GSW @ LAL",
                is_home=False,
                result="L",
                days_since_previous_game=2,
                minutes=Decimal("34.00"),
                points=24,
                rebounds=5,
                assists=6,
                steals=1,
                turnovers=2,
                field_goals_made=8,
                field_goals_attempted=18,
                three_pointers_made=4,
                three_pointers_attempted=10,
                free_throws_made=4,
                free_throws_attempted=4,
                plus_minus=Decimal("-5.00"),
            ),
            PlayerGameStat(
                player=lebron,
                game=opening_night,
                team=lakers,
                season="2025-26",
                matchup="LAL @ GSW",
                is_home=False,
                result="L",
                minutes=Decimal("35.00"),
                points=26,
                rebounds=8,
                assists=9,
                turnovers=4,
                field_goals_made=9,
                field_goals_attempted=19,
                free_throws_made=8,
                free_throws_attempted=10,
            ),
            _summary(curry, warriors),
            _summary(
                lebron,
                lakers,
                points_per_game=Decimal("26.00"),
                rebounds_per_game=Decimal("8.00"),
                assists_per_game=Decimal("9.00"),
            ),
        ]
    )
    db_session.commit()
    return {"curry": curry, "lebron": lebron}


def _summary(
    player: Player,
    team: Team,
    *,
    points_per_game: Decimal = Decimal("27.00"),
    rebounds_per_game: Decimal = Decimal("4.50"),
    assists_per_game: Decimal = Decimal("6.50"),
) -> PlayerSeasonSummary:
    return PlayerSeasonSummary(
        player=player,
        team=team,
        season="2025-26",
        games_played=2,
        minutes_per_game=Decimal("33.25"),
        points_per_game=points_per_game,
        rebounds_per_game=rebounds_per_game,
        assists_per_game=assists_per_game,
        turnovers_per_game=Decimal("2.50"),
        plus_minus_per_game=Decimal("1.50"),
        true_shooting_percentage=Decimal("0.625"),
        true_shooting_source="calculated",
        usage_rate=Decimal("0.290"),
        points_per_36=Decimal("29.25"),
        rebounds_per_36=Decimal("4.87"),
        assists_per_36=Decimal("7.04"),
        turnovers_per_36=Decimal("2.71"),
        league_percentiles={"points_per_game": 87.0},
        position_percentiles={"assists_per_game": 92.0},
        minutes_tier_percentiles={"true_shooting_percentage": 71.0},
        production_trend="stable",
        production_trend_value=Decimal("0.1000"),
        efficiency_trend="stable",
        efficiency_trend_value=Decimal("-0.0500"),
        trend_payload={"production": {"recent_5_average": 27.0}},
        analytics_warnings=[{"code": "small_sample", "message": "2 games"}],
        analytics_rebuilt_at=datetime(2026, 6, 30, tzinfo=UTC),
    )
