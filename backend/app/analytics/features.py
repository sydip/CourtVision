from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import sqrt
from statistics import fmean

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.analytics.prediction_types import PlayerProjectionFeatures, TeamProjectionFeatures
from app.models import (
    Game,
    Injury,
    Player,
    PlayerGameStat,
    PlayerSeasonSummary,
    PlayerTeamSeason,
    Team,
)


@dataclass(frozen=True)
class _PreliminaryPlayer:
    summary: PlayerSeasonSummary
    player: Player
    team: Team | None
    games_started: int
    shooting: dict[str, float]
    minutes_trend: float
    previous: PlayerSeasonSummary | None
    health_factor: float


def resolve_source_season(session: Session, requested_season: str) -> str:
    seasons = sorted(
        str(value)
        for value in session.scalars(
            select(distinct(PlayerSeasonSummary.season)).order_by(PlayerSeasonSummary.season)
        )
        if value
    )
    if not seasons:
        raise ValueError("No player season summaries are available in the database.")
    if requested_season in seasons:
        return requested_season
    eligible = [season for season in seasons if season <= requested_season]
    return eligible[-1] if eligible else seasons[-1]


def load_player_projection_features(
    session: Session,
    requested_season: str,
) -> tuple[str, list[PlayerProjectionFeatures]]:
    source_season = resolve_source_season(session, requested_season)
    previous_season = _previous_season(source_season)
    rows = session.execute(
        select(PlayerSeasonSummary, Player, Team)
        .join(Player, PlayerSeasonSummary.player_id == Player.id)
        .outerjoin(Team, PlayerSeasonSummary.team_id == Team.id)
        .where(PlayerSeasonSummary.season == source_season)
        .order_by(Player.full_name)
    ).all()
    shooting = _load_shooting_and_defense(session, source_season)
    recent_minutes = _load_recent_minutes(session, source_season)
    previous = {
        summary.player_id: summary
        for summary in session.scalars(
            select(PlayerSeasonSummary).where(PlayerSeasonSummary.season == previous_season)
        )
    }
    starts = {
        row.player_id: row.games_started
        for row in session.scalars(
            select(PlayerTeamSeason).where(PlayerTeamSeason.season == source_season)
        )
    }
    missed_games = defaultdict(int)
    for player_id, games_missed in session.execute(
        select(Injury.player_id, func.sum(Injury.games_missed))
        .where(Injury.season == source_season)
        .group_by(Injury.player_id)
    ):
        missed_games[player_id] = int(games_missed or 0)

    preliminary: list[_PreliminaryPlayer] = []
    for summary, player, team in rows:
        aggregate = shooting.get(player.id, {})
        mpg = _number(summary.minutes_per_game)
        games_started = starts.get(player.id, summary.games_played if mpg >= 24 else 0)
        preliminary.append(
            _PreliminaryPlayer(
                summary=summary,
                player=player,
                team=team,
                games_started=games_started,
                shooting=aggregate,
                minutes_trend=recent_minutes.get(player.id, mpg) - mpg,
                previous=previous.get(player.id),
                health_factor=max(0.5, 1 - missed_games[player.id] / 82),
            )
        )

    team_strengths = _team_strengths(preliminary)
    features: list[PlayerProjectionFeatures] = []
    for row in preliminary:
        summary = row.summary
        player = row.player
        team = row.team
        aggregate = row.shooting
        prior = row.previous
        games_started = row.games_started
        mpg = _number(summary.minutes_per_game)
        features.append(
            PlayerProjectionFeatures(
                player_id=player.id,
                nba_player_id=player.nba_player_id,
                player_name=player.full_name,
                team_id=team.id if team else player.team_id,
                team_name=f"{team.city} {team.name}" if team else None,
                team_abbreviation=team.abbreviation if team else None,
                conference=team.conference if team else None,
                position=player.position,
                source_season=source_season,
                games_played=summary.games_played,
                games_started=games_started,
                minutes_per_game=mpg,
                points_per_game=_number(summary.points_per_game),
                rebounds_per_game=_number(summary.rebounds_per_game),
                assists_per_game=_number(summary.assists_per_game),
                steals_per_game=float(aggregate.get("steals_per_game", 0.0)),
                blocks_per_game=float(aggregate.get("blocks_per_game", 0.0)),
                turnovers_per_game=_number(summary.turnovers_per_game),
                field_goal_percentage=float(aggregate.get("field_goal_percentage", 0.0)),
                three_point_percentage=float(aggregate.get("three_point_percentage", 0.0)),
                free_throw_percentage=float(aggregate.get("free_throw_percentage", 0.0)),
                true_shooting_percentage=_percentage(summary.true_shooting_percentage),
                usage_rate=_percentage(summary.usage_rate),
                plus_minus_per_game=_number(summary.plus_minus_per_game),
                points_per_36=_number(summary.points_per_36),
                rebounds_per_36=_number(summary.rebounds_per_36),
                assists_per_36=_number(summary.assists_per_36),
                minutes_trend=row.minutes_trend,
                year_over_year_points_delta=(
                    _number(summary.points_per_game) - _number(prior.points_per_game)
                    if prior
                    else 0.0
                ),
                year_over_year_minutes_delta=(
                    mpg - _number(prior.minutes_per_game) if prior else 0.0
                ),
                team_strength=team_strengths.get(team.id if team else -1, 0.0),
                age=_age_at_season_start(player.birthdate, requested_season),
                years_pro=player.years_pro,
                health_factor=row.health_factor,
                is_starter=games_started >= max(10, summary.games_played // 2) or mpg >= 26,
                is_synthetic=summary.is_synthetic,
                data_source=summary.data_source,
            )
        )
    return source_season, features


def load_team_projection_features(
    session: Session,
    requested_season: str,
) -> tuple[str, list[TeamProjectionFeatures]]:
    source_season, players = load_player_projection_features(session, requested_season)
    teams = {
        team.id: team for team in session.scalars(select(Team).order_by(Team.abbreviation)).all()
    }
    by_team: dict[int, list[PlayerProjectionFeatures]] = defaultdict(list)
    for player in players:
        if player.team_id is not None:
            by_team[player.team_id].append(player)

    results: list[TeamProjectionFeatures] = []
    for team_id, roster in by_team.items():
        team = teams.get(team_id)
        if team is None:
            continue
        rotation = sorted(roster, key=lambda player: player.minutes_per_game, reverse=True)[:10]
        minute_total = sum(max(player.minutes_per_game, 1) for player in rotation)
        weighted_plus_minus = sum(
            player.plus_minus_per_game * max(player.minutes_per_game, 1) for player in rotation
        ) / minute_total
        weighted_true_shooting = sum(
            player.true_shooting_percentage * max(player.minutes_per_game, 1)
            for player in rotation
        ) / minute_total
        weighted_production = sum(
            (
                player.points_per_game
                + 0.7 * player.assists_per_game
                + 0.35 * player.rebounds_per_game
            )
            * max(player.minutes_per_game, 1)
            for player in rotation
        ) / minute_total
        returning_minutes = sum(
            player.minutes_per_game for player in roster if player.games_played >= 10
        )
        continuity = min(1.0, returning_minutes / max(1.0, len(roster) * 22.0))
        results.append(
            TeamProjectionFeatures(
                team_id=team.id,
                nba_team_id=team.nba_team_id,
                team_name=f"{team.city} {team.name}",
                abbreviation=team.abbreviation,
                conference=team.conference,
                division=team.division,
                source_season=source_season,
                roster_size=len(roster),
                rotation_size=len(rotation),
                weighted_plus_minus=weighted_plus_minus,
                weighted_true_shooting=weighted_true_shooting,
                weighted_production=weighted_production,
                continuity=continuity,
                health_factor=fmean(player.health_factor for player in rotation),
                is_synthetic=any(player.is_synthetic for player in rotation),
                data_sources=sorted({player.data_source for player in rotation}),
            )
        )
    return source_season, results


def z_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    mean = fmean(values)
    variance = fmean((value - mean) ** 2 for value in values)
    standard_deviation = sqrt(variance)
    if standard_deviation == 0:
        return [0.0 for _ in values]
    return [(value - mean) / standard_deviation for value in values]


def _load_shooting_and_defense(
    session: Session,
    season: str,
) -> dict[int, dict[str, float]]:
    rows = session.execute(
        select(
            PlayerGameStat.player_id,
            func.count(PlayerGameStat.id),
            func.sum(PlayerGameStat.steals),
            func.sum(PlayerGameStat.blocks),
            func.sum(PlayerGameStat.field_goals_made),
            func.sum(PlayerGameStat.field_goals_attempted),
            func.sum(PlayerGameStat.three_pointers_made),
            func.sum(PlayerGameStat.three_pointers_attempted),
            func.sum(PlayerGameStat.free_throws_made),
            func.sum(PlayerGameStat.free_throws_attempted),
        )
        .where(PlayerGameStat.season == season)
        .group_by(PlayerGameStat.player_id)
    ).all()
    result: dict[int, dict[str, float]] = {}
    for row in rows:
        games = int(row[1] or 0)
        result[int(row[0])] = {
            "steals_per_game": _ratio(row[2], games),
            "blocks_per_game": _ratio(row[3], games),
            "field_goal_percentage": _ratio(row[4], row[5]),
            "three_point_percentage": _ratio(row[6], row[7]),
            "free_throw_percentage": _ratio(row[8], row[9]),
        }
    return result


def _load_recent_minutes(session: Session, season: str) -> dict[int, float]:
    rows = session.execute(
        select(PlayerGameStat.player_id, Game.game_date, PlayerGameStat.minutes)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .where(PlayerGameStat.season == season)
        .order_by(PlayerGameStat.player_id, Game.game_date.desc(), Game.nba_game_id.desc())
    ).all()
    values: dict[int, list[float]] = defaultdict(list)
    for player_id, _game_date, minutes in rows:
        if len(values[player_id]) < 10 and minutes is not None:
            values[player_id].append(float(minutes))
    return {
        player_id: fmean(player_minutes)
        for player_id, player_minutes in values.items()
        if player_minutes
    }


def _team_strengths(rows: list[_PreliminaryPlayer]) -> dict[int, float]:
    raw: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        team = row.team
        summary = row.summary
        if team is not None:
            raw[team.id].append(_number(summary.plus_minus_per_game))
    return {
        team_id: fmean(sorted(values, reverse=True)[:10])
        for team_id, values in raw.items()
        if values
    }


def _previous_season(season: str) -> str:
    try:
        start = int(season.split("-", maxsplit=1)[0])
    except (ValueError, IndexError):
        return season
    return f"{start - 1}-{str(start)[-2:]}"


def _age_at_season_start(birthdate: date | None, season: str) -> float | None:
    if birthdate is None:
        return None
    try:
        start_year = int(season.split("-", maxsplit=1)[0])
    except (ValueError, IndexError):
        return None
    season_start = date(start_year, 10, 1)
    return (season_start - birthdate).days / 365.2425


def _number(value: Decimal | int | float | None) -> float:
    return float(value) if value is not None else 0.0


def _percentage(value: Decimal | int | float | None) -> float:
    number = _number(value)
    return number / 100 if number > 1 else number


def _ratio(
    numerator: Decimal | int | float | None,
    denominator: Decimal | int | float | None,
) -> float:
    top = float(numerator or 0)
    bottom = float(denominator or 0)
    return top / bottom if bottom > 0 else 0.0
