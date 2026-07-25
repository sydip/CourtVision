from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from app.analytics.rebuild import rebuild_season_analytics
from app.analytics.types import BenchmarkConfig
from app.core.config import Settings, get_settings
from app.data.providers import FixtureProvider, NbaApiProvider
from app.db.base import Base
from app.db.session import create_database_engine, create_session_factory, session_scope
from app.ingestion.pipeline import (
    ALL_INGESTION_STEPS,
    IngestionStep,
    run_fixture_ingestion,
    run_provider_ingestion,
    stderr_progress,
)
from app.models import schema as _schema  # noqa: F401


def main(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="HoopsIQ ingestion commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fixtures_parser = subparsers.add_parser("fixtures", help="Ingest offline fixture data.")
    fixtures_parser.add_argument("--season", default=settings.nba_season)
    fixtures_parser.add_argument("--fixture-dir", type=Path, default=None)
    _add_database_args(fixtures_parser)

    analytics_parser = subparsers.add_parser(
        "rebuild-analytics",
        help="Rebuild season analytics from stored game logs without downloading data.",
    )
    analytics_parser.add_argument("--season", default=settings.nba_season)
    analytics_parser.add_argument(
        "--minimum-games",
        type=int,
        default=settings.benchmark_minimum_games,
    )
    analytics_parser.add_argument(
        "--minimum-minutes-per-game",
        type=float,
        default=settings.benchmark_minimum_minutes_per_game,
    )
    analytics_parser.add_argument(
        "--similar-minutes-tolerance",
        type=float,
        default=settings.benchmark_similar_minutes_tolerance,
    )
    _add_database_args(analytics_parser)

    live_commands: dict[str, tuple[str, tuple[IngestionStep, ...]]] = {
        "sync-players": ("Sync static NBA players and teams.", ("teams", "players")),
        "sync-profiles": (
            "Sync common player information for a sample of players.",
            ("teams", "players", "profiles"),
        ),
        "sync-game-logs": (
            "Sync game logs and derived games for a sample of players.",
            ("teams", "players", "games", "game_logs"),
        ),
        "sync-league-statistics": (
            "Sync league-wide player statistics for a sample of players.",
            ("teams", "players", "league_statistics"),
        ),
        "sync-sample-player": (
            "Sync one small sample end to end before a full-season run.",
            ("teams", "players", "profiles", "games", "game_logs", "league_statistics"),
        ),
        "sync-season": (
            "Sync the configured season for all active players.",
            ALL_INGESTION_STEPS,
        ),
    }
    for command_name, (help_text, _) in live_commands.items():
        live_parser = subparsers.add_parser(command_name, help=help_text)
        _add_live_args(live_parser, settings)

    args = parser.parse_args(argv)
    if args.init_schema:
        _init_schema(args.database_url)

    if args.command == "fixtures":
        fixture_provider = FixtureProvider(fixture_root=args.fixture_dir, season=args.season)
        session_factory = create_session_factory(args.database_url)
        with session_scope(session_factory) as session:
            summary = run_fixture_ingestion(session, fixture_provider, args.season)
            print(json.dumps(summary.as_dict(), indent=2))
        return 0

    if args.command == "rebuild-analytics":
        config = BenchmarkConfig(
            minimum_games=args.minimum_games,
            minimum_minutes_per_game=args.minimum_minutes_per_game,
            similar_minutes_tolerance=args.similar_minutes_tolerance,
        )
        session_factory = create_session_factory(args.database_url)
        with session_scope(session_factory) as session:
            analytics_summary = rebuild_season_analytics(session, args.season, config)
            print(json.dumps(analytics_summary.as_dict(), indent=2))
        return 0

    if args.command not in live_commands:
        parser.error(f"Unsupported command: {args.command}")

    nba_provider = _build_nba_provider(args)
    _, steps = live_commands[args.command]
    session_factory = create_session_factory(args.database_url)
    with session_scope(session_factory) as session:
        summary = run_provider_ingestion(
            session,
            nba_provider,
            args.season,
            source=f"nba_api:{args.command}",
            steps=steps,
            progress=None if args.quiet else stderr_progress,
            raise_on_failure=False,
        )
        print(json.dumps(summary.as_dict(), indent=2))
    return 1 if summary.status == "failed" else 0


def _add_database_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--database-url", default=None)
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Create tables before ingestion; intended for disposable fixture checks.",
    )


def _add_live_args(parser: argparse.ArgumentParser, settings: Settings) -> None:
    parser.add_argument("--season", default=settings.nba_season)
    parser.add_argument("--raw-data-dir", default=settings.raw_data_dir)
    parser.add_argument(
        "--player-id",
        type=int,
        action="append",
        default=[],
        help="NBA player ID to sync. Repeat for multiple sample players.",
    )
    parser.add_argument(
        "--player-limit",
        type=int,
        default=1,
        help="Sample size when --player-id is not supplied. Defaults to 1.",
    )
    parser.add_argument(
        "--all-players",
        action="store_true",
        help="Disable the sample limit and run the selected command for all returned players.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress command-line progress reporting.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=settings.api_request_timeout_seconds,
    )
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--request-delay-seconds", type=float, default=0.6)
    _add_database_args(parser)


def _build_nba_provider(args: argparse.Namespace) -> NbaApiProvider:
    player_limit = None if args.all_players or args.command == "sync-season" else args.player_limit
    return NbaApiProvider(
        season=args.season,
        raw_data_dir=args.raw_data_dir,
        timeout_seconds=args.timeout_seconds,
        player_ids=args.player_id,
        player_limit=player_limit,
        max_retries=args.max_retries,
        backoff_seconds=args.backoff_seconds,
        request_delay_seconds=args.request_delay_seconds,
    )


def _init_schema(database_url: str | None) -> None:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
