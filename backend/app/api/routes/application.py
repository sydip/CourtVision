from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any, Literal, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.analytics.efficiency import calculate_true_shooting
from app.analytics.rolling import calculate_rolling_averages
from app.analytics.similarity import (
    PlayerFeatureRow,
    compute_feature_values,
    rank_similar_players,
)
from app.analytics.splits import calculate_home_away_splits, categorize_rest_days
from app.analytics.types import GameLog, SplitSummary
from app.api.schemas import (
    ApiMetadata,
    BenchmarksResponse,
    CompareMetricResponse,
    ComparePlayerResponse,
    CompareResponse,
    DraftPickResponse,
    DraftResponse,
    ErrorResponse,
    GameLogItem,
    PageMeta,
    PaginatedGameLogsResponse,
    PaginatedPlayersResponse,
    PlayerDetail,
    PlayerListItem,
    PlayerReportResponse,
    PlayerSeasonSummariesResponse,
    PlayerSeasonSummaryResponse,
    PlayerSplitsResponse,
    PositionsResponse,
    RecentWindowResponse,
    ReportSectionResponse,
    ReportSentenceResponse,
    RestSplitsResponse,
    RollingTrendPointResponse,
    RosterMemberResponse,
    SeasonItemResponse,
    SeasonsResponse,
    SimilarFeatureComparison,
    SimilarPlayerResponse,
    SimilarPlayersResponse,
    SplitResponse,
    StandingRowResponse,
    StandingsResponse,
    TeamDetailResponse,
    TeamResponse,
    TeamRosterResponse,
    TeamSeasonSummaryApiResponse,
    TeamsResponse,
    TrendsResponse,
)
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models import (
    DraftPick,
    Game,
    Player,
    PlayerGameStat,
    PlayerSeasonSummary,
    RosterMembership,
    StandingsSnapshot,
    SyncRun,
    Team,
    TeamSeasonSummary,
)
from app.services.seasons import (
    PREDICTION_SEASON,
    get_available_seasons,
    get_default_season,
    list_seasons,
    player_has_season,
    team_has_season,
    validate_season,
)

router = APIRouter(tags=["application"], responses={404: {"model": ErrorResponse}})


@router.get(
    "/seasons",
    response_model=SeasonsResponse,
    summary="List seasons",
    description=(
        "Returns every historical data season and the supported prediction season."
    ),
)
async def seasons(session: Annotated[Session, Depends(get_db_session)]) -> SeasonsResponse:
    rows = [row for row in list_seasons(session) if row.season != PREDICTION_SEASON]
    return SeasonsResponse(
        seasons=[row.season for row in reversed(rows)],
        data=[
            SeasonItemResponse(
                season=row.season,
                displayName=row.display_name,
                isCompleted=row.is_completed,
                isCurrent=row.is_current,
                supportsPredictions=row.supports_predictions,
                supportsJordanPredictions=row.supports_jordan_predictions,
            )
            for row in rows
        ],
    )


@router.get(
    "/teams",
    response_model=TeamsResponse,
    summary="List teams",
    description="Returns stored NBA teams ordered by abbreviation.",
)
async def teams(
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query(description="Season in YYYY-YY format.")] = None,
) -> TeamsResponse:
    selected = _resolve_season_or_400(season)
    rows = _teams_for_season(session, selected)
    return TeamsResponse(
        teams=[_team_response(team) for team in rows], meta=_api_meta(session, selected)
    )


@router.get(
    "/drafts/{draft_year}",
    response_model=DraftResponse,
    summary="Get NBA draft results",
    description=(
        "Returns persisted draft selections using the team that ultimately received "
        "each player after draft-night trades."
    ),
)
async def draft_results(
    draft_year: Annotated[int, Path(ge=1947, le=2100)],
    session: Annotated[Session, Depends(get_db_session)],
    round_number: Annotated[int | None, Query(alias="round", ge=1, le=2)] = None,
) -> DraftResponse:
    statement = (
        select(DraftPick)
        .options(joinedload(DraftPick.team))
        .where(DraftPick.draft_year == draft_year)
        .order_by(DraftPick.overall_pick)
    )
    if round_number is not None:
        statement = statement.where(DraftPick.round == round_number)
    rows = session.scalars(statement).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No stored draft results are available for {draft_year}.",
        )
    return DraftResponse(
        draft_year=draft_year,
        event_dates="June 23-24, 2026" if draft_year == 2026 else "Not stored",
        venue="Barclays Center" if draft_year == 2026 else "Not stored",
        location="Brooklyn, New York" if draft_year == 2026 else "Not stored",
        total_picks=len(rows),
        picks=[
            DraftPickResponse(
                id=pick.id,
                draft_year=pick.draft_year,
                round=pick.round,
                overall_pick=pick.overall_pick,
                player_name=pick.player_name,
                school_country=pick.school_country,
                team=_team_response(pick.team),
                transaction_note=pick.transaction_note,
            )
            for pick in rows
        ],
        data_source=rows[0].data_source,
    )


@router.get(
    "/positions",
    response_model=PositionsResponse,
    summary="List player positions",
    description="Returns distinct non-empty positions for stored players.",
)
async def positions(session: Annotated[Session, Depends(get_db_session)]) -> PositionsResponse:
    rows = session.scalars(
        select(Player.position)
        .where(Player.position.is_not(None), Player.position != "")
        .distinct()
        .order_by(Player.position)
    ).all()
    return PositionsResponse(positions=[position for position in rows if position is not None])


@router.get(
    "/players",
    response_model=PaginatedPlayersResponse,
    summary="Search players",
    description="Searches players by partial, case-insensitive full name with pagination.",
)
async def players(
    session: Annotated[Session, Depends(get_db_session)],
    q: Annotated[str | None, Query(description="Partial player name search.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum players to return.")] = 25,
    offset: Annotated[int, Query(ge=0, description="Number of players to skip.")] = 0,
    season: Annotated[str | None, Query(description="Season in YYYY-YY format.")] = None,
) -> PaginatedPlayersResponse:
    selected = _resolve_season_or_400(season)
    conditions = [_player_season_exists(selected)]
    if q:
        conditions.append(Player.full_name.ilike(f"%{q.strip()}%"))
    total = _count(session, Player, conditions)
    rows = session.scalars(
        select(Player)
        .options(joinedload(Player.team))
        .where(*conditions)
        .order_by(Player.full_name)
        .limit(limit)
        .offset(offset)
    ).all()
    return PaginatedPlayersResponse(
        items=[_player_list_item_for_season(session, player, selected) for player in rows],
        meta=_page_meta(limit, offset, total).model_copy(
            update=_api_meta(session, selected).model_dump()
        ),
    )


@router.get(
    "/players/{player_id}",
    response_model=PlayerDetail,
    summary="Get player",
    description="Returns one player by internal ID or NBA player ID.",
)
async def player_detail(
    player_id: Annotated[int, Path(gt=0, description="Internal player ID or NBA player ID.")],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query(description="Season in YYYY-YY format.")] = None,
) -> PlayerDetail:
    selected = _resolve_season_or_400(season)
    player = _get_player_or_404(session, player_id)
    _ensure_player_has_season(session, player, selected)
    membership = _season_membership(session, player.id, selected)
    detail = _player_detail(player).model_copy(
        update={
            "team": _season_team_response(session, player.id, selected),
            "position": membership.position
            if membership and membership.position
            else player.position,
            "jersey_number": (
                membership.jersey_number
                if membership and membership.jersey_number
                else player.jersey_number
            ),
            "meta": _api_meta(session, selected),
        }
    )
    return detail


@router.get(
    "/seasons/{season}/summaries",
    response_model=PlayerSeasonSummariesResponse,
    summary="List player season summaries",
    description="Returns stored season summaries for every player with data in the given season.",
)
async def season_summaries(
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
) -> PlayerSeasonSummariesResponse:
    _resolve_season_or_400(season)
    rows = session.execute(
        select(PlayerSeasonSummary, Player)
        .join(Player, PlayerSeasonSummary.player_id == Player.id)
        .where(PlayerSeasonSummary.season == season)
    ).all()
    return PlayerSeasonSummariesResponse(
        items=[_summary_response(player, summary) for summary, player in rows]
    )


@router.get(
    "/players/{player_id}/seasons/{season}/summary",
    response_model=PlayerSeasonSummaryResponse,
    summary="Get player season summary",
    description="Returns stored season summary and rebuilt analytics for one player season.",
)
async def player_summary(
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
) -> PlayerSeasonSummaryResponse:
    player = _get_player_or_404(session, player_id)
    summary = _get_summary_or_404(session, player.id, season)
    return _summary_response(player, summary).model_copy(
        update={"meta": _api_meta(session, season)}
    )


@router.get(
    "/players/{player_id}/seasons/{season}/games",
    response_model=PaginatedGameLogsResponse,
    summary="List player game logs",
    description=(
        "Returns filtered, paginated player game logs ordered chronologically "
        "or reverse-chronologically."
    ),
)
async def player_games(
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    location: Annotated[Literal["home", "away"] | None, Query()] = None,
    opponent: Annotated[
        str | None, Query(description="Opponent abbreviation or NBA team ID.")
    ] = None,
    result: Annotated[Literal["W", "L"] | None, Query()] = None,
    sort: Annotated[Literal["asc", "desc"], Query(description="Sort by game date.")] = "asc",
) -> PaginatedGameLogsResponse:
    player = _get_player_or_404(session, player_id)
    _ensure_season_exists_for_player(session, player.id, season)
    home_team = aliased(Team)
    away_team = aliased(Team)
    statement = (
        select(PlayerGameStat, Game, home_team, away_team)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .join(home_team, Game.home_team_id == home_team.id)
        .join(away_team, Game.away_team_id == away_team.id)
        .where(PlayerGameStat.player_id == player.id, PlayerGameStat.season == season)
    )
    conditions = _game_log_filter_conditions(
        home_team=home_team,
        away_team=away_team,
        location=location,
        opponent=opponent,
        result=result,
    )
    statement = statement.where(*conditions)
    count_statement = (
        select(func.count())
        .select_from(PlayerGameStat)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .join(home_team, Game.home_team_id == home_team.id)
        .join(away_team, Game.away_team_id == away_team.id)
        .where(
            PlayerGameStat.player_id == player.id,
            PlayerGameStat.season == season,
            *conditions,
        )
    )
    total = session.scalar(count_statement) or 0
    order_columns = (
        (Game.game_date.asc(), Game.nba_game_id.asc())
        if sort == "asc"
        else (Game.game_date.desc(), Game.nba_game_id.desc())
    )
    rows = session.execute(statement.order_by(*order_columns).limit(limit).offset(offset)).all()
    return PaginatedGameLogsResponse(
        items=[
            _game_log_item(stat=stat, game=game, home_team=home, away_team=away)
            for stat, game, home, away in rows
        ],
        meta=_page_meta(limit, offset, total).model_copy(
            update=_api_meta(session, season).model_dump()
        ),
    )


@router.get(
    "/players/{player_id}/seasons/{season}/trends",
    response_model=TrendsResponse,
    summary="Get player trends",
    description=(
        "Returns stored production and efficiency trend classifications and "
        "exact calculation payloads."
    ),
)
async def player_trends(
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
) -> TrendsResponse:
    player = _get_player_or_404(session, player_id)
    summary = _get_summary_or_404(session, player.id, season)
    return TrendsResponse(
        player_id=player.id,
        nba_player_id=player.nba_player_id,
        season=season,
        production_trend=summary.production_trend,
        production_trend_value=_float(summary.production_trend_value),
        efficiency_trend=summary.efficiency_trend,
        efficiency_trend_value=_float(summary.efficiency_trend_value),
        payload=_json_dict(summary.trend_payload),
        meta=_api_meta(session, season),
    )


@router.get(
    "/players/{player_id}/seasons/{season}/splits",
    response_model=PlayerSplitsResponse,
    summary="Get player home/away splits",
    description="Calculates home and away splits from stored game logs only.",
)
async def player_splits(
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
) -> PlayerSplitsResponse:
    player = _get_player_or_404(session, player_id)
    game_logs = _game_logs_for_player(session, player.id, season)
    if not game_logs:
        _raise_not_found("season", season)
    splits = calculate_home_away_splits(game_logs)
    return PlayerSplitsResponse(
        player_id=player.id,
        nba_player_id=player.nba_player_id,
        season=season,
        home=_split_response(splits.get("home")),
        away=_split_response(splits.get("away")),
        meta=_api_meta(session, season),
    )


@router.get(
    "/players/{player_id}/seasons/{season}/benchmarks",
    response_model=BenchmarksResponse,
    summary="Get player benchmarks",
    description="Returns stored league, position, and similar-minutes-tier percentile payloads.",
)
async def player_benchmarks(
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
) -> BenchmarksResponse:
    player = _get_player_or_404(session, player_id)
    summary = _get_summary_or_404(session, player.id, season)
    return _benchmarks_response(player, summary).model_copy(
        update={"meta": _api_meta(session, season)}
    )


@router.get(
    "/players/{player_id}/seasons/{season}/similar",
    response_model=SimilarPlayersResponse,
    summary="Find statistically similar players",
    description=(
        "Ranks stored players by statistical similarity to the selected player. A per-role "
        "feature vector (per-36 scoring, rebounding, playmaking, steals, blocks, turnovers, "
        "true-shooting, usage when available, and minutes) is standardized across the eligible "
        "player pool and compared with cosine similarity. Results describe statistical "
        "resemblance, not identical play style, and use only stored PostgreSQL data."
    ),
)
async def similar_players(
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
    same_position_only: Annotated[bool, Query()] = False,
) -> SimilarPlayersResponse:
    player = _get_player_or_404(session, player_id)
    summary = _get_summary_or_404(session, player.id, season)
    rows = session.execute(
        select(Player, PlayerSeasonSummary)
        .join(PlayerSeasonSummary, PlayerSeasonSummary.player_id == Player.id)
        .options(joinedload(Player.team))
        .where(PlayerSeasonSummary.season == season)
    ).all()

    candidate_index = {candidate.id: (candidate, row) for candidate, row in rows}
    target_row = _feature_row(player, summary)
    candidate_rows = [
        _feature_row(candidate, row) for candidate, row in rows if candidate.id != player.id
    ]

    settings = get_settings()
    results = rank_similar_players(
        target_row,
        candidate_rows,
        minimum_games=settings.similarity_minimum_games,
        minimum_minutes_per_game=settings.similarity_minimum_minutes_per_game,
        same_position_only=same_position_only,
        limit=limit,
    )

    players: list[SimilarPlayerResponse] = []
    for result in results:
        candidate, candidate_summary = candidate_index[result.player_id]
        players.append(
            SimilarPlayerResponse(
                player=_player_list_item(candidate),
                summary=_summary_response(candidate, candidate_summary),
                similarity_score=result.similarity_score,
                shared_position=bool(
                    player.position
                    and candidate.position
                    and player.position.casefold() == candidate.position.casefold()
                ),
                minutes_difference=_absolute_difference(
                    _float(summary.minutes_per_game),
                    _float(candidate_summary.minutes_per_game),
                ),
                shared_strengths=result.shared_strengths,
                largest_differences=result.largest_differences,
                feature_comparisons=[
                    SimilarFeatureComparison(
                        feature=comparison.feature,
                        label=comparison.label,
                        unit=comparison.unit,
                        player_value=comparison.player_value,
                        candidate_value=comparison.candidate_value,
                        difference=comparison.difference,
                    )
                    for comparison in result.feature_comparisons
                ],
            )
        )

    return SimilarPlayersResponse(
        player_id=player.id,
        nba_player_id=player.nba_player_id,
        season=season,
        players=players,
        meta=_api_meta(session, season),
    )


def _feature_row(player: Player, summary: PlayerSeasonSummary) -> PlayerFeatureRow:
    return PlayerFeatureRow(
        player_id=player.id,
        games_played=summary.games_played,
        minutes_per_game=_float(summary.minutes_per_game),
        position=player.position,
        values=compute_feature_values(
            minutes_per_game=_float(summary.minutes_per_game),
            points_per_36=_float(summary.points_per_36),
            rebounds_per_36=_float(summary.rebounds_per_36),
            assists_per_36=_float(summary.assists_per_36),
            turnovers_per_36=_float(summary.turnovers_per_36),
            steals_per_game=_float(summary.steals_per_game),
            blocks_per_game=_float(summary.blocks_per_game),
            true_shooting_percentage=_float(summary.true_shooting_percentage),
            usage_rate=_float(summary.usage_rate),
        ),
    )


@router.get(
    "/compare",
    response_model=CompareResponse,
    summary="Compare players",
    description=(
        "Compares two players for one stored season using only structured PostgreSQL analytics."
    ),
)
async def compare_players(
    session: Annotated[Session, Depends(get_db_session)],
    player_a: Annotated[int, Query(gt=0, description="Internal or NBA ID for player A.")],
    player_b: Annotated[int, Query(gt=0, description="Internal or NBA ID for player B.")],
    season: Annotated[str | None, Query(min_length=4, max_length=16)] = None,
) -> CompareResponse:
    season = _resolve_season_or_400(season)
    if player_a == player_b:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": "Compare requires two different players.",
                }
            },
        )
    first_player = _get_player_or_404(session, player_a)
    second_player = _get_player_or_404(session, player_b)
    first_subject = _compare_subject_response(session, first_player, season)
    second_subject = _compare_subject_response(session, second_player, season)
    first_position = first_player.position or "an unknown position"
    second_position = second_player.position or "an unknown position"
    position_match = bool(
        first_player.position
        and second_player.position
        and first_player.position.casefold() == second_player.position.casefold()
    )
    position_context = (
        f"Both players are listed at {first_player.position}."
        if position_match
        else (
            f"{first_player.full_name} is listed at {first_position} while "
            f"{second_player.full_name} is listed at {second_position}; "
            "position percentile comparisons "
            "should be read in that context."
        )
    )
    return CompareResponse(
        season=season,
        player_a=first_subject,
        player_b=second_subject,
        position_match=position_match,
        position_context=position_context,
        category_winners=_compare_metric_winners(
            first_subject.summary,
            second_subject.summary,
            first_subject.benchmarks,
            second_subject.benchmarks,
            first_subject.recent_5,
            second_subject.recent_5,
            first_subject.recent_10,
            second_subject.recent_10,
        ),
        meta=_api_meta(session, season),
    )


@router.get(
    "/players/{player_id}/seasons/{season}/report",
    response_model=PlayerReportResponse,
    summary="Get deterministic player report",
    description=(
        "Returns a deterministic player report assembled from testable templates. "
        "No route logic calls live data providers or an LLM."
    ),
)
async def player_report(
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[str, Path(min_length=4, max_length=16)],
    session: Annotated[Session, Depends(get_db_session)],
) -> PlayerReportResponse:
    player = _get_player_or_404(session, player_id)
    summary = _get_summary_or_404(session, player.id, season)
    game_logs = _game_logs_for_player(session, player.id, season)
    if not game_logs:
        _raise_not_found("season", season)
    splits = _splits_response(player, season, game_logs)
    trends = _trends_response(player, season, summary)
    benchmarks = _benchmarks_response(player, summary)
    summary_response = _summary_response(player, summary)
    return PlayerReportResponse(
        player=_player_list_item(player),
        season=season,
        summary=summary_response,
        trends=trends,
        splits=splits,
        benchmarks=benchmarks,
        sample_size_warnings=_json_list(summary.analytics_warnings),
        sections=_report_sections(
            player=player,
            summary=summary_response,
            splits=splits,
            trends=trends,
            benchmarks=benchmarks,
        ),
        meta=_api_meta(session, season),
    )


@router.get("/teams/{team_id}", response_model=TeamDetailResponse, summary="Get team by season")
async def team_detail(
    team_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> TeamDetailResponse:
    selected = _resolve_season_or_400(season)
    team = _get_team_or_404(session, team_id)
    _ensure_team_has_season(session, team, selected)
    summary = _get_team_summary(session, team.id, selected)
    return TeamDetailResponse(
        team=_team_response(team),
        summary=_team_summary_response(session, team, summary, selected) if summary else None,
        meta=_api_meta(session, selected),
    )


@router.get("/teams/{team_id}/roster", response_model=TeamRosterResponse, summary="Get team roster")
async def team_roster(
    team_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> TeamRosterResponse:
    selected = _resolve_season_or_400(season)
    team = _get_team_or_404(session, team_id)
    _ensure_team_has_season(session, team, selected)
    rows = session.execute(
        select(RosterMembership, Player)
        .join(Player, RosterMembership.player_id == Player.id)
        .where(RosterMembership.team_id == team.id, RosterMembership.season == selected)
        .order_by(RosterMembership.depth_order.nullslast(), Player.full_name)
    ).all()
    return TeamRosterResponse(
        team=_team_response(team),
        members=[
            RosterMemberResponse(
                player=_player_list_item_for_season(session, player, selected),
                jersey_number=membership.jersey_number,
                position=membership.position,
                roster_status=membership.roster_status,
                is_projected_starter=membership.is_projected_starter,
                depth_order=membership.depth_order,
            )
            for membership, player in rows
        ],
        meta=_api_meta(session, selected),
    )


@router.get(
    "/teams/{team_id}/summary",
    response_model=TeamSeasonSummaryApiResponse,
    summary="Get team season summary",
)
async def team_summary(
    team_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> TeamSeasonSummaryApiResponse:
    selected = _resolve_season_or_400(season)
    team = _get_team_or_404(session, team_id)
    summary = _get_team_summary(session, team.id, selected)
    if summary is None:
        _raise_entity_season_not_found("Team", team.name, selected)
    return _team_summary_response(session, team, summary, selected)


@router.get("/standings", response_model=StandingsResponse, summary="Get standings by season")
async def standings(
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> StandingsResponse:
    selected = _resolve_season_or_400(season)
    rows = session.execute(
        select(StandingsSnapshot, Team)
        .join(Team, StandingsSnapshot.team_id == Team.id)
        .where(StandingsSnapshot.season == selected)
        .order_by(StandingsSnapshot.conference, StandingsSnapshot.rank)
    ).all()
    return StandingsResponse(
        standings=[
            StandingRowResponse(
                team=_team_response(team),
                conference=row.conference,
                rank=row.rank,
                wins=row.wins,
                losses=row.losses,
                win_pct=float(row.win_pct),
                games_back=_float(row.games_back),
                conference_record=row.conference_record,
                division_record=row.division_record,
                home_record=row.home_record,
                away_record=row.away_record,
                last_10=row.last_10,
                streak=row.streak,
            )
            for row, team in rows
        ],
        meta=_api_meta(session, selected),
    )


@router.get("/players/{player_id}/summary", response_model=PlayerSeasonSummaryResponse)
async def player_summary_query(
    player_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> PlayerSeasonSummaryResponse:
    return await player_summary(player_id, _resolve_season_or_400(season), session)


@router.get("/players/{player_id}/games", response_model=PaginatedGameLogsResponse)
async def player_games_query(
    player_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedGameLogsResponse:
    return await player_games(
        player_id, _resolve_season_or_400(season), session, limit, offset, None, None, None, "asc"
    )


@router.get("/players/{player_id}/trends", response_model=TrendsResponse)
async def player_trends_query(
    player_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> TrendsResponse:
    return await player_trends(player_id, _resolve_season_or_400(season), session)


@router.get("/players/{player_id}/splits", response_model=PlayerSplitsResponse)
async def player_splits_query(
    player_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> PlayerSplitsResponse:
    return await player_splits(player_id, _resolve_season_or_400(season), session)


@router.get("/players/{player_id}/benchmarks", response_model=BenchmarksResponse)
async def player_benchmarks_query(
    player_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> BenchmarksResponse:
    return await player_benchmarks(player_id, _resolve_season_or_400(season), session)


@router.get("/similar-players", response_model=SimilarPlayersResponse)
async def similar_players_query(
    session: Annotated[Session, Depends(get_db_session)],
    player_id: Annotated[int, Query(gt=0)],
    season: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
    same_position_only: Annotated[bool, Query()] = False,
) -> SimilarPlayersResponse:
    return await similar_players(
        player_id,
        _resolve_season_or_400(season),
        session,
        limit,
        same_position_only=same_position_only,
    )


@router.get("/reports/player/{player_id}", response_model=PlayerReportResponse)
async def player_report_query(
    player_id: Annotated[int, Path(gt=0)],
    session: Annotated[Session, Depends(get_db_session)],
    season: Annotated[str | None, Query()] = None,
) -> PlayerReportResponse:
    return await player_report(player_id, _resolve_season_or_400(season), session)


def _compare_subject_response(
    session: Session,
    player: Player,
    season: str,
) -> ComparePlayerResponse:
    summary = _get_summary_or_404(session, player.id, season)
    game_logs = _game_logs_for_player(session, player.id, season)
    if not game_logs:
        _raise_not_found("season", season)
    return ComparePlayerResponse(
        player=_player_list_item(player),
        summary=_summary_response(player, summary),
        trends=_trends_response(player, season, summary),
        splits=_splits_response(player, season, game_logs),
        benchmarks=_benchmarks_response(player, summary),
        rest_splits=_rest_splits_response(game_logs),
        recent_5=_recent_window_response(game_logs, 5),
        recent_10=_recent_window_response(game_logs, 10),
        rolling_trend=_rolling_trend_response(player, game_logs),
    )


def _trends_response(
    player: Player,
    season: str,
    summary: PlayerSeasonSummary,
) -> TrendsResponse:
    return TrendsResponse(
        player_id=player.id,
        nba_player_id=player.nba_player_id,
        season=season,
        production_trend=summary.production_trend,
        production_trend_value=_float(summary.production_trend_value),
        efficiency_trend=summary.efficiency_trend,
        efficiency_trend_value=_float(summary.efficiency_trend_value),
        payload=_json_dict(summary.trend_payload),
    )


def _splits_response(
    player: Player,
    season: str,
    game_logs: list[GameLog],
) -> PlayerSplitsResponse:
    splits = calculate_home_away_splits(game_logs)
    return PlayerSplitsResponse(
        player_id=player.id,
        nba_player_id=player.nba_player_id,
        season=season,
        home=_split_response(splits.get("home")),
        away=_split_response(splits.get("away")),
    )


def _rest_splits_response(game_logs: list[GameLog]) -> RestSplitsResponse:
    grouped: dict[str, list[GameLog]] = {
        "first_game": [],
        "back_to_back": [],
        "one_day_rest": [],
        "two_or_more_days_rest": [],
    }
    for log in sorted(game_logs, key=lambda item: (item.game_date, item.game_id)):
        grouped[categorize_rest_days(log.days_since_previous_game)].append(log)
    return RestSplitsResponse(
        first_game=_split_response(_split_from_logs(grouped["first_game"])),
        back_to_back=_split_response(_split_from_logs(grouped["back_to_back"])),
        one_day_rest=_split_response(_split_from_logs(grouped["one_day_rest"])),
        two_or_more_days_rest=_split_response(_split_from_logs(grouped["two_or_more_days_rest"])),
    )


def _recent_window_response(game_logs: list[GameLog], window: int) -> RecentWindowResponse:
    recent_logs = sorted(game_logs, key=lambda log: (log.game_date, log.game_id))[-window:]
    split = _split_from_logs(recent_logs)
    plus_minus_values = [log.plus_minus for log in recent_logs if log.plus_minus is not None]
    return RecentWindowResponse(
        window=window,
        games=len(recent_logs),
        points=_per_game(split.points, split.games) if split is not None else None,
        rebounds=_per_game(split.rebounds, split.games) if split is not None else None,
        assists=_per_game(split.assists, split.games) if split is not None else None,
        minutes=_per_game(split.minutes, split.games) if split is not None else None,
        true_shooting_percentage=split.true_shooting_percentage if split is not None else None,
        turnovers=_per_game(sum(log.turnovers for log in recent_logs), len(recent_logs)),
        plus_minus=(sum(plus_minus_values) / len(plus_minus_values) if plus_minus_values else None),
    )


def _rolling_trend_response(
    player: Player,
    game_logs: list[GameLog],
) -> list[RollingTrendPointResponse]:
    rolling_rows = calculate_rolling_averages(game_logs)[-10:]
    return [
        RollingTrendPointResponse(
            player_id=player.id,
            nba_player_id=player.nba_player_id,
            game_id=row.game_log.game_id,
            game_date=row.game_log.game_date,
            points_rolling_5=row.values.get("points_rolling_5"),
            points_rolling_10=row.values.get("points_rolling_10"),
            assists_rolling_5=row.values.get("assists_rolling_5"),
            assists_rolling_10=row.values.get("assists_rolling_10"),
            true_shooting_percentage_rolling_5=row.values.get("true_shooting_percentage_rolling_5"),
            true_shooting_percentage_rolling_10=row.values.get(
                "true_shooting_percentage_rolling_10"
            ),
        )
        for row in rolling_rows
    ]


def _compare_metric_winners(
    first_summary: PlayerSeasonSummaryResponse,
    second_summary: PlayerSeasonSummaryResponse,
    first_benchmarks: BenchmarksResponse,
    second_benchmarks: BenchmarksResponse,
    first_recent_5: RecentWindowResponse,
    second_recent_5: RecentWindowResponse,
    first_recent_10: RecentWindowResponse,
    second_recent_10: RecentWindowResponse,
) -> list[CompareMetricResponse]:
    specs: list[tuple[str, str, str, bool, float | None, float | None]] = [
        (
            "points_per_game",
            "Points / Game",
            "season_averages",
            True,
            first_summary.points_per_game,
            second_summary.points_per_game,
        ),
        (
            "rebounds_per_game",
            "Rebounds / Game",
            "season_averages",
            True,
            first_summary.rebounds_per_game,
            second_summary.rebounds_per_game,
        ),
        (
            "assists_per_game",
            "Assists / Game",
            "season_averages",
            True,
            first_summary.assists_per_game,
            second_summary.assists_per_game,
        ),
        (
            "minutes_per_game",
            "Minutes / Game",
            "season_averages",
            True,
            first_summary.minutes_per_game,
            second_summary.minutes_per_game,
        ),
        (
            "true_shooting_percentage",
            "True Shooting",
            "efficiency",
            True,
            first_summary.true_shooting_percentage,
            second_summary.true_shooting_percentage,
        ),
        (
            "turnovers_per_game",
            "Turnovers / Game",
            "efficiency",
            False,
            first_summary.turnovers_per_game,
            second_summary.turnovers_per_game,
        ),
        (
            "recent_5_points",
            "Recent 5 PPG",
            "recent_form",
            True,
            first_recent_5.points,
            second_recent_5.points,
        ),
        (
            "recent_10_points",
            "Recent 10 PPG",
            "recent_form",
            True,
            first_recent_10.points,
            second_recent_10.points,
        ),
        (
            "position_points_percentile",
            "Position Points Percentile",
            "benchmarks",
            True,
            _numeric_json_value(first_benchmarks.position_percentiles, "points_per_game"),
            _numeric_json_value(second_benchmarks.position_percentiles, "points_per_game"),
        ),
        (
            "position_assists_percentile",
            "Position Assists Percentile",
            "benchmarks",
            True,
            _numeric_json_value(first_benchmarks.position_percentiles, "assists_per_game"),
            _numeric_json_value(second_benchmarks.position_percentiles, "assists_per_game"),
        ),
    ]
    return [
        CompareMetricResponse(
            key=key,
            label=label,
            category=category,
            higher_is_better=higher_is_better,
            player_a_value=player_a_value,
            player_b_value=player_b_value,
            winner=_metric_winner(player_a_value, player_b_value, higher_is_better),
        )
        for key, label, category, higher_is_better, player_a_value, player_b_value in specs
    ]


def _metric_winner(
    player_a_value: float | None,
    player_b_value: float | None,
    higher_is_better: bool,
) -> str | None:
    if player_a_value is None or player_b_value is None:
        return None
    if player_a_value == player_b_value:
        return "tie"
    if higher_is_better:
        return "player_a" if player_a_value > player_b_value else "player_b"
    return "player_a" if player_a_value < player_b_value else "player_b"


def _report_sections(
    *,
    player: Player,
    summary: PlayerSeasonSummaryResponse,
    splits: PlayerSplitsResponse,
    trends: TrendsResponse,
    benchmarks: BenchmarksResponse,
) -> list[ReportSectionResponse]:
    league_points_percentile = _format_number(
        _numeric_json_value(benchmarks.league_percentiles, "points_per_game")
    )
    position_assists_percentile = _format_number(
        _numeric_json_value(benchmarks.position_percentiles, "assists_per_game")
    )
    minutes_tier_ts_percentile = _format_number(
        _numeric_json_value(
            benchmarks.minutes_tier_percentiles,
            "true_shooting_percentage",
        )
    )

    return [
        ReportSectionResponse(
            key="season_overview",
            title="Season Overview",
            sentences=[
                _sentence(
                    (
                        f"{player.full_name} has played {summary.games_played} games in "
                        f"{summary.season}, averaging {_format_number(summary.points_per_game)} "
                        f"points, {_format_number(summary.rebounds_per_game)} rebounds, "
                        f"{_format_number(summary.assists_per_game)} assists, and "
                        f"{_format_number(summary.minutes_per_game)} minutes per game."
                    ),
                    [
                        "summary.games_played",
                        "summary.points_per_game",
                        "summary.rebounds_per_game",
                        "summary.assists_per_game",
                        "summary.minutes_per_game",
                    ],
                )
            ],
        ),
        ReportSectionResponse(
            key="recent_form",
            title="Recent Form",
            sentences=[
                _sentence(
                    (
                        f"The production trend is {trends.production_trend or 'unavailable'} "
                        f"with a composite value of "
                        f"{_format_number(trends.production_trend_value, 3)}."
                    ),
                    ["trends.production_trend", "trends.production_trend_value"],
                )
            ],
        ),
        ReportSectionResponse(
            key="efficiency",
            title="Efficiency",
            sentences=[
                _sentence(
                    (
                        f"True shooting is {_format_percent(summary.true_shooting_percentage)} "
                        f"and is labeled as {summary.true_shooting_source or 'unavailable'}."
                    ),
                    ["summary.true_shooting_percentage", "summary.true_shooting_source"],
                )
            ],
        ),
        ReportSectionResponse(
            key="splits",
            title="Splits",
            sentences=[_split_sentence(splits)],
        ),
        ReportSectionResponse(
            key="benchmarks",
            title="League And Position Benchmarks",
            sentences=[
                _sentence(
                    (
                        "Stored benchmark percentiles are "
                        f"{league_points_percentile} for league points per game, "
                        f"{position_assists_percentile} for position assists per "
                        "game, and "
                        f"{minutes_tier_ts_percentile} for similar-minutes true "
                        "shooting."
                    ),
                    [
                        "benchmarks.league_percentiles.points_per_game",
                        "benchmarks.position_percentiles.assists_per_game",
                        "benchmarks.minutes_tier_percentiles.true_shooting_percentage",
                    ],
                )
            ],
        ),
        ReportSectionResponse(
            key="trends",
            title="Production And Efficiency Trends",
            sentences=[
                _sentence(
                    (
                        f"Efficiency trend is {trends.efficiency_trend or 'unavailable'} "
                        f"with a composite value of "
                        f"{_format_number(trends.efficiency_trend_value, 3)}."
                    ),
                    ["trends.efficiency_trend", "trends.efficiency_trend_value"],
                )
            ],
        ),
        ReportSectionResponse(
            key="sample_size_warnings",
            title="Sample-Size Warnings",
            sentences=[
                _sentence(
                    (
                        f"{len(summary.analytics_warnings)} analytics warning"
                        f"{'' if len(summary.analytics_warnings) == 1 else 's'} "
                        "are attached to this player-season."
                    ),
                    ["summary.analytics_warnings"],
                )
            ],
        ),
    ]


def _sentence(text: str, fields: list[str]) -> ReportSentenceResponse:
    return ReportSentenceResponse(text=text, fields=fields)


def _split_sentence(splits: PlayerSplitsResponse) -> ReportSentenceResponse:
    if splits.home is None or splits.away is None:
        return _sentence(
            "Home and away split data is incomplete for this player-season.",
            ["splits.home", "splits.away"],
        )
    return _sentence(
        (
            f"Home split includes {splits.home.games} games at "
            f"{_format_number(_per_game(splits.home.points, splits.home.games))} points per game, "
            f"while away split includes {splits.away.games} games at "
            f"{_format_number(_per_game(splits.away.points, splits.away.games))} points per game."
        ),
        ["splits.home.games", "splits.home.points", "splits.away.games", "splits.away.points"],
    )


def _game_log_filter_conditions(
    *,
    home_team: Any,
    away_team: Any,
    location: str | None,
    opponent: str | None,
    result: str | None,
) -> list[Any]:
    conditions: list[Any] = []
    if location == "home":
        conditions.append(PlayerGameStat.is_home.is_(True))
    elif location == "away":
        conditions.append(PlayerGameStat.is_home.is_(False))
    if result is not None:
        conditions.append(PlayerGameStat.result == result)
    if opponent:
        opponent_value = opponent.strip()
        if opponent_value.isdigit():
            opponent_team_id = int(opponent_value)
            conditions.append(
                or_(
                    and_(
                        PlayerGameStat.is_home.is_(True),
                        away_team.nba_team_id == opponent_team_id,
                    ),
                    and_(
                        PlayerGameStat.is_home.is_(False),
                        home_team.nba_team_id == opponent_team_id,
                    ),
                )
            )
        else:
            conditions.append(
                or_(
                    and_(
                        PlayerGameStat.is_home.is_(True),
                        away_team.abbreviation.ilike(opponent_value),
                    ),
                    and_(
                        PlayerGameStat.is_home.is_(False),
                        home_team.abbreviation.ilike(opponent_value),
                    ),
                )
            )
    return conditions


def _get_player_or_404(session: Session, player_identifier: int) -> Player:
    player = session.scalar(
        select(Player)
        .options(joinedload(Player.team))
        .where(or_(Player.id == player_identifier, Player.nba_player_id == player_identifier))
        .order_by(Player.id)
        .limit(1)
    )
    if player is None:
        _raise_not_found("player", str(player_identifier))
    return player


def _get_summary_or_404(session: Session, player_id: int, season: str) -> PlayerSeasonSummary:
    season = _resolve_season_or_400(season)
    summary = _get_summary(session, player_id, season)
    if summary is None:
        _raise_not_found("season_summary", f"player={player_id}, season={season}")
    return summary


def _get_summary(
    session: Session,
    player_id: int,
    season: str,
) -> PlayerSeasonSummary | None:
    return session.scalar(
        select(PlayerSeasonSummary).where(
            PlayerSeasonSummary.player_id == player_id,
            PlayerSeasonSummary.season == season,
        )
    )


def _ensure_season_exists_for_player(session: Session, player_id: int, season: str) -> None:
    season = _resolve_season_or_400(season)
    exists = session.scalar(
        select(PlayerGameStat.id)
        .where(PlayerGameStat.player_id == player_id, PlayerGameStat.season == season)
        .limit(1)
    )
    if exists is None:
        _raise_not_found("season", season)


def _game_logs_for_player(session: Session, player_id: int, season: str) -> list[GameLog]:
    season = _resolve_season_or_400(season)
    rows = session.execute(
        select(PlayerGameStat, Game, Player)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .join(Player, PlayerGameStat.player_id == Player.id)
        .where(PlayerGameStat.player_id == player_id, PlayerGameStat.season == season)
        .order_by(Game.game_date, Game.nba_game_id)
    ).all()
    return [
        GameLog(
            player_id=player.id,
            game_id=game.id,
            game_date=game.game_date,
            position=player.position,
            team_id=stat.team_id,
            matchup=stat.matchup,
            is_home=stat.is_home,
            days_since_previous_game=stat.days_since_previous_game,
            minutes=_float(stat.minutes),
            points=stat.points,
            rebounds=stat.rebounds,
            assists=stat.assists,
            steals=stat.steals,
            blocks=stat.blocks,
            turnovers=stat.turnovers,
            personal_fouls=stat.personal_fouls,
            field_goals_made=stat.field_goals_made,
            field_goal_attempts=stat.field_goals_attempted,
            three_pointers_made=stat.three_pointers_made,
            three_point_attempts=stat.three_pointers_attempted,
            free_throws_made=stat.free_throws_made,
            free_throw_attempts=stat.free_throws_attempted,
            plus_minus=_float(stat.plus_minus),
        )
        for stat, game, player in rows
    ]


def _count(session: Session, model: type[Any], conditions: list[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


def _page_meta(limit: int, offset: int, total: int) -> PageMeta:
    next_offset = offset + limit if offset + limit < total else None
    previous_offset = max(offset - limit, 0) if offset > 0 else None
    return PageMeta(
        limit=limit,
        offset=offset,
        total=total,
        next_offset=next_offset,
        previous_offset=previous_offset,
    )


def _player_list_item(player: Player) -> PlayerListItem:
    return PlayerListItem(
        id=player.id,
        nba_player_id=player.nba_player_id,
        slug=player.slug,
        full_name=player.full_name,
        first_name=player.first_name,
        last_name=player.last_name,
        position=player.position,
        jersey_number=player.jersey_number,
        active=player.active,
        team=_team_response(player.team) if player.team is not None else None,
    )


def _player_detail(player: Player) -> PlayerDetail:
    item = _player_list_item(player)
    return PlayerDetail(
        **item.model_dump(),
        height=player.height,
        weight_pounds=player.weight_pounds,
        birthdate=player.birthdate,
    )


def _team_response(team: Team) -> TeamResponse:
    return TeamResponse.model_validate(team, from_attributes=True)


def _summary_response(player: Player, summary: PlayerSeasonSummary) -> PlayerSeasonSummaryResponse:
    return PlayerSeasonSummaryResponse(
        player_id=player.id,
        nba_player_id=player.nba_player_id,
        season=summary.season,
        games_played=summary.games_played,
        minutes_per_game=_float(summary.minutes_per_game),
        points_per_game=_float(summary.points_per_game),
        rebounds_per_game=_float(summary.rebounds_per_game),
        assists_per_game=_float(summary.assists_per_game),
        turnovers_per_game=_float(summary.turnovers_per_game),
        plus_minus_per_game=_float(summary.plus_minus_per_game),
        true_shooting_percentage=_float(summary.true_shooting_percentage),
        true_shooting_source=summary.true_shooting_source,
        usage_rate=_float(summary.usage_rate),
        points_per_36=_float(summary.points_per_36),
        rebounds_per_36=_float(summary.rebounds_per_36),
        assists_per_36=_float(summary.assists_per_36),
        turnovers_per_36=_float(summary.turnovers_per_36),
        analytics_rebuilt_at=summary.analytics_rebuilt_at,
        analytics_warnings=_json_list(summary.analytics_warnings),
    )


def _game_log_item(
    *,
    stat: PlayerGameStat,
    game: Game,
    home_team: Team,
    away_team: Team,
) -> GameLogItem:
    opponent = _opponent_team(stat, home_team, away_team)
    location = None if stat.is_home is None else ("home" if stat.is_home else "away")
    return GameLogItem(
        id=stat.id,
        game_id=game.id,
        nba_game_id=game.nba_game_id,
        game_date=game.game_date,
        season=stat.season,
        matchup=stat.matchup,
        location=location,
        opponent=_team_response(opponent) if opponent is not None else None,
        result=stat.result,
        days_since_previous_game=stat.days_since_previous_game,
        minutes=_float(stat.minutes),
        points=stat.points,
        rebounds=stat.rebounds,
        assists=stat.assists,
        steals=stat.steals,
        blocks=stat.blocks,
        turnovers=stat.turnovers,
        personal_fouls=stat.personal_fouls,
        field_goals_made=stat.field_goals_made,
        field_goals_attempted=stat.field_goals_attempted,
        three_pointers_made=stat.three_pointers_made,
        three_pointers_attempted=stat.three_pointers_attempted,
        free_throws_made=stat.free_throws_made,
        free_throws_attempted=stat.free_throws_attempted,
        plus_minus=_float(stat.plus_minus),
        calculated_true_shooting_percentage=calculate_true_shooting(
            stat.points,
            stat.field_goals_attempted,
            stat.free_throws_attempted,
        ),
    )


def _opponent_team(stat: PlayerGameStat, home_team: Team, away_team: Team) -> Team | None:
    if stat.is_home is True:
        return away_team
    if stat.is_home is False:
        return home_team
    return None


def _split_from_logs(game_logs: list[GameLog]) -> SplitSummary | None:
    if not game_logs:
        return None
    points = sum(log.points for log in game_logs)
    field_goal_attempts = sum(log.field_goal_attempts for log in game_logs)
    free_throw_attempts = sum(log.free_throw_attempts for log in game_logs)
    return SplitSummary(
        games=len(game_logs),
        minutes=sum(log.minutes or 0 for log in game_logs),
        points=points,
        rebounds=sum(log.rebounds for log in game_logs),
        assists=sum(log.assists for log in game_logs),
        true_shooting_percentage=calculate_true_shooting(
            points,
            field_goal_attempts,
            free_throw_attempts,
        ),
    )


def _split_response(split: SplitSummary | None) -> SplitResponse | None:
    if split is None:
        return None
    return SplitResponse(
        games=split.games,
        minutes=split.minutes,
        points=split.points,
        rebounds=split.rebounds,
        assists=split.assists,
        true_shooting_percentage=split.true_shooting_percentage,
    )


def _benchmarks_response(player: Player, summary: PlayerSeasonSummary) -> BenchmarksResponse:
    return BenchmarksResponse(
        player_id=player.id,
        nba_player_id=player.nba_player_id,
        season=summary.season,
        league_percentiles=_json_dict(summary.league_percentiles),
        position_percentiles=_json_dict(summary.position_percentiles),
        minutes_tier_percentiles=_json_dict(summary.minutes_tier_percentiles),
        analytics_warnings=_json_list(summary.analytics_warnings),
    )


def _absolute_difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(abs(left - right), 1)


def _per_game(total: float | int | None, games: int) -> float | None:
    if total is None or games <= 0:
        return None
    return float(total) / games


def _numeric_json_value(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _format_number(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "unavailable"
    return f"{float(value):.{digits}f}"


def _format_percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "unavailable"
    return f"{value * 100:.{digits}f}%"


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _resolve_season_or_400(season: str | None) -> str:
    try:
        return validate_season(season)
    except ValueError as exc:
        available = ", ".join(get_available_seasons())
        requested = season or get_default_season()
        raise HTTPException(
            status_code=400,
            detail=f"Season {requested} is not available. Available seasons: {available}.",
        ) from exc


def _player_season_exists(season: str) -> Any:
    return or_(
        exists().where(
            PlayerSeasonSummary.player_id == Player.id,
            PlayerSeasonSummary.season == season,
        ),
        exists().where(
            PlayerGameStat.player_id == Player.id,
            PlayerGameStat.season == season,
        ),
        exists().where(
            RosterMembership.player_id == Player.id,
            RosterMembership.season == season,
        ),
    )


def _teams_for_season(session: Session, season: str) -> list[Team]:
    condition = or_(
        exists().where(TeamSeasonSummary.team_id == Team.id, TeamSeasonSummary.season == season),
        exists().where(StandingsSnapshot.team_id == Team.id, StandingsSnapshot.season == season),
        exists().where(RosterMembership.team_id == Team.id, RosterMembership.season == season),
        exists().where(Game.home_team_id == Team.id, Game.season == season),
        exists().where(Game.away_team_id == Team.id, Game.season == season),
    )
    return list(session.scalars(select(Team).where(condition).order_by(Team.abbreviation)))


def _player_list_item_for_season(session: Session, player: Player, season: str) -> PlayerListItem:
    membership = _season_membership(session, player.id, season)
    return _player_list_item(player).model_copy(
        update={
            "team": _season_team_response(session, player.id, season),
            "position": membership.position
            if membership and membership.position
            else player.position,
            "jersey_number": (
                membership.jersey_number
                if membership and membership.jersey_number
                else player.jersey_number
            ),
        }
    )


def _season_membership(session: Session, player_id: int, season: str) -> RosterMembership | None:
    return session.scalar(
        select(RosterMembership)
        .where(
            RosterMembership.player_id == player_id,
            RosterMembership.season == season,
        )
        .order_by(RosterMembership.start_date.desc().nullslast(), RosterMembership.id.desc())
        .limit(1)
    )


def _season_team_response(session: Session, player_id: int, season: str) -> TeamResponse | None:
    team = session.scalar(
        select(Team)
        .join(RosterMembership, RosterMembership.team_id == Team.id)
        .where(
            RosterMembership.player_id == player_id,
            RosterMembership.season == season,
        )
        .order_by(RosterMembership.start_date.desc().nullslast(), RosterMembership.id.desc())
        .limit(1)
    )
    if team is None:
        team = session.scalar(
            select(Team)
            .join(PlayerSeasonSummary, PlayerSeasonSummary.team_id == Team.id)
            .where(
                PlayerSeasonSummary.player_id == player_id,
                PlayerSeasonSummary.season == season,
            )
            .limit(1)
        )
    return _team_response(team) if team else None


def _get_team_or_404(session: Session, identifier: int) -> Team:
    team = session.scalar(
        select(Team).where(or_(Team.id == identifier, Team.nba_team_id == identifier))
    )
    if team is None:
        _raise_not_found("team", str(identifier))
    return team


def _ensure_player_has_season(session: Session, player: Player, season: str) -> None:
    if not player_has_season(session, player.id, season):
        _raise_entity_season_not_found("Player", player.full_name, season)


def _ensure_team_has_season(session: Session, team: Team, season: str) -> None:
    if not team_has_season(session, team.id, season):
        _raise_entity_season_not_found("Team", team.name, season)


def _raise_entity_season_not_found(entity: str, name: str, season: str) -> NoReturn:
    raise HTTPException(
        status_code=404,
        detail=f"{entity} {name} exists, but has no stored data for season {season}.",
    )


def _get_team_summary(session: Session, team_id: int, season: str) -> TeamSeasonSummary | None:
    return session.scalar(
        select(TeamSeasonSummary).where(
            TeamSeasonSummary.team_id == team_id, TeamSeasonSummary.season == season
        )
    )


def _team_summary_response(
    session: Session,
    team: Team,
    summary: TeamSeasonSummary,
    season: str,
) -> TeamSeasonSummaryApiResponse:
    return TeamSeasonSummaryApiResponse(
        team=_team_response(team),
        season=season,
        conference=summary.conference,
        division=summary.division,
        wins=summary.wins,
        losses=summary.losses,
        win_pct=_float(summary.win_pct),
        conference_rank=summary.conference_rank,
        division_rank=summary.division_rank,
        points_per_game=_float(summary.points_per_game),
        points_allowed_per_game=_float(summary.points_allowed_per_game),
        net_rating=_float(summary.net_rating),
        offensive_rating=_float(summary.offensive_rating),
        defensive_rating=_float(summary.defensive_rating),
        pace=_float(summary.pace),
        playoff_result=summary.playoff_result,
        meta=_api_meta(session, season),
    )


def _api_meta(session: Session, season: str) -> ApiMetadata:
    freshness = session.scalar(
        select(SyncRun.finished_at)
        .where(
            SyncRun.season == season,
            SyncRun.status.in_(("completed", "completed_with_rejections")),
        )
        .order_by(SyncRun.finished_at.desc().nullslast(), SyncRun.id.desc())
        .limit(1)
    )
    return ApiMetadata(season=season, dataFreshness=freshness, source="database")


def _json_dict(value: dict[str, object] | None) -> dict[str, Any]:
    return dict(value or {})


def _json_list(value: list[dict[str, object]] | None) -> list[dict[str, Any]]:
    return [dict(item) for item in value or []]


def _raise_not_found(resource: str, identifier: str) -> NoReturn:
    raise HTTPException(
        status_code=404,
        detail={
            "error": {
                "code": "not_found",
                "message": f"{resource} not found: {identifier}",
            }
        },
    )
