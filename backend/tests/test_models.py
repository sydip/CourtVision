from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Game,
    PerformanceReport,
    Player,
    PlayerGameStat,
    PlayerSeasonSummary,
    SyncRun,
    Team,
)
from app.repositories import PlayerGameStatRepository, PlayerRepository


def make_team(nba_team_id: int = 1610612744, abbreviation: str = "GSW") -> Team:
    return Team(
        nba_team_id=nba_team_id,
        abbreviation=abbreviation,
        city="San Francisco",
        name="Warriors",
        conference="West",
        division="Pacific",
    )


def make_player(team: Team, nba_player_id: int = 201939, slug: str = "stephen-curry") -> Player:
    return Player(
        nba_player_id=nba_player_id,
        slug=slug,
        full_name="Stephen Curry",
        first_name="Stephen",
        last_name="Curry",
        team=team,
        position="PG",
        height="6-2",
        weight_pounds=185,
        birthdate=date(1988, 3, 14),
    )


def make_game(home_team: Team, away_team: Team, nba_game_id: str = "0022400001") -> Game:
    return Game(
        nba_game_id=nba_game_id,
        season="2025-26",
        game_date=date(2025, 5, 8),
        home_team=home_team,
        away_team=away_team,
        home_score=121,
        away_score=118,
    )


def commit_and_expect_integrity_error(session: Session, model: object) -> None:
    session.add(model)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_model_creation_relationships_and_repositories(db_session: Session) -> None:
    warriors = make_team()
    wolves = make_team(1610612750, "MIN")
    player = make_player(warriors)
    game = make_game(warriors, wolves)
    stat = PlayerGameStat(
        player=player,
        game=game,
        team=warriors,
        season="2025-26",
        minutes=Decimal("33.50"),
        points=31,
        rebounds=4,
        assists=7,
        field_goals_made=11,
        field_goals_attempted=21,
    )
    summary = PlayerSeasonSummary(
        player=player,
        team=warriors,
        season="2025-26",
        games_played=72,
        points_per_game=Decimal("24.80"),
        assists_per_game=Decimal("6.10"),
        true_shooting_percentage=Decimal("63.400"),
    )
    sync_run = SyncRun(source="mock", season="2025-26", status="success", rows_processed=1)
    report = PerformanceReport(
        player=player,
        season="2025-26",
        report_type="player_overview",
        report_key="player-overview:201939:2025-26",
        content="Deterministic mock report.",
        payload={"points_per_game": 24.8},
    )

    db_session.add_all([warriors, wolves, player, game, stat, summary, sync_run, report])
    db_session.commit()

    player_repository = PlayerRepository(db_session)
    stat_repository = PlayerGameStatRepository(db_session)

    found_player = player_repository.get_by_slug("stephen-curry")
    assert found_player is player
    assert found_player.team is warriors
    assert found_player.game_stats[0].game is game
    assert found_player.season_summaries[0].season == "2025-26"
    assert found_player.performance_reports[0].report_key == "player-overview:201939:2025-26"
    assert stat_repository.get_for_player_game(player.id, game.id) is stat
    assert stat_repository.list_for_player_season(player.id, "2025-26") == [stat]


def test_unique_natural_keys_are_rejected(db_session: Session) -> None:
    warriors = make_team()
    wolves = make_team(1610612750, "MIN")
    player = make_player(warriors)
    game = make_game(warriors, wolves)
    db_session.add_all([warriors, wolves, player, game])
    db_session.commit()

    commit_and_expect_integrity_error(db_session, make_team())
    commit_and_expect_integrity_error(db_session, make_player(warriors, 201940, "stephen-curry"))
    commit_and_expect_integrity_error(db_session, make_player(warriors, 201939, "wardell-curry"))
    commit_and_expect_integrity_error(db_session, make_game(warriors, wolves))


def test_duplicate_player_game_stat_is_rejected(db_session: Session) -> None:
    warriors = make_team()
    wolves = make_team(1610612750, "MIN")
    player = make_player(warriors)
    game = make_game(warriors, wolves)
    db_session.add_all([warriors, wolves, player, game])
    db_session.commit()

    first_stat = PlayerGameStat(
        player=player, game=game, team=warriors, season="2025-26", points=31
    )
    db_session.add(first_stat)
    db_session.commit()

    duplicate_stat = PlayerGameStat(
        player_id=player.id,
        game_id=game.id,
        team_id=warriors.id,
        season="2025-26",
        points=22,
    )
    commit_and_expect_integrity_error(db_session, duplicate_stat)


def test_player_season_summary_lookup_is_unique(db_session: Session) -> None:
    warriors = make_team()
    player = make_player(warriors)
    db_session.add_all([warriors, player])
    db_session.commit()

    db_session.add(
        PlayerSeasonSummary(player=player, team=warriors, season="2025-26", games_played=72)
    )
    db_session.commit()

    duplicate_summary = PlayerSeasonSummary(
        player_id=player.id,
        team_id=warriors.id,
        season="2025-26",
        games_played=73,
    )
    commit_and_expect_integrity_error(db_session, duplicate_summary)
