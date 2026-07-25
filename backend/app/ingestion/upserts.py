from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.normalization import (
    GameRecord,
    PlayerGameStatRecord,
    PlayerProfileRecord,
    PlayerRecord,
    PlayerSeasonSummaryRecord,
    TeamRecord,
)
from app.models import Game, Player, PlayerGameStat, PlayerSeasonSummary, Team

UpsertOutcome = Literal["inserted", "updated", "unchanged"]


class RecordRejectedError(Exception):
    pass


def upsert_team(session: Session, record: TeamRecord) -> UpsertOutcome:
    team = session.scalar(select(Team).where(Team.nba_team_id == record.nba_team_id))
    values = {
        "abbreviation": record.abbreviation,
        "city": record.city,
        "name": record.name,
        "conference": record.conference,
        "division": record.division,
    }
    if team is None:
        session.add(Team(nba_team_id=record.nba_team_id, **values))
        session.flush()
        return "inserted"
    if _apply_changes(team, values):
        session.flush()
        return "updated"
    return "unchanged"


def upsert_player(session: Session, record: PlayerRecord) -> UpsertOutcome:
    player = session.scalar(select(Player).where(Player.nba_player_id == record.nba_player_id))
    team_id = _team_id_for_nba_id(session, record.team_nba_id)
    values = {
        "slug": record.slug,
        "full_name": record.full_name,
        "first_name": record.first_name,
        "last_name": record.last_name,
        "team_id": team_id,
    }
    if player is None or record.position is not None:
        values["position"] = record.position
    if player is None:
        session.add(Player(nba_player_id=record.nba_player_id, **values))
        session.flush()
        return "inserted"
    if _apply_changes(player, values):
        session.flush()
        return "updated"
    return "unchanged"


def upsert_player_profile(session: Session, record: PlayerProfileRecord) -> UpsertOutcome:
    player = session.scalar(select(Player).where(Player.nba_player_id == record.nba_player_id))
    if player is None:
        raise RecordRejectedError(f"unknown player nba_player_id={record.nba_player_id}")
    values = {
        "birthdate": record.birthdate,
        "height": record.height,
        "weight_pounds": record.weight_pounds,
        "active": record.active,
    }
    if record.position is not None:
        values["position"] = record.position
    if record.jersey_number is not None:
        values["jersey_number"] = record.jersey_number
    if _apply_changes(player, values):
        session.flush()
        return "updated"
    return "unchanged"


def upsert_game(session: Session, record: GameRecord) -> UpsertOutcome:
    game = session.scalar(select(Game).where(Game.nba_game_id == record.nba_game_id))
    home_team_id = _required_team_id_for_nba_id(session, record.home_team_nba_id)
    away_team_id = _required_team_id_for_nba_id(session, record.away_team_nba_id)
    values = {
        "season": record.season,
        "game_date": record.game_date,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_score": record.home_score,
        "away_score": record.away_score,
    }
    if game is None:
        session.add(Game(nba_game_id=record.nba_game_id, **values))
        session.flush()
        return "inserted"
    if _apply_changes(game, values):
        session.flush()
        return "updated"
    return "unchanged"


def upsert_player_game_stat(session: Session, record: PlayerGameStatRecord) -> UpsertOutcome:
    player = session.scalar(select(Player).where(Player.nba_player_id == record.nba_player_id))
    if player is None:
        raise RecordRejectedError(f"unknown player nba_player_id={record.nba_player_id}")
    game = session.scalar(select(Game).where(Game.nba_game_id == record.nba_game_id))
    if game is None:
        raise RecordRejectedError(f"unknown game nba_game_id={record.nba_game_id}")
    team_id = _team_id_for_nba_id(session, record.team_nba_id)
    stat = session.scalar(
        select(PlayerGameStat).where(
            PlayerGameStat.player_id == player.id,
            PlayerGameStat.game_id == game.id,
        )
    )
    values = {
        "team_id": team_id,
        "season": record.season,
        "matchup": record.matchup,
        "is_home": record.is_home,
        "result": record.result,
        "minutes": record.minutes,
        "points": record.points,
        "rebounds": record.rebounds,
        "assists": record.assists,
        "steals": record.steals,
        "blocks": record.blocks,
        "turnovers": record.turnovers,
        "personal_fouls": record.personal_fouls,
        "field_goals_made": record.field_goals_made,
        "field_goals_attempted": record.field_goals_attempted,
        "three_pointers_made": record.three_pointers_made,
        "three_pointers_attempted": record.three_pointers_attempted,
        "free_throws_made": record.free_throws_made,
        "free_throws_attempted": record.free_throws_attempted,
        "plus_minus": record.plus_minus,
    }
    if stat is None:
        session.add(PlayerGameStat(player_id=player.id, game_id=game.id, **values))
        session.flush()
        return "inserted"
    if _apply_changes(stat, values):
        session.flush()
        return "updated"
    return "unchanged"


def refresh_days_since_previous_game(session: Session, season: str) -> int:
    rows = session.execute(
        select(PlayerGameStat, Game.game_date)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .where(PlayerGameStat.season == season)
        .order_by(PlayerGameStat.player_id, Game.game_date, Game.nba_game_id)
    ).tuples()
    previous_dates: dict[int, date] = {}
    changed = 0
    for stat, game_date in rows:
        previous_date = previous_dates.get(stat.player_id)
        rest_days = None if previous_date is None else (game_date - previous_date).days
        if stat.days_since_previous_game != rest_days:
            stat.days_since_previous_game = rest_days
            changed += 1
        previous_dates[stat.player_id] = game_date
    if changed:
        session.flush()
    return changed


def upsert_player_season_summary(
    session: Session,
    record: PlayerSeasonSummaryRecord,
) -> UpsertOutcome:
    player = session.scalar(select(Player).where(Player.nba_player_id == record.nba_player_id))
    if player is None:
        raise RecordRejectedError(f"unknown player nba_player_id={record.nba_player_id}")
    team_id = _team_id_for_nba_id(session, record.team_nba_id)
    summary = session.scalar(
        select(PlayerSeasonSummary).where(
            PlayerSeasonSummary.player_id == player.id,
            PlayerSeasonSummary.season == record.season,
        )
    )
    values = {
        "team_id": team_id,
        "games_played": record.games_played,
        "minutes_per_game": record.minutes_per_game,
        "points_per_game": record.points_per_game,
        "rebounds_per_game": record.rebounds_per_game,
        "assists_per_game": record.assists_per_game,
        "true_shooting_percentage": record.true_shooting_percentage,
        "usage_rate": record.usage_rate,
    }
    if summary is None:
        session.add(PlayerSeasonSummary(player_id=player.id, season=record.season, **values))
        session.flush()
        return "inserted"
    if _apply_changes(summary, values):
        session.flush()
        return "updated"
    return "unchanged"


def _team_id_for_nba_id(session: Session, nba_team_id: int | None) -> int | None:
    if nba_team_id is None:
        return None
    return _required_team_id_for_nba_id(session, nba_team_id)


def _required_team_id_for_nba_id(session: Session, nba_team_id: int) -> int:
    team_id = session.scalar(select(Team.id).where(Team.nba_team_id == nba_team_id))
    if team_id is None:
        raise RecordRejectedError(f"unknown team nba_team_id={nba_team_id}")
    return team_id


def _apply_changes(instance: object, values: Mapping[str, object]) -> bool:
    changed = False
    for field_name, value in values.items():
        if getattr(instance, field_name) != value:
            setattr(instance, field_name, value)
            changed = True
    return changed
