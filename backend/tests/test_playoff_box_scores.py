from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.ingestion.playoff_box_scores import (
    EXPECTED_FIRST_ROUND_GAMES,
    ParsedSeries,
    ingest_playoff_box_scores,
    parse_playoff_box_scores,
)
from app.main import create_app
from app.models import (
    Player,
    PlayoffGame,
    PlayoffPlayerBoxScore,
    PlayoffSeries,
    PlayoffTeamBoxScore,
    Team,
)


def test_supplied_playoff_fixture_parses_complete_available_content() -> None:
    series = parse_playoff_box_scores()

    assert len(series) == 6
    assert sum(len(item.games) for item in series) == 36
    assert sum(len(game.team_boxes) for item in series for game in item.games) == 72
    assert (
        sum(
            len(box.players)
            for item in series
            for game in item.games
            for box in game.team_boxes.values()
        )
        == 774
    )
    detroit_game_one = series[0].games[0]
    assert detroit_game_one.scores == {"DET": 101, "ORL": 112}
    assert detroit_game_one.team_boxes["DET"].players[0].name == "Cade Cunningham"
    assert detroit_game_one.team_boxes["DET"].players[0].points == 39
    assert EXPECTED_FIRST_ROUND_GAMES == 48


def test_playoff_ingestion_is_idempotent_and_api_reports_source_coverage(
    db_session: Session,
) -> None:
    parsed = parse_playoff_box_scores()
    teams = _add_teams(db_session, parsed)
    cade = Player(
        nba_player_id=2,
        slug="cade-cunningham",
        full_name="Cade Cunningham",
        first_name="Cade",
        last_name="Cunningham",
        team_id=teams["DET"].id,
        active=True,
    )
    db_session.add(cade)
    db_session.flush()

    first = ingest_playoff_box_scores(db_session)
    db_session.commit()
    second = ingest_playoff_box_scores(db_session)
    db_session.commit()

    assert first == {
        "series": 6,
        "games": 36,
        "team_box_scores": 72,
        "player_box_scores": 774,
        "inserted": 888,
        "updated": 0,
    }
    assert second["inserted"] == 0
    assert second["updated"] == 888
    assert db_session.scalar(select(func.count()).select_from(PlayoffSeries)) == 6
    assert db_session.scalar(select(func.count()).select_from(PlayoffGame)) == 36
    assert db_session.scalar(select(func.count()).select_from(PlayoffTeamBoxScore)) == 72
    assert db_session.scalar(select(func.count()).select_from(PlayoffPlayerBoxScore)) == 774
    assert db_session.scalar(
        select(PlayoffPlayerBoxScore.player_id).where(
            PlayoffPlayerBoxScore.player_name == "Cade Cunningham"
        )
    ) == cade.id

    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    response = TestClient(app).get("/api/playoffs/2025-26/rounds/first-round")

    assert response.status_code == 200
    body = response.json()
    assert body["stored_series"] == 6
    assert body["stored_games"] == 36
    assert body["expected_games"] == 48
    assert body["coverage_complete"] is False
    assert body["series"][0]["conference"] == "East"
    first_game = body["series"][0]["games"][0]
    detroit = next(
        item for item in first_game["team_box_scores"] if item["team"]["abbreviation"] == "DET"
    )
    assert detroit["field_goals_made"] == 31
    assert detroit["players"][0]["player_name"] == "Cade Cunningham"
    assert detroit["players"][0]["points"] == 39


def _add_teams(session: Session, parsed: list[ParsedSeries]) -> dict[str, Team]:
    abbreviations = sorted(
        {
            abbreviation
            for playoff_series in parsed
            for game in playoff_series.games
            for abbreviation in (game.home_team, game.away_team)
        }
    )
    teams = {
        abbreviation: Team(
            nba_team_id=1_610_610_000 + index,
            abbreviation=abbreviation,
            city=f"City {abbreviation}",
            name=f"Team {abbreviation}",
            conference="East" if index % 2 else "West",
            division="Test",
        )
        for index, abbreviation in enumerate(abbreviations, start=1)
    }
    session.add_all(teams.values())
    session.flush()
    return teams
