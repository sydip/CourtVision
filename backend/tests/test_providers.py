from __future__ import annotations

import json
from pathlib import Path

from app.data.providers import CachedResponseProvider, FixtureProvider


def fixture_root() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "2025-26"


def test_fixture_provider_loads_offline_records() -> None:
    provider = FixtureProvider(fixture_root=fixture_root(), season="2025-26")

    assert len(provider.get_teams()) == 4
    assert provider.get_players()[0].slug == "stephen-curry"
    assert provider.get_games()[0].nba_game_id == "0022500001"
    assert len(provider.get_season_game_logs("2025-26")) == 5
    assert len(provider.get_league_player_statistics("2025-26")) == 5


def test_cached_response_provider_uses_cache_files(tmp_path: Path) -> None:
    fixture_provider = FixtureProvider(fixture_root=fixture_root(), season="2025-26")
    cached_provider = CachedResponseProvider(fixture_provider, tmp_path)

    first_load = cached_provider.get_players()
    cache_path = tmp_path / "players.json"
    assert cache_path.exists()

    cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    cached_payload[0]["full_name"] = "Cached Stephen Curry"
    cache_path.write_text(json.dumps(cached_payload), encoding="utf-8")

    second_load = cached_provider.get_players()
    assert first_load[0].full_name == "Stephen Curry"
    assert second_load[0].full_name == "Cached Stephen Curry"
