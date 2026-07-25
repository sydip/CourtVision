from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Player


class PlayerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, player: Player) -> Player:
        self.session.add(player)
        return player

    def get_by_slug(self, slug: str) -> Player | None:
        return self.session.scalar(select(Player).where(Player.slug == slug))

    def get_by_nba_player_id(self, nba_player_id: int) -> Player | None:
        return self.session.scalar(select(Player).where(Player.nba_player_id == nba_player_id))

    def search_by_full_name(self, query: str, limit: int = 20) -> list[Player]:
        statement = (
            select(Player)
            .where(Player.full_name.ilike(f"%{query}%"))
            .order_by(Player.full_name)
            .limit(limit)
        )
        return list(self.session.scalars(statement))
