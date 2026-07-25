from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.models import Team


def team_count(session: Session, nba_team_id: int | None = None) -> int:
    statement = select(func.count()).select_from(Team)
    if nba_team_id is not None:
        statement = statement.where(Team.nba_team_id == nba_team_id)
    return session.scalar(statement) or 0


def test_session_scope_commits_and_rolls_back(session_factory: sessionmaker[Session]) -> None:
    with session_scope(session_factory) as session:
        session.add(
            Team(
                nba_team_id=1610612744,
                abbreviation="GSW",
                city="San Francisco",
                name="Warriors",
            )
        )

    with session_factory() as session:
        assert team_count(session, 1610612744) == 1

    with pytest.raises(RuntimeError, match="rollback"):
        with session_scope(session_factory) as session:
            session.add(
                Team(
                    nba_team_id=1610612750,
                    abbreviation="MIN",
                    city="Minneapolis",
                    name="Timberwolves",
                )
            )
            raise RuntimeError("force rollback")

    with session_factory() as session:
        assert team_count(session, 1610612750) == 0
        assert team_count(session) == 1
