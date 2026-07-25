from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SourceBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceTeam(SourceBaseModel):
    nba_team_id: int
    abbreviation: str
    city: str
    name: str
    conference: str | None = None
    division: str | None = None


class SourcePlayer(SourceBaseModel):
    nba_player_id: int
    slug: str
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    team_nba_id: int | None = None
    position: str | None = None


class SourcePlayerProfile(SourceBaseModel):
    nba_player_id: int
    birthdate: date | None = None
    height: str | None = None
    weight_pounds: int | None = None
    position: str | None = None
    jersey_number: str | None = None
    active: bool = True


class SourceGame(SourceBaseModel):
    nba_game_id: str
    season: str
    game_date: date
    home_team_nba_id: int
    away_team_nba_id: int
    home_score: int | None = None
    away_score: int | None = None


class SourcePlayerGameLog(SourceBaseModel):
    nba_player_id: int
    nba_game_id: str
    team_nba_id: int | None = None
    season: str
    matchup: str | None = None
    is_home: bool | None = None
    result: str | None = None
    minutes: Decimal | None = None
    points: int = 0
    rebounds: int = 0
    assists: int = 0
    steals: int = 0
    blocks: int = 0
    turnovers: int = 0
    personal_fouls: int = 0
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    three_pointers_made: int = 0
    three_pointers_attempted: int = 0
    free_throws_made: int = 0
    free_throws_attempted: int = 0
    plus_minus: Decimal | None = None


class SourceLeaguePlayerStatistic(SourceBaseModel):
    nba_player_id: int
    team_nba_id: int | None = None
    season: str
    games_played: int = 0
    minutes_per_game: Decimal | None = None
    points_per_game: Decimal | None = None
    rebounds_per_game: Decimal | None = None
    assists_per_game: Decimal | None = None
    true_shooting_percentage: Decimal | None = None
    usage_rate: Decimal | None = None
