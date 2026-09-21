from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AwardHistory, PlayerSeasonSummary, RosterMembership, TeamSeasonSummary

ALL_NBA_FEATURES = (
    "games_played",
    "minutes_per_game",
    "points_per_game",
    "rebounds_per_game",
    "assists_per_game",
    "steals_per_game",
    "blocks_per_game",
    "turnovers_per_game",
    "true_shooting_percentage",
    "effective_field_goal_percentage",
    "usage_rate",
    "team_wins",
    "team_win_pct",
    "team_conference_rank",
    "prior_all_nba_count",
    "previous_season_ppg",
    "previous_season_games_played",
    "previous_season_team_wins",
)
STANDINGS_FEATURES = (
    "previous_season_wins",
    "previous_season_losses",
    "previous_season_win_pct",
    "previous_season_net_rating",
    "previous_season_offensive_rating",
    "previous_season_defensive_rating",
    "previous_season_pace",
    "returning_minutes_percentage",
    "returning_points_percentage",
    "returning_rebounds_percentage",
    "returning_assists_percentage",
    "average_roster_age",
    "top_player_ppg",
    "top_player_minutes",
    "projected_roster_continuity_score",
    "injury_risk_proxy",
    "conference_strength_proxy",
)
FINALS_FEATURES = (
    "predicted_wins",
    "predicted_conference_rank",
    "playoff_probability",
    "prior_season_wins",
    "prior_season_net_rating",
    "top_player_strength",
    "roster_continuity",
    "offensive_rating",
    "defensive_rating",
    "conference_strength",
    "number_of_elite_players",
    "recent_playoff_success",
)
MINIMUM_GAMES = 40
MINIMUM_MINUTES_PER_GAME = 20.0


@dataclass(frozen=True)
class FeatureRow:
    entity_id: int
    entity_name: str
    feature_season: str
    label_season: str
    values: dict[str, float | None]
    warnings: tuple[str, ...] = ()
    group: str | None = None


def all_nba_rows(
    session: Session, label_season: str, feature_season: str | None = None
) -> list[FeatureRow]:
    source = feature_season or label_season
    previous = previous_season(source)
    previous_summaries = {
        row.player_id: row
        for row in session.scalars(
            select(PlayerSeasonSummary).where(PlayerSeasonSummary.season == previous)
        )
    }
    team_summaries = {
        row.team_id: row
        for row in session.scalars(
            select(TeamSeasonSummary).where(TeamSeasonSummary.season == source)
        )
    }
    previous_teams = {
        row.team_id: row
        for row in session.scalars(
            select(TeamSeasonSummary).where(TeamSeasonSummary.season == previous)
        )
    }
    prior_counts: dict[int, int] = {
        int(player_id): int(count)
        for player_id, count in session.execute(
            select(AwardHistory.player_id, func.count(AwardHistory.id))
            .where(AwardHistory.award_type.like("ALL_NBA%"), AwardHistory.season < label_season)
            .group_by(AwardHistory.player_id)
        ).all()
        if player_id is not None
    }
    rows = []
    for summary in session.scalars(
        select(PlayerSeasonSummary)
        .where(PlayerSeasonSummary.season == source)
        .order_by(PlayerSeasonSummary.player_id)
    ):
        if (
            summary.games_played < MINIMUM_GAMES
            or (number(summary.minutes_per_game) or 0) < MINIMUM_MINUTES_PER_GAME
        ):
            continue
        prior = previous_summaries.get(summary.player_id)
        team = team_summaries.get(summary.team_id or -1)
        prior_team = previous_teams.get(summary.team_id or -1)
        values = {
            "games_played": float(summary.games_played),
            "minutes_per_game": number(summary.minutes_per_game),
            "points_per_game": number(summary.points_per_game),
            "rebounds_per_game": number(summary.rebounds_per_game),
            "assists_per_game": number(summary.assists_per_game),
            "steals_per_game": number(summary.steals_per_game),
            "blocks_per_game": number(summary.blocks_per_game),
            "turnovers_per_game": number(summary.turnovers_per_game),
            "true_shooting_percentage": number(summary.true_shooting_percentage),
            "effective_field_goal_percentage": number(summary.effective_field_goal_percentage),
            "usage_rate": number(summary.usage_rate),
            "team_wins": number(team.wins if team else None),
            "team_win_pct": number(team.win_pct if team else None),
            "team_conference_rank": number(team.conference_rank if team else None),
            "prior_all_nba_count": float(prior_counts.get(summary.player_id, 0)),
            "previous_season_ppg": number(prior.points_per_game if prior else None),
            "previous_season_games_played": number(prior.games_played if prior else None),
            "previous_season_team_wins": number(prior_team.wins if prior_team else None),
        }
        warnings = tuple(name for name, value in values.items() if value is None)
        rows.append(
            FeatureRow(
                summary.player_id, summary.player.full_name, source, label_season, values, warnings
            )
        )
    return rows


def projected_active_player_ids(session: Session) -> set[int]:
    return set(
        session.scalars(
            select(RosterMembership.player_id).where(
                RosterMembership.season == "2026-27",
                RosterMembership.roster_status.in_(("active", "two_way")),
            )
        )
    )


def standings_rows(
    session: Session, label_season: str, feature_season: str | None = None
) -> list[FeatureRow]:
    source = feature_season or previous_season(label_season)
    team_rows = list(
        session.scalars(
            select(TeamSeasonSummary)
            .where(TeamSeasonSummary.season == source)
            .order_by(TeamSeasonSummary.team_id)
        )
    )
    player_rows = list(
        session.scalars(select(PlayerSeasonSummary).where(PlayerSeasonSummary.season == source))
    )
    projected_by_team: dict[int, set[int]] = {}
    for membership in session.scalars(
        select(RosterMembership).where(
            RosterMembership.season == label_season,
            RosterMembership.roster_status.in_(("active", "two_way")),
        )
    ):
        projected_by_team.setdefault(membership.team_id, set()).add(membership.player_id)
    conference_wins: dict[str, list[float]] = {}
    for row in team_rows:
        if row.conference:
            conference_wins.setdefault(row.conference, []).append(number(row.wins) or 0)
    output = []
    for team in team_rows:
        players = [row for row in player_rows if row.team_id == team.team_id]
        total_minutes = sum(
            (number(row.minutes_per_game) or 0) * row.games_played for row in players
        )
        projected_ids = projected_by_team.get(team.team_id)
        returning = (
            [row for row in players if row.player_id in projected_ids]
            if projected_ids
            else [row for row in players if row.games_played >= 10]
        )
        returning_minutes = sum(
            (number(row.minutes_per_game) or 0) * row.games_played for row in returning
        )
        total_points = sum((number(row.points_per_game) or 0) * row.games_played for row in players)
        total_rebounds = sum(
            (number(row.rebounds_per_game) or 0) * row.games_played for row in players
        )
        total_assists = sum(
            (number(row.assists_per_game) or 0) * row.games_played for row in players
        )
        top = max(players, key=lambda row: number(row.points_per_game) or 0, default=None)
        conference = conference_wins.get(team.conference or "", [])
        values = {
            "previous_season_wins": number(team.wins),
            "previous_season_losses": number(team.losses),
            "previous_season_win_pct": number(team.win_pct),
            "previous_season_net_rating": number(team.net_rating),
            "previous_season_offensive_rating": number(team.offensive_rating),
            "previous_season_defensive_rating": number(team.defensive_rating),
            "previous_season_pace": number(team.pace),
            "returning_minutes_percentage": ratio(returning_minutes, total_minutes),
            "returning_points_percentage": ratio(
                sum((number(row.points_per_game) or 0) * row.games_played for row in returning),
                total_points,
            ),
            "returning_rebounds_percentage": ratio(
                sum((number(row.rebounds_per_game) or 0) * row.games_played for row in returning),
                total_rebounds,
            ),
            "returning_assists_percentage": ratio(
                sum((number(row.assists_per_game) or 0) * row.games_played for row in returning),
                total_assists,
            ),
            "average_roster_age": None,
            "top_player_ppg": number(top.points_per_game if top else None),
            "top_player_minutes": number(top.minutes_per_game if top else None),
            "projected_roster_continuity_score": ratio(returning_minutes, total_minutes),
            "injury_risk_proxy": None,
            "conference_strength_proxy": sum(conference) / len(conference) if conference else None,
        }
        output.append(
            FeatureRow(
                team.team_id,
                team.team.name,
                source,
                label_season,
                values,
                tuple(name for name, value in values.items() if value is None),
                team.conference,
            )
        )
    return output


def finals_rows(
    session: Session, label_season: str, feature_season: str | None = None
) -> list[FeatureRow]:
    source = feature_season or previous_season(label_season)
    standings = standings_rows(session, label_season, source)
    output = []
    for row in standings:
        values = {
            "predicted_wins": row.values["previous_season_wins"],
            "predicted_conference_rank": None,
            "playoff_probability": 1.0 if (row.values["previous_season_wins"] or 0) >= 40 else 0.0,
            "prior_season_wins": row.values["previous_season_wins"],
            "prior_season_net_rating": row.values["previous_season_net_rating"],
            "top_player_strength": row.values["top_player_ppg"],
            "roster_continuity": row.values["projected_roster_continuity_score"],
            "offensive_rating": row.values["previous_season_offensive_rating"],
            "defensive_rating": row.values["previous_season_defensive_rating"],
            "conference_strength": row.values["conference_strength_proxy"],
            "number_of_elite_players": None,
            "recent_playoff_success": None,
        }
        output.append(
            FeatureRow(
                row.entity_id,
                row.entity_name,
                source,
                label_season,
                values,
                tuple(name for name, value in values.items() if value is None),
                row.group,
            )
        )
    return output


def previous_season(season: str) -> str:
    start = int(season[:4]) - 1
    return f"{start}-{str(start + 1)[-2:]}"


def number(value: Any) -> float | None:
    return float(value) if value is not None else None


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0 else None
