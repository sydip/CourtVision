from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Game,
    Player,
    PlayerGameStat,
    PlayerSeasonSummary,
    RosterMembership,
    StandingsSnapshot,
    Team,
    TeamSeasonSummary,
)


def player_season_stats(session: Session, player: Player, season: str) -> list[dict[str, Any]]:
    summary = session.scalar(
        select(PlayerSeasonSummary).where(
            PlayerSeasonSummary.player_id == player.id, PlayerSeasonSummary.season == season
        )
    )
    if summary is None:
        return []
    return [
        {
            "type": "player_season_stats",
            "player": player.full_name,
            "season": season,
            "gamesPlayed": summary.games_played,
            "pointsPerGame": _float(summary.points_per_game),
            "reboundsPerGame": _float(summary.rebounds_per_game),
            "assistsPerGame": _float(summary.assists_per_game),
            "trueShootingPercentage": _float(summary.true_shooting_percentage),
            "source": "database",
        }
    ]


def player_games(
    session: Session,
    player: Player,
    season: str,
    game_date: str | None = None,
    opponent: Team | None = None,
) -> list[dict[str, Any]]:
    statement = (
        select(PlayerGameStat, Game, Team)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .outerjoin(Team, PlayerGameStat.team_id == Team.id)
        .where(
            PlayerGameStat.player_id == player.id,
            PlayerGameStat.season == season,
            Game.season == season,
        )
        .order_by(Game.game_date)
    )
    if game_date:
        statement = statement.where(Game.game_date == game_date)
    rows = session.execute(statement).all()
    evidence = []
    for stat, game, team in rows:
        opponent_id = game.away_team_id if stat.team_id == game.home_team_id else game.home_team_id
        opponent_team = session.get(Team, opponent_id)
        if opponent is not None and opponent_id != opponent.id:
            continue
        evidence.append(
            {
                "type": "player_game_stats",
                "player": player.full_name,
                "team": _team_name(team),
                "opponent": _team_name(opponent_team),
                "gameDate": game.game_date.isoformat(),
                "points": stat.points,
                "rebounds": stat.rebounds,
                "assists": stat.assists,
                "steals": stat.steals,
                "blocks": stat.blocks,
                "turnovers": stat.turnovers,
                "source": "database",
            }
        )
    return evidence


def team_summary(session: Session, team: Team, season: str) -> list[dict[str, Any]]:
    summary = session.scalar(
        select(TeamSeasonSummary).where(
            TeamSeasonSummary.team_id == team.id, TeamSeasonSummary.season == season
        )
    )
    if summary is None:
        return []
    return [
        {
            "type": "team_season_summary",
            "team": _team_name(team),
            "season": season,
            "wins": summary.wins,
            "losses": summary.losses,
            "winPct": _float(summary.win_pct),
            "pointsPerGame": _float(summary.points_per_game),
            "leaders": summary.leaders or {},
            "source": "database",
        }
    ]


def team_leader(
    session: Session, team: Team, season: str, stat: str | None
) -> list[dict[str, Any]]:
    summary = session.scalar(
        select(TeamSeasonSummary).where(
            TeamSeasonSummary.team_id == team.id, TeamSeasonSummary.season == season
        )
    )
    metric = f"{stat}_per_game" if stat else "points_per_game"
    leader = (summary.leaders or {}).get(metric) if summary else None
    if not isinstance(leader, dict) or not isinstance(leader.get("player_id"), int):
        return []
    player = session.get(Player, leader["player_id"])
    if player is None:
        return []
    return [
        {
            "type": "team_leader",
            "team": _team_name(team),
            "player": player.full_name,
            "season": season,
            "stat": metric,
            "value": leader.get("value"),
            "source": "database",
        }
    ]


def standings(
    session: Session, season: str, conference: str | None, limit: int | None
) -> list[dict[str, Any]]:
    statement = (
        select(StandingsSnapshot, Team)
        .join(Team, StandingsSnapshot.team_id == Team.id)
        .where(
            StandingsSnapshot.season == season,
            StandingsSnapshot.snapshot_type.in_(("final_regular_season", "current")),
        )
        .order_by(StandingsSnapshot.rank)
    )
    if conference:
        statement = statement.where(
            StandingsSnapshot.conference.in_((conference, f"{conference}ern"))
        )
    rows = session.execute(statement).all()
    seen: set[int] = set()
    output = []
    for row, team in rows:
        if team.id in seen:
            continue
        seen.add(team.id)
        output.append(
            {
                "type": "standings",
                "team": _team_name(team),
                "conference": row.conference,
                "rank": row.rank,
                "wins": row.wins,
                "losses": row.losses,
                "season": season,
                "source": "database",
            }
        )
        if limit and len(output) >= limit:
            break
    return output


def roster(session: Session, team: Team, season: str) -> list[dict[str, Any]]:
    rows = list(
        session.execute(
            select(RosterMembership, Player)
            .join(Player, RosterMembership.player_id == Player.id)
            .where(RosterMembership.team_id == team.id, RosterMembership.season == season)
            .order_by(Player.full_name)
        ).all()
    )
    return [
        {
            "type": "roster",
            "team": _team_name(team),
            "player": player.full_name,
            "position": membership.position or player.position,
            "status": membership.roster_status,
            "season": season,
            "source": "database",
        }
        for membership, player in rows
    ]


def compare(session: Session, players: list[Player], season: str) -> list[dict[str, Any]]:
    output = []
    for player in players:
        output.extend(player_season_stats(session, player, season))
    return output


def similar(session: Session, player: Player, season: str, limit: int = 5) -> list[dict[str, Any]]:
    target = session.scalar(
        select(PlayerSeasonSummary).where(
            PlayerSeasonSummary.player_id == player.id, PlayerSeasonSummary.season == season
        )
    )
    if target is None:
        return []
    rows = list(
        session.execute(
            select(PlayerSeasonSummary, Player)
            .join(Player, PlayerSeasonSummary.player_id == Player.id)
            .where(PlayerSeasonSummary.season == season, PlayerSeasonSummary.player_id != player.id)
        ).all()
    )
    metrics = (
        "points_per_game",
        "rebounds_per_game",
        "assists_per_game",
        "true_shooting_percentage",
    )

    def distance(summary: PlayerSeasonSummary) -> float:
        return sum(
            ((_float(getattr(summary, metric)) or 0) - (_float(getattr(target, metric)) or 0)) ** 2
            for metric in metrics
        )

    rows.sort(key=lambda row: (distance(row[0]), row[1].full_name))
    return [
        {
            "type": "similar_player",
            "player": candidate.full_name,
            "comparedTo": player.full_name,
            "season": season,
            "distance": round(distance(summary), 6),
            "source": "database",
        }
        for summary, candidate in rows[:limit]
    ]


def available_seasons(session: Session) -> list[str]:
    return sorted(set(session.scalars(select(PlayerSeasonSummary.season))), reverse=True)


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _team_name(team: Team | None) -> str | None:
    return f"{team.city} {team.name}" if team else None
