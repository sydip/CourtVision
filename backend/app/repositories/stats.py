from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlayerGameStat


class PlayerGameStatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, stat: PlayerGameStat) -> PlayerGameStat:
        self.session.add(stat)
        return stat

    def get_for_player_game(self, player_id: int, game_id: int) -> PlayerGameStat | None:
        statement = select(PlayerGameStat).where(
            PlayerGameStat.player_id == player_id,
            PlayerGameStat.game_id == game_id,
        )
        return self.session.scalar(statement)

    def list_for_player_season(self, player_id: int, season: str) -> list[PlayerGameStat]:
        statement = (
            select(PlayerGameStat)
            .where(
                PlayerGameStat.player_id == player_id,
                PlayerGameStat.season == season,
            )
            .order_by(PlayerGameStat.game_id)
        )
        return list(self.session.scalars(statement))
