from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceTeam,
)

SourceModel = TypeVar("SourceModel", bound=BaseModel)


class FixtureProvider:
    def __init__(self, fixture_root: Path | str | None = None, season: str = "2025-26") -> None:
        self.season = season
        self.fixture_root = (
            Path(fixture_root) if fixture_root else self.default_fixture_root(season)
        )

    @staticmethod
    def default_fixture_root(season: str) -> Path:
        backend_root = Path(__file__).resolve().parents[3]
        return backend_root / "fixtures" / season

    def get_teams(self) -> list[SourceTeam]:
        return self._load_many("teams.json", SourceTeam)

    def get_players(self) -> list[SourcePlayer]:
        return self._load_many("players.json", SourcePlayer)

    def get_player_profiles(self) -> list[SourcePlayerProfile]:
        return self._load_many("player_profiles.json", SourcePlayerProfile)

    def get_games(self) -> list[SourceGame]:
        return self._load_many("games.json", SourceGame)

    def get_season_game_logs(self, season: str) -> list[SourcePlayerGameLog]:
        self._ensure_supported_season(season)
        return self._load_many("player_game_logs.json", SourcePlayerGameLog)

    def get_league_player_statistics(self, season: str) -> list[SourceLeaguePlayerStatistic]:
        self._ensure_supported_season(season)
        return self._load_many("league_player_statistics.json", SourceLeaguePlayerStatistic)

    def _ensure_supported_season(self, season: str) -> None:
        if season != self.season:
            raise ValueError(f"FixtureProvider has {self.season} fixtures, not {season}.")

    def _load_many(self, filename: str, schema: type[SourceModel]) -> list[SourceModel]:
        fixture_path = self.fixture_root / filename
        raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValueError(f"{fixture_path} must contain a JSON array.")
        return [schema.model_validate(item) for item in raw_data]
