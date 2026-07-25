from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceTeam,
)


@dataclass(frozen=True)
class TeamRecord:
    nba_team_id: int
    abbreviation: str
    city: str
    name: str
    conference: str | None
    division: str | None


@dataclass(frozen=True)
class PlayerRecord:
    nba_player_id: int
    slug: str
    full_name: str
    first_name: str | None
    last_name: str | None
    team_nba_id: int | None
    position: str | None


@dataclass(frozen=True)
class PlayerProfileRecord:
    nba_player_id: int
    birthdate: date | None
    height: str | None
    weight_pounds: int | None
    position: str | None
    jersey_number: str | None
    active: bool


@dataclass(frozen=True)
class GameRecord:
    nba_game_id: str
    season: str
    game_date: date
    home_team_nba_id: int
    away_team_nba_id: int
    home_score: int | None
    away_score: int | None


@dataclass(frozen=True)
class PlayerGameStatRecord:
    nba_player_id: int
    nba_game_id: str
    team_nba_id: int | None
    season: str
    matchup: str | None
    is_home: bool | None
    result: str | None
    minutes: Decimal | None
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    personal_fouls: int
    field_goals_made: int
    field_goals_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int
    plus_minus: Decimal | None


@dataclass(frozen=True)
class PlayerSeasonSummaryRecord:
    nba_player_id: int
    team_nba_id: int | None
    season: str
    games_played: int
    minutes_per_game: Decimal | None
    points_per_game: Decimal | None
    rebounds_per_game: Decimal | None
    assists_per_game: Decimal | None
    true_shooting_percentage: Decimal | None
    usage_rate: Decimal | None


def normalize_team(source: SourceTeam) -> TeamRecord:
    return TeamRecord(
        nba_team_id=source.nba_team_id,
        abbreviation=source.abbreviation,
        city=source.city,
        name=source.name,
        conference=source.conference,
        division=source.division,
    )


def normalize_player(source: SourcePlayer) -> PlayerRecord:
    return PlayerRecord(
        nba_player_id=source.nba_player_id,
        slug=source.slug,
        full_name=source.full_name,
        first_name=source.first_name,
        last_name=source.last_name,
        team_nba_id=source.team_nba_id,
        position=source.position,
    )


def normalize_player_profile(source: SourcePlayerProfile) -> PlayerProfileRecord:
    return PlayerProfileRecord(
        nba_player_id=source.nba_player_id,
        birthdate=source.birthdate,
        height=source.height,
        weight_pounds=source.weight_pounds,
        position=source.position,
        jersey_number=source.jersey_number,
        active=source.active,
    )


def normalize_game(source: SourceGame) -> GameRecord:
    return GameRecord(
        nba_game_id=source.nba_game_id,
        season=source.season,
        game_date=source.game_date,
        home_team_nba_id=source.home_team_nba_id,
        away_team_nba_id=source.away_team_nba_id,
        home_score=source.home_score,
        away_score=source.away_score,
    )


def normalize_player_game_log(source: SourcePlayerGameLog) -> PlayerGameStatRecord:
    return PlayerGameStatRecord(
        nba_player_id=source.nba_player_id,
        nba_game_id=source.nba_game_id,
        team_nba_id=source.team_nba_id,
        season=source.season,
        matchup=source.matchup,
        is_home=source.is_home,
        result=source.result,
        minutes=source.minutes,
        points=source.points,
        rebounds=source.rebounds,
        assists=source.assists,
        steals=source.steals,
        blocks=source.blocks,
        turnovers=source.turnovers,
        personal_fouls=source.personal_fouls,
        field_goals_made=source.field_goals_made,
        field_goals_attempted=source.field_goals_attempted,
        three_pointers_made=source.three_pointers_made,
        three_pointers_attempted=source.three_pointers_attempted,
        free_throws_made=source.free_throws_made,
        free_throws_attempted=source.free_throws_attempted,
        plus_minus=source.plus_minus,
    )


def normalize_league_player_statistic(
    source: SourceLeaguePlayerStatistic,
) -> PlayerSeasonSummaryRecord:
    return PlayerSeasonSummaryRecord(
        nba_player_id=source.nba_player_id,
        team_nba_id=source.team_nba_id,
        season=source.season,
        games_played=source.games_played,
        minutes_per_game=source.minutes_per_game,
        points_per_game=source.points_per_game,
        rebounds_per_game=source.rebounds_per_game,
        assists_per_game=source.assists_per_game,
        true_shooting_percentage=source.true_shooting_percentage,
        usage_rate=source.usage_rate,
    )
