from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.schemas import (
    ErrorResponse,
    PlayoffGameResponse,
    PlayoffPlayerBoxScoreResponse,
    PlayoffRoundResponse,
    PlayoffSeriesResponse,
    PlayoffTeamBoxScoreResponse,
    TeamResponse,
)
from app.db.session import get_db_session
from app.models import (
    PlayoffGame,
    PlayoffPlayerBoxScore,
    PlayoffSeries,
    PlayoffTeamBoxScore,
    Team,
)
from app.services.seasons import get_available_seasons, validate_season

router = APIRouter(tags=["playoffs"], responses={404: {"model": ErrorResponse}})


@router.get(
    "/playoffs/{season}/rounds/{round_slug}",
    response_model=PlayoffRoundResponse,
    summary="Get stored playoff box scores",
    description=(
        "Returns persisted playoff series, official team totals, and supplied player "
        "box-score lines. Coverage fields make incomplete source files explicit."
    ),
)
async def playoff_round(
    season: Annotated[str, Path(pattern=r"^\d{4}-\d{2}$")],
    round_slug: Annotated[str, Path(pattern=r"^[a-z0-9-]+$")],
    session: Annotated[Session, Depends(get_db_session)],
) -> PlayoffRoundResponse:
    try:
        season = validate_season(season)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Season {season} is not available. Available seasons: "
                f"{', '.join(get_available_seasons())}."
            ),
        ) from exc
    round_name = round_slug.replace("-", " ").title()
    rows = session.scalars(
        select(PlayoffSeries)
        .options(
            joinedload(PlayoffSeries.winner_team),
            joinedload(PlayoffSeries.loser_team),
            selectinload(PlayoffSeries.games).joinedload(PlayoffGame.home_team),
            selectinload(PlayoffSeries.games).joinedload(PlayoffGame.away_team),
            selectinload(PlayoffSeries.games)
            .selectinload(PlayoffGame.team_box_scores)
            .joinedload(PlayoffTeamBoxScore.team),
            selectinload(PlayoffSeries.games).selectinload(PlayoffGame.player_box_scores),
        )
        .where(
            PlayoffSeries.season == season,
            PlayoffSeries.round_name == round_name,
        )
        .order_by(PlayoffSeries.conference, PlayoffSeries.id)
    ).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No stored {round_name} box scores are available for {season}.",
        )

    stored_games = sum(len(item.games) for item in rows)
    expected_games = 48 if season == "2025-26" and round_name == "First Round" else stored_games
    return PlayoffRoundResponse(
        season=season,
        round=round_name,
        stored_series=len(rows),
        stored_games=stored_games,
        expected_games=expected_games,
        coverage_complete=stored_games == expected_games,
        data_source=rows[0].data_source,
        series=[_series_response(item) for item in rows],
    )


def _series_response(series: PlayoffSeries) -> PlayoffSeriesResponse:
    return PlayoffSeriesResponse(
        id=series.id,
        conference=series.conference,
        winner=_team_response(series.winner_team),
        loser=_team_response(series.loser_team),
        winner_wins=series.winner_wins,
        loser_wins=series.loser_wins,
        games=[_game_response(game) for game in series.games],
    )


def _game_response(game: PlayoffGame) -> PlayoffGameResponse:
    team_boxes = sorted(game.team_box_scores, key=lambda item: item.team.abbreviation)
    players_by_team: dict[int, list[PlayoffPlayerBoxScore]] = {}
    for player in game.player_box_scores:
        players_by_team.setdefault(player.team_id, []).append(player)
    return PlayoffGameResponse(
        id=game.id,
        game_number=game.game_number,
        home_team=_team_response(game.home_team),
        away_team=_team_response(game.away_team),
        home_score=game.home_score,
        away_score=game.away_score,
        overtime=game.overtime,
        data_note=game.data_note,
        team_box_scores=[
            PlayoffTeamBoxScoreResponse(
                team=_team_response(box.team),
                points=box.points,
                rebounds=box.rebounds,
                assists=box.assists,
                steals=box.steals,
                blocks=box.blocks,
                turnovers=box.turnovers,
                field_goals_made=box.field_goals_made,
                field_goals_attempted=box.field_goals_attempted,
                three_pointers_made=box.three_pointers_made,
                three_pointers_attempted=box.three_pointers_attempted,
                free_throws_made=box.free_throws_made,
                free_throws_attempted=box.free_throws_attempted,
                players=[
                    _player_response(player)
                    for player in sorted(
                        players_by_team.get(box.team_id, []),
                        key=lambda item: (-item.points, item.player_name),
                    )
                ],
            )
            for box in team_boxes
        ],
    )


def _player_response(player: PlayoffPlayerBoxScore) -> PlayoffPlayerBoxScoreResponse:
    return PlayoffPlayerBoxScoreResponse(
        player_id=player.player_id,
        player_name=player.player_name,
        points=player.points,
        rebounds=player.rebounds,
        assists=player.assists,
        steals=player.steals,
        blocks=player.blocks,
        turnovers=player.turnovers,
        field_goals_made=player.field_goals_made,
        field_goals_attempted=player.field_goals_attempted,
        three_pointers_made=player.three_pointers_made,
        three_pointers_attempted=player.three_pointers_attempted,
        free_throws_made=player.free_throws_made,
        free_throws_attempted=player.free_throws_attempted,
        plus_minus=player.plus_minus,
    )


def _team_response(team: Team) -> TeamResponse:
    return TeamResponse.model_validate(team)
