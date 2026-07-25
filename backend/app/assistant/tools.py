from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.analytics.awards_predictor import SUPPORTED_AWARDS, predict_awards
from app.analytics.standings_predictor import predict_standings
from app.models import (
    AwardHistory,
    Player,
    PlayerSeasonSummary,
    Prediction,
    Team,
    TeamSeasonStat,
)


def list_capabilities(session: Session) -> dict[str, Any]:
    seasons = sorted(
        {
            value
            for value in session.scalars(select(PlayerSeasonSummary.season))
            if value is not None
        },
        reverse=True,
    )
    return {
        "capabilities": [
            "Search stored players and teams",
            "Compare player season summaries",
            "Explain player efficiency, trends, splits, and benchmarks",
            "Project NBA awards with transparent weighted scoring",
            "Project conference or league standings from stored roster data",
            "Inspect saved prediction runs and their feature attributions",
        ],
        "available_seasons": seasons,
        "supported_awards": sorted(SUPPORTED_AWARDS),
        "grounding": (
            "Answers use only stored HoopsIQ records or deterministic predictions "
            "computed from those records."
        ),
    }


def get_player(session: Session, name: str, season: str | None = None) -> dict[str, Any]:
    player = _find_player(session, name)
    if player is None:
        return {"found": False, "query": name, "message": "Player is not in the database."}
    summary = _player_summary(session, player.id, season)
    return {
        "found": True,
        "player": {
            "id": player.id,
            "nba_player_id": player.nba_player_id,
            "full_name": player.full_name,
            "position": player.position,
            "height": player.height,
            "weight_pounds": player.weight_pounds,
            "birthdate": player.birthdate.isoformat() if player.birthdate else None,
            "team": _team_payload(player.team),
            "active": player.active,
        },
        "summary": _summary_payload(summary),
    }


def get_team(
    session: Session,
    name_or_abbreviation: str,
    season: str | None = None,
) -> dict[str, Any]:
    team = _find_team(session, name_or_abbreviation)
    if team is None:
        return {
            "found": False,
            "query": name_or_abbreviation,
            "message": "Team is not in the database.",
        }
    resolved_season = season or _latest_season(session)
    roster_rows = session.execute(
        select(Player, PlayerSeasonSummary)
        .join(PlayerSeasonSummary, PlayerSeasonSummary.player_id == Player.id)
        .where(
            PlayerSeasonSummary.team_id == team.id,
            PlayerSeasonSummary.season == resolved_season,
        )
        .order_by(PlayerSeasonSummary.minutes_per_game.desc(), Player.full_name)
    ).all()
    team_stat = session.scalar(
        select(TeamSeasonStat).where(
            TeamSeasonStat.team_id == team.id,
            TeamSeasonStat.season == resolved_season,
        )
    )
    return {
        "found": True,
        "team": _team_payload(team),
        "season": resolved_season,
        "record": (
            {"wins": team_stat.wins, "losses": team_stat.losses}
            if team_stat is not None
            else None
        ),
        "roster": [
            {
                "nba_player_id": player.nba_player_id,
                "full_name": player.full_name,
                "position": player.position,
                "minutes_per_game": _float(summary.minutes_per_game),
                "points_per_game": _float(summary.points_per_game),
            }
            for player, summary in roster_rows
        ],
        "data_note": (
            None
            if team_stat is not None
            else f"No completed team record is stored for {resolved_season}."
        ),
    }


def compare_players(
    session: Session,
    names: list[str],
    season: str | None = None,
) -> dict[str, Any]:
    if len(names) < 2:
        return {"found": False, "message": "Two player names are required for comparison."}
    resolved_season = season or _latest_season(session)
    players = [get_player(session, name, resolved_season) for name in names[:4]]
    missing = [names[index] for index, player in enumerate(players) if not player["found"]]
    return {
        "found": not missing,
        "season": resolved_season,
        "players": players,
        "missing_players": missing,
    }


def get_award_history(
    session: Session,
    award_type: str,
    season: str | None = None,
) -> dict[str, Any]:
    normalized = award_type.strip().upper().replace(" ", "_")
    statement = (
        select(AwardHistory, Player, Team)
        .outerjoin(Player, AwardHistory.player_id == Player.id)
        .outerjoin(Team, AwardHistory.team_id == Team.id)
        .where(AwardHistory.award_type == normalized)
        .order_by(AwardHistory.season.desc())
    )
    if season:
        statement = statement.where(AwardHistory.season == season)
    rows = session.execute(statement).all()
    return {
        "award_type": normalized,
        "season": season,
        "results": [
            {
                "season": award.season,
                "player": player.full_name if player else None,
                "team": f"{team.city} {team.name}" if team else None,
                "voting_share": _float(award.voting_share),
                "is_synthetic": award.is_synthetic,
                "data_source": award.data_source,
            }
            for award, player, team in rows
        ],
        "message": None if rows else "No matching award history is stored.",
    }


def predict_award(
    session: Session,
    award_type: str,
    season: str,
    limit: int = 10,
) -> dict[str, Any]:
    return predict_awards(session, season, award_type, limit=limit).as_dict()


def predict_league_standings(
    session: Session,
    season: str,
    conference: str | None = None,
) -> dict[str, Any]:
    return predict_standings(session, season, conference).as_dict()


def list_predictions(session: Session, limit: int = 20) -> dict[str, Any]:
    rows = session.scalars(
        select(Prediction).order_by(Prediction.created_at.desc()).limit(limit)
    ).all()
    return {
        "predictions": [
            {
                "id": prediction.id,
                "created_at": prediction.created_at.isoformat(),
                "target_season": prediction.target_season,
                "prediction_type": prediction.prediction_type,
                "model_version": prediction.model_version,
                "notes": prediction.notes,
                "payload": prediction.payload,
            }
            for prediction in rows
        ]
    }


def search(session: Session, query: str, limit: int = 10) -> dict[str, Any]:
    normalized = f"%{query.strip()}%"
    players = session.scalars(
        select(Player)
        .options(joinedload(Player.team))
        .where(Player.full_name.ilike(normalized))
        .order_by(Player.full_name)
        .limit(limit)
    ).all()
    teams = session.scalars(
        select(Team)
        .where(
            or_(
                Team.name.ilike(normalized),
                Team.city.ilike(normalized),
                Team.abbreviation.ilike(normalized),
            )
        )
        .order_by(Team.city, Team.name)
        .limit(limit)
    ).all()
    return {
        "query": query,
        "players": [
            {
                "nba_player_id": player.nba_player_id,
                "full_name": player.full_name,
                "position": player.position,
                "team": _team_payload(player.team),
            }
            for player in players
        ],
        "teams": [_team_payload(team) for team in teams],
    }


def execute_tool(session: Session, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "get_player":
        return get_player(
            session,
            str(arguments["name"]),
            _optional_string(arguments.get("season")),
        )
    if name == "get_team":
        return get_team(
            session,
            str(arguments["name_or_abbr"]),
            _optional_string(arguments.get("season")),
        )
    if name == "compare_players":
        names = [str(value) for value in arguments.get("names", [])]
        return compare_players(session, names, _optional_string(arguments.get("season")))
    if name == "get_award_history":
        return get_award_history(
            session,
            str(arguments["award_type"]),
            _optional_string(arguments.get("season")),
        )
    if name == "predict_award":
        return predict_award(
            session,
            str(arguments["award_type"]),
            str(arguments["season"]),
            int(arguments.get("limit", 10)),
        )
    if name == "predict_standings":
        return predict_league_standings(
            session,
            str(arguments["season"]),
            _optional_string(arguments.get("conference")),
        )
    if name == "list_capabilities":
        return list_capabilities(session)
    if name == "search":
        return search(session, str(arguments["query"]))
    raise ValueError(f"Unknown assistant tool '{name}'.")


def _find_player(session: Session, name: str) -> Player | None:
    normalized = name.strip()
    exact = session.scalar(
        select(Player)
        .options(joinedload(Player.team))
        .where(Player.full_name.ilike(normalized))
    )
    if exact is not None:
        return exact
    candidates = session.scalars(
        select(Player).options(joinedload(Player.team)).order_by(Player.full_name)
    ).unique()
    scored = sorted(
        (
            (SequenceMatcher(None, normalized.lower(), player.full_name.lower()).ratio(), player)
            for player in candidates
        ),
        key=lambda item: (-item[0], item[1].full_name),
    )
    return scored[0][1] if scored and scored[0][0] >= 0.55 else None


def _find_team(session: Session, value: str) -> Team | None:
    normalized = value.strip()
    exact = session.scalar(
        select(Team).where(
            or_(
                Team.abbreviation.ilike(normalized),
                Team.name.ilike(normalized),
                (Team.city + " " + Team.name).ilike(normalized),
            )
        )
    )
    if exact is not None:
        return exact
    candidates = session.scalars(select(Team).order_by(Team.city, Team.name)).all()
    scored = sorted(
        (
            (
                max(
                    SequenceMatcher(None, normalized.lower(), team.name.lower()).ratio(),
                    SequenceMatcher(
                        None,
                        normalized.lower(),
                        f"{team.city} {team.name}".lower(),
                    ).ratio(),
                ),
                team,
            )
            for team in candidates
        ),
        key=lambda item: (-item[0], item[1].name),
    )
    return scored[0][1] if scored and scored[0][0] >= 0.5 else None


def _player_summary(
    session: Session,
    player_id: int,
    season: str | None,
) -> PlayerSeasonSummary | None:
    statement = select(PlayerSeasonSummary).where(PlayerSeasonSummary.player_id == player_id)
    if season:
        statement = statement.where(PlayerSeasonSummary.season == season)
    else:
        statement = statement.order_by(PlayerSeasonSummary.season.desc())
    return session.scalar(statement)


def _summary_payload(summary: PlayerSeasonSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "season": summary.season,
        "games_played": summary.games_played,
        "minutes_per_game": _float(summary.minutes_per_game),
        "points_per_game": _float(summary.points_per_game),
        "rebounds_per_game": _float(summary.rebounds_per_game),
        "assists_per_game": _float(summary.assists_per_game),
        "turnovers_per_game": _float(summary.turnovers_per_game),
        "plus_minus_per_game": _float(summary.plus_minus_per_game),
        "true_shooting_percentage": _float(summary.true_shooting_percentage),
        "production_trend": summary.production_trend,
        "efficiency_trend": summary.efficiency_trend,
        "position_percentiles": summary.position_percentiles or {},
        "data_source": summary.data_source,
        "is_synthetic": summary.is_synthetic,
    }


def _team_payload(team: Team | None) -> dict[str, Any] | None:
    if team is None:
        return None
    return {
        "id": team.id,
        "nba_team_id": team.nba_team_id,
        "name": f"{team.city} {team.name}",
        "abbreviation": team.abbreviation,
        "conference": team.conference,
        "division": team.division,
        "arena": team.arena,
        "head_coach": team.head_coach,
    }


def _latest_season(session: Session) -> str:
    season = session.scalar(
        select(PlayerSeasonSummary.season).order_by(PlayerSeasonSummary.season.desc()).limit(1)
    )
    if season is None:
        raise ValueError("No player season data is stored.")
    return season


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
