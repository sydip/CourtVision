from __future__ import annotations

from typing import Protocol

from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceTeam,
)


class BasketballDataProvider(Protocol):
    def get_teams(self) -> list[SourceTeam]: ...

    def get_players(self) -> list[SourcePlayer]: ...

    def get_player_profiles(self) -> list[SourcePlayerProfile]: ...

    def get_games(self) -> list[SourceGame]: ...

    def get_season_game_logs(self, season: str) -> list[SourcePlayerGameLog]: ...

    def get_league_player_statistics(self, season: str) -> list[SourceLeaguePlayerStatistic]: ...
