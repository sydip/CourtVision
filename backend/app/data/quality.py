from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceTeam,
)

SourceRecord = TypeVar("SourceRecord", bound=BaseModel)


@dataclass(frozen=True)
class RejectedRecord:
    entity: str
    source_id: str
    reason: str
    payload: dict[str, object]


@dataclass(frozen=True)
class ValidationResult(Generic[SourceRecord]):
    accepted: list[SourceRecord]
    rejected: list[RejectedRecord]


def validate_teams(records: list[SourceTeam]) -> ValidationResult[SourceTeam]:
    return _validate_many("team", records, lambda record: str(record.nba_team_id), _team_errors)


def validate_players(records: list[SourcePlayer]) -> ValidationResult[SourcePlayer]:
    return _validate_many(
        "player",
        records,
        lambda record: str(record.nba_player_id),
        _player_errors,
    )


def validate_player_profiles(
    records: list[SourcePlayerProfile],
) -> ValidationResult[SourcePlayerProfile]:
    return _validate_many(
        "player_profile",
        records,
        lambda record: str(record.nba_player_id),
        _profile_errors,
    )


def validate_games(records: list[SourceGame]) -> ValidationResult[SourceGame]:
    return _validate_many("game", records, lambda record: record.nba_game_id, _game_errors)


def validate_player_game_logs(
    records: list[SourcePlayerGameLog],
) -> ValidationResult[SourcePlayerGameLog]:
    return _validate_many(
        "player_game_log",
        records,
        lambda record: f"{record.nba_player_id}:{record.nba_game_id}",
        _game_log_errors,
    )


def validate_league_player_statistics(
    records: list[SourceLeaguePlayerStatistic],
) -> ValidationResult[SourceLeaguePlayerStatistic]:
    return _validate_many(
        "league_player_statistic",
        records,
        lambda record: f"{record.nba_player_id}:{record.season}",
        _league_stat_errors,
    )


def _validate_many(
    entity: str,
    records: list[SourceRecord],
    source_id: Callable[[SourceRecord], str],
    validator: Callable[[SourceRecord], list[str]],
) -> ValidationResult[SourceRecord]:
    accepted: list[SourceRecord] = []
    rejected: list[RejectedRecord] = []
    for record in records:
        errors = validator(record)
        if errors:
            rejected.append(
                RejectedRecord(
                    entity=entity,
                    source_id=source_id(record),
                    reason="; ".join(errors),
                    payload=record.model_dump(mode="json"),
                )
            )
            continue
        accepted.append(record)
    return ValidationResult(accepted=accepted, rejected=rejected)


def _team_errors(record: SourceTeam) -> list[str]:
    errors = _positive_id(record.nba_team_id, "nba_team_id")
    if not record.abbreviation.strip():
        errors.append("abbreviation is required")
    if not record.name.strip():
        errors.append("name is required")
    return errors


def _player_errors(record: SourcePlayer) -> list[str]:
    errors = _positive_id(record.nba_player_id, "nba_player_id")
    if record.team_nba_id is not None:
        errors.extend(_positive_id(record.team_nba_id, "team_nba_id"))
    if not record.slug.strip():
        errors.append("slug is required")
    if not record.full_name.strip():
        errors.append("full_name is required")
    return errors


def _profile_errors(record: SourcePlayerProfile) -> list[str]:
    errors = _positive_id(record.nba_player_id, "nba_player_id")
    if record.weight_pounds is not None and record.weight_pounds < 0:
        errors.append("weight_pounds cannot be negative")
    return errors


def _game_errors(record: SourceGame) -> list[str]:
    errors = _positive_id(record.home_team_nba_id, "home_team_nba_id")
    errors.extend(_positive_id(record.away_team_nba_id, "away_team_nba_id"))
    if not record.nba_game_id.strip():
        errors.append("nba_game_id is required")
    if not record.season.strip():
        errors.append("season is required")
    if record.home_score is not None and record.home_score < 0:
        errors.append("home_score cannot be negative")
    if record.away_score is not None and record.away_score < 0:
        errors.append("away_score cannot be negative")
    return errors


def _game_log_errors(record: SourcePlayerGameLog) -> list[str]:
    errors = _positive_id(record.nba_player_id, "nba_player_id")
    if record.team_nba_id is not None:
        errors.extend(_positive_id(record.team_nba_id, "team_nba_id"))
    if not record.nba_game_id.strip():
        errors.append("nba_game_id is required")
    if not record.season.strip():
        errors.append("season is required")
    if record.result is not None and record.result not in {"W", "L"}:
        errors.append("result must be W or L")
    errors.extend(_nonnegative_decimal(record.minutes, "minutes"))
    errors.extend(_nonnegative_int(record.points, "points"))
    errors.extend(_nonnegative_int(record.rebounds, "rebounds"))
    errors.extend(_nonnegative_int(record.assists, "assists"))
    errors.extend(_nonnegative_int(record.steals, "steals"))
    errors.extend(_nonnegative_int(record.blocks, "blocks"))
    errors.extend(_nonnegative_int(record.turnovers, "turnovers"))
    errors.extend(_nonnegative_int(record.personal_fouls, "personal_fouls"))
    errors.extend(
        _made_not_exceed_attempted(
            record.field_goals_made, record.field_goals_attempted, "field_goals"
        )
    )
    errors.extend(
        _made_not_exceed_attempted(
            record.three_pointers_made,
            record.three_pointers_attempted,
            "three_pointers",
        )
    )
    errors.extend(
        _made_not_exceed_attempted(
            record.free_throws_made, record.free_throws_attempted, "free_throws"
        )
    )
    return errors


def _league_stat_errors(record: SourceLeaguePlayerStatistic) -> list[str]:
    errors = _positive_id(record.nba_player_id, "nba_player_id")
    if record.team_nba_id is not None:
        errors.extend(_positive_id(record.team_nba_id, "team_nba_id"))
    if not record.season.strip():
        errors.append("season is required")
    errors.extend(_nonnegative_int(record.games_played, "games_played"))
    errors.extend(_nonnegative_decimal(record.minutes_per_game, "minutes_per_game"))
    errors.extend(_nonnegative_decimal(record.points_per_game, "points_per_game"))
    errors.extend(
        _percentage_between_zero_one(record.true_shooting_percentage, "true_shooting_percentage")
    )
    errors.extend(_percentage_between_zero_one(record.usage_rate, "usage_rate"))
    return errors


def _positive_id(value: int, field_name: str) -> list[str]:
    if value <= 0:
        return [f"{field_name} must be positive"]
    return []


def _nonnegative_int(value: int, field_name: str) -> list[str]:
    if value < 0:
        return [f"{field_name} cannot be negative"]
    return []


def _nonnegative_decimal(value: Decimal | None, field_name: str) -> list[str]:
    if value is not None and value < 0:
        return [f"{field_name} cannot be negative"]
    return []


def _made_not_exceed_attempted(made: int, attempted: int, stat_name: str) -> list[str]:
    errors: list[str] = []
    if made < 0:
        errors.append(f"{stat_name}_made cannot be negative")
    if attempted < 0:
        errors.append(f"{stat_name}_attempted cannot be negative")
    if made > attempted:
        errors.append(f"{stat_name}_made cannot exceed {stat_name}_attempted")
    return errors


def _percentage_between_zero_one(value: Decimal | None, field_name: str) -> list[str]:
    if value is None:
        return []
    if value < 0 or value > 1:
        return [f"{field_name} must be between zero and one"]
    return []
