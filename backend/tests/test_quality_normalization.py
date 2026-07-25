from __future__ import annotations

from decimal import Decimal

from app.data.normalization import normalize_player_game_log
from app.data.quality import validate_league_player_statistics, validate_player_game_logs
from app.data.source_schemas import SourceLeaguePlayerStatistic, SourcePlayerGameLog


def test_quality_reports_invalid_player_game_log_reasons() -> None:
    bad_log = SourcePlayerGameLog(
        nba_player_id=201939,
        nba_game_id="0022500001",
        team_nba_id=1610612744,
        season="2025-26",
        minutes=Decimal("-1"),
        points=-2,
        field_goals_made=6,
        field_goals_attempted=5,
    )

    result = validate_player_game_logs([bad_log])

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "minutes cannot be negative" in result.rejected[0].reason
    assert "points cannot be negative" in result.rejected[0].reason
    assert "field_goals_made cannot exceed field_goals_attempted" in result.rejected[0].reason


def test_quality_reports_invalid_percentages() -> None:
    bad_stat = SourceLeaguePlayerStatistic(
        nba_player_id=2544,
        team_nba_id=1610612747,
        season="2025-26",
        games_played=1,
        true_shooting_percentage=Decimal("1.2"),
        usage_rate=Decimal("-0.1"),
    )

    result = validate_league_player_statistics([bad_stat])

    assert len(result.rejected) == 1
    assert "true_shooting_percentage must be between zero and one" in result.rejected[0].reason
    assert "usage_rate must be between zero and one" in result.rejected[0].reason


def test_normalization_maps_source_to_internal_record() -> None:
    source = SourcePlayerGameLog(
        nba_player_id=201939,
        nba_game_id="0022500001",
        team_nba_id=1610612744,
        season="2025-26",
        minutes=Decimal("33.50"),
        points=31,
        field_goals_made=11,
        field_goals_attempted=21,
    )

    record = normalize_player_game_log(source)

    assert record.nba_player_id == 201939
    assert record.nba_game_id == "0022500001"
    assert record.minutes == Decimal("33.50")
    assert record.points == 31
