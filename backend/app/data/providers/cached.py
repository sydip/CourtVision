from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.data.providers.base import BasketballDataProvider
from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceTeam,
)

SourceModel = TypeVar("SourceModel", bound=BaseModel)


class CachedResponseProvider:
    def __init__(self, wrapped_provider: BasketballDataProvider, cache_dir: Path | str) -> None:
        self.wrapped_provider = wrapped_provider
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_teams(self) -> list[SourceTeam]:
        return self._cached("teams", self.wrapped_provider.get_teams, SourceTeam)

    def get_players(self) -> list[SourcePlayer]:
        return self._cached("players", self.wrapped_provider.get_players, SourcePlayer)

    def get_player_profiles(self) -> list[SourcePlayerProfile]:
        return self._cached(
            "player_profiles",
            self.wrapped_provider.get_player_profiles,
            SourcePlayerProfile,
        )

    def get_games(self) -> list[SourceGame]:
        return self._cached("games", self.wrapped_provider.get_games, SourceGame)

    def get_season_game_logs(self, season: str) -> list[SourcePlayerGameLog]:
        return self._cached(
            f"{season}_player_game_logs",
            lambda: self.wrapped_provider.get_season_game_logs(season),
            SourcePlayerGameLog,
        )

    def get_league_player_statistics(self, season: str) -> list[SourceLeaguePlayerStatistic]:
        return self._cached(
            f"{season}_league_player_statistics",
            lambda: self.wrapped_provider.get_league_player_statistics(season),
            SourceLeaguePlayerStatistic,
        )

    def _cached(
        self,
        cache_key: str,
        loader: Callable[[], list[SourceModel]],
        schema: type[SourceModel],
    ) -> list[SourceModel]:
        cache_path = self.cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
            if not isinstance(cached_data, list):
                raise ValueError(f"{cache_path} must contain a JSON array.")
            return [schema.model_validate(item) for item in cached_data]

        records = loader()
        cache_path.write_text(
            json.dumps([record.model_dump(mode="json") for record in records], indent=2),
            encoding="utf-8",
        )
        return records
