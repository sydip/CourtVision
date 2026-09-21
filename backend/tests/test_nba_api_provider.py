from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest

from app.data.providers.nba_api import (
    NbaApiProvider,
    ProviderUnavailableError,
)
from app.data.raw_cache import JsonPayload, RawResponseCache

SEASON = "2025-26"
PLAYER_ID = 201939

STATIC_PLAYERS: JsonPayload = [
    {
        "id": PLAYER_ID,
        "full_name": "Stephen Curry",
        "first_name": "Stephen",
        "last_name": "Curry",
        "is_active": True,
    }
]
STATIC_TEAMS: JsonPayload = [
    {"id": 1610612744, "abbreviation": "GSW", "city": "San Francisco", "nickname": "Warriors"},
    {"id": 1610612747, "abbreviation": "LAL", "city": "Los Angeles", "nickname": "Lakers"},
]
COMMON_INFO: JsonPayload = {
    "CommonPlayerInfo": [
        {
            "PERSON_ID": PLAYER_ID,
            "BIRTHDATE": "1988-03-14T00:00:00",
            "HEIGHT": "6-2",
            "WEIGHT": "185",
            "POSITION": "Guard",
            "JERSEY": "30",
            "ROSTERSTATUS": "Active",
        }
    ]
}
PLAYER_GAME_LOG: JsonPayload = {
    "PlayerGameLog": [
        {
            "Player_ID": PLAYER_ID,
            "Game_ID": "0022500001",
            "GAME_DATE": "OCT 21, 2025",
            "MATCHUP": "GSW vs. LAL",
            "MIN": 31,
            "PTS": 28,
            "REB": 4,
            "AST": 7,
            "STL": 1,
            "BLK": 0,
            "TOV": 2,
            "PF": 3,
            "WL": "W",
            "FGM": 9,
            "FGA": 18,
            "FG3M": 5,
            "FG3A": 11,
            "FTM": 5,
            "FTA": 5,
            "PLUS_MINUS": 8,
        }
    ]
}
LEAGUE_BASE: JsonPayload = {
    "LeagueDashPlayerStats": [
        {
            "PLAYER_ID": PLAYER_ID,
            "TEAM_ID": 1610612744,
            "GP": 1,
            "MIN": 31.0,
            "PTS": 28.0,
            "REB": 4.0,
            "AST": 7.0,
        }
    ]
}
LEAGUE_ADVANCED: JsonPayload = {
    "LeagueDashPlayerStats": [{"PLAYER_ID": PLAYER_ID, "TS_PCT": 0.65, "USG_PCT": 0.31}]
}
LEAGUE_PLAYER_GAME_LOG: JsonPayload = {
    "LeagueGameLog": [
        {
            "PLAYER_ID": PLAYER_ID,
            "GAME_ID": "0022400001",
            "GAME_DATE": "2024-10-22",
            "MATCHUP": "GSW vs. LAL",
            "WL": "W",
            "MIN": 34,
            "PTS": 31,
            "REB": 5,
            "AST": 6,
            "STL": 2,
            "BLK": 0,
            "TOV": 3,
            "PF": 2,
            "FGM": 10,
            "FGA": 20,
            "FG3M": 5,
            "FG3A": 12,
            "FTM": 6,
            "FTA": 6,
            "PLUS_MINUS": 12,
        },
        {
            "PLAYER_ID": 977,
            "GAME_ID": "0022400001",
            "GAME_DATE": "2024-10-22",
            "MATCHUP": "LAL @ GSW",
            "WL": "L",
            "MIN": 30,
            "PTS": 22,
            "REB": 7,
            "AST": 4,
            "STL": 1,
            "BLK": 1,
            "TOV": 2,
            "PF": 3,
            "FGM": 8,
            "FGA": 18,
            "FG3M": 2,
            "FG3A": 6,
            "FTM": 4,
            "FTA": 5,
            "PLUS_MINUS": -12,
        },
    ]
}


class FakeRateLimitError(Exception):
    status_code = 429


class FakeNbaApiClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.failures: dict[str, list[Exception]] = {}
        self.common_info_response: JsonPayload = COMMON_INFO
        self.static_players: JsonPayload = STATIC_PLAYERS
        self.league_base: JsonPayload = LEAGUE_BASE
        self.league_player_game_log: JsonPayload = LEAGUE_PLAYER_GAME_LOG

    def fail_once(self, method_name: str, exc: Exception) -> None:
        self.failures.setdefault(method_name, []).append(exc)

    def _maybe_fail(self, method_name: str) -> None:
        self.calls.append(method_name)
        failures = self.failures.get(method_name, [])
        if failures:
            raise failures.pop(0)

    def get_static_players(self) -> JsonPayload:
        self._maybe_fail("get_static_players")
        return self.static_players

    def get_static_teams(self) -> JsonPayload:
        self._maybe_fail("get_static_teams")
        return STATIC_TEAMS

    def get_common_player_info(self, player_id: int, timeout_seconds: float) -> JsonPayload:
        self._maybe_fail("get_common_player_info")
        return self.common_info_response

    def get_player_game_log(
        self,
        player_id: int,
        season: str,
        timeout_seconds: float,
    ) -> JsonPayload:
        self._maybe_fail("get_player_game_log")
        return PLAYER_GAME_LOG

    def get_league_player_game_log(self, season: str, timeout_seconds: float) -> JsonPayload:
        self._maybe_fail("get_league_player_game_log")
        return self.league_player_game_log

    def get_league_player_stats(
        self,
        season: str,
        measure_type: str,
        timeout_seconds: float,
    ) -> JsonPayload:
        method_name = f"get_league_player_stats_{measure_type.lower()}"
        self._maybe_fail(method_name)
        if measure_type == "Advanced":
            return LEAGUE_ADVANCED
        return self.league_base


def _provider(
    tmp_path: Path,
    client: FakeNbaApiClient,
    *,
    sleep_func: Callable[[float], None] | None = None,
) -> NbaApiProvider:
    return NbaApiProvider(
        season=SEASON,
        raw_data_dir=str(tmp_path),
        timeout_seconds=0.1,
        player_ids=[PLAYER_ID],
        max_retries=1,
        backoff_seconds=0,
        request_delay_seconds=0,
        client=client,
        sleep_func=sleep_func or (lambda _: None),
    )


def test_nba_api_provider_success_maps_and_caches_raw_responses(tmp_path: Path) -> None:
    client = FakeNbaApiClient()
    provider = _provider(tmp_path, client)

    assert provider.get_players()[0].full_name == "Stephen Curry"
    profile = provider.get_player_profiles()[0]
    assert profile.height == "6-2"
    assert profile.position == "Guard"
    assert profile.jersey_number == "30"
    assert provider.get_teams()[0].city == "Golden State"
    assert provider.get_games()[0].home_team_nba_id == 1610612744
    game_log = provider.get_season_game_logs(SEASON)[0]
    assert game_log.points == 28
    assert game_log.is_home is True
    assert game_log.result == "W"
    assert game_log.personal_fouls == 3
    assert provider.get_league_player_statistics(SEASON)[0].true_shooting_percentage == Decimal(
        "0.65"
    )

    assert (tmp_path / SEASON / "static_players").exists()
    assert (tmp_path / SEASON / "common_player_info_201939").exists()
    assert (tmp_path / SEASON / "player_game_log_2025-26_201939").exists()

    RawResponseCache(tmp_path).save(SEASON, "static_players", STATIC_PLAYERS)
    assert len(list((tmp_path / SEASON / "static_players").glob("*.json"))) == 2


def test_season_roster_source_includes_players_who_played_that_season(tmp_path: Path) -> None:
    retired_id = 977
    client = FakeNbaApiClient()
    client.static_players = [
        *STATIC_PLAYERS,
        {
            "id": retired_id,
            "full_name": "Kobe Bryant",
            "first_name": "Kobe",
            "last_name": "Bryant",
            "is_active": False,
        },
    ]
    client.league_base = {
        "LeagueDashPlayerStats": [
            {"PLAYER_ID": PLAYER_ID, "TEAM_ID": 1610612744, "GP": 1},
            {"PLAYER_ID": retired_id, "TEAM_ID": 1610612747, "GP": 1},
        ]
    }

    def build(roster_source: str) -> NbaApiProvider:
        return NbaApiProvider(
            season=SEASON,
            raw_data_dir=str(tmp_path / roster_source),
            timeout_seconds=0.1,
            player_ids=None,
            player_limit=None,
            max_retries=1,
            backoff_seconds=0,
            request_delay_seconds=0,
            roster_source=roster_source,  # type: ignore[arg-type]
            client=client,
            sleep_func=lambda _: None,
        )

    season_ids = {player.nba_player_id for player in build("season").get_players()}
    assert season_ids == {PLAYER_ID, retired_id}  # retired player included via season stats

    active_ids = {player.nba_player_id for player in build("active").get_players()}
    assert active_ids == {PLAYER_ID}  # active-only roster excludes the retired player


def test_league_game_log_source_fetches_all_players_in_one_request(tmp_path: Path) -> None:
    retired_id = 977
    client = FakeNbaApiClient()
    client.static_players = [
        *STATIC_PLAYERS,
        {
            "id": retired_id,
            "full_name": "Kobe Bryant",
            "first_name": "Kobe",
            "last_name": "Bryant",
            "is_active": False,
        },
    ]
    client.league_base = {
        "LeagueDashPlayerStats": [
            {"PLAYER_ID": PLAYER_ID, "TEAM_ID": 1610612744, "GP": 1},
            {"PLAYER_ID": retired_id, "TEAM_ID": 1610612747, "GP": 1},
        ]
    }
    provider = NbaApiProvider(
        season=SEASON,
        raw_data_dir=str(tmp_path),
        timeout_seconds=0.1,
        player_ids=None,
        player_limit=None,
        max_retries=1,
        backoff_seconds=0,
        request_delay_seconds=0,
        roster_source="season",
        game_log_source="league",
        client=client,
        sleep_func=lambda _: None,
    )

    logs = provider.get_season_game_logs(SEASON)
    by_player = {log.nba_player_id: log for log in logs}
    assert set(by_player) == {PLAYER_ID, retired_id}  # both players from one bulk call
    assert by_player[PLAYER_ID].points == 31
    assert by_player[PLAYER_ID].is_home is True
    assert by_player[retired_id].points == 22
    assert by_player[retired_id].is_home is False

    # The whole-season log is fetched exactly once and reused for games + logs.
    assert client.calls.count("get_league_player_game_log") == 1
    assert "get_player_game_log" not in client.calls
    provider.get_games()
    assert client.calls.count("get_league_player_game_log") == 1


def test_nba_api_provider_timeout_uses_bounded_retries(tmp_path: Path) -> None:
    client = FakeNbaApiClient()
    client.fail_once("get_static_players", TimeoutError("read timeout"))
    client.fail_once("get_static_players", TimeoutError("read timeout"))
    provider = _provider(tmp_path, client)

    with pytest.raises(ProviderUnavailableError, match="no cached response"):
        provider.get_players()

    assert client.calls == ["get_static_players", "get_static_players"]


def test_nba_api_provider_rate_limit_retries_then_succeeds(tmp_path: Path) -> None:
    client = FakeNbaApiClient()
    client.fail_once("get_static_players", FakeRateLimitError("429 too many requests"))
    slept: list[float] = []
    provider = _provider(tmp_path, client, sleep_func=slept.append)

    assert provider.get_players()[0].nba_player_id == PLAYER_ID
    assert client.calls == [
        "get_static_players",
        "get_static_players",
        "get_league_player_stats_base",
    ]
    assert slept == [0]


def test_nba_api_provider_malformed_response_fails_clearly(tmp_path: Path) -> None:
    client = FakeNbaApiClient()
    client.common_info_response = {"CommonPlayerInfo": {"bad": "shape"}}
    provider = _provider(tmp_path, client)

    with pytest.raises(ProviderUnavailableError, match="missing list dataset CommonPlayerInfo"):
        provider.get_player_profiles()


def test_nba_api_provider_uses_latest_cached_response_on_failure(tmp_path: Path) -> None:
    client = FakeNbaApiClient()
    client.fail_once("get_common_player_info", TimeoutError("read timeout"))
    client.fail_once("get_common_player_info", TimeoutError("read timeout"))
    RawResponseCache(tmp_path).save(SEASON, "common_player_info_201939", COMMON_INFO)
    provider = _provider(tmp_path, client)

    profile = provider.get_player_profiles()[0]

    assert profile.nba_player_id == PLAYER_ID
    assert profile.weight_pounds == 185
