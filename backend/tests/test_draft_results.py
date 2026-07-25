from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.ingestion.draft_results import DRAFT_RESULTS, ingest_2026_draft_results
from app.main import create_app
from app.models import DraftPick, Team


def test_draft_ingestion_is_complete_and_idempotent(db_session: Session) -> None:
    _add_draft_teams(db_session)

    first = ingest_2026_draft_results(db_session)
    db_session.commit()
    second = ingest_2026_draft_results(db_session)
    db_session.commit()

    assert first == {"fetched": 60, "inserted": 60, "updated": 0}
    assert second == {"fetched": 60, "inserted": 0, "updated": 60}
    assert db_session.scalar(select(func.count()).select_from(DraftPick)) == 60
    assert db_session.scalar(
        select(DraftPick.player_name).where(DraftPick.overall_pick == 1)
    ) == "AJ Dybantsa"
    assert db_session.scalar(
        select(DraftPick.player_name).where(DraftPick.overall_pick == 60)
    ) == "Malique Lewis"


def test_draft_api_returns_rounds_and_final_destination_teams(
    db_session: Session,
) -> None:
    _add_draft_teams(db_session)
    ingest_2026_draft_results(db_session)
    db_session.commit()
    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.get("/api/drafts/2026")
    assert response.status_code == 200
    body = response.json()
    assert body["total_picks"] == 60
    assert body["picks"][0]["player_name"] == "AJ Dybantsa"
    assert body["picks"][0]["team"]["abbreviation"] == "WAS"
    assert body["picks"][12]["transaction_note"] == "traded from Miami"

    second_round = client.get("/api/drafts/2026?round=2")
    assert second_round.status_code == 200
    assert second_round.json()["total_picks"] == 30
    assert second_round.json()["picks"][0]["overall_pick"] == 31


def _add_draft_teams(session: Session) -> None:
    abbreviations = sorted({record.team_abbreviation for record in DRAFT_RESULTS})
    session.add_all(
        [
            Team(
                nba_team_id=1_610_610_000 + index,
                abbreviation=abbreviation,
                city=f"City {abbreviation}",
                name=f"Team {abbreviation}",
                conference="East" if index % 2 else "West",
                division="Test",
            )
            for index, abbreviation in enumerate(abbreviations, start=1)
        ]
    )
    session.flush()
