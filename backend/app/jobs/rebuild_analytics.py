from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from app.analytics.rebuild import rebuild_season_analytics
from app.analytics.types import BenchmarkConfig
from app.core.config import get_settings
from app.db.session import create_session_factory, session_scope
from app.models import SyncRun
from app.services.seasons import HISTORICAL_SEASONS, validate_season_slug


def run(season: str) -> dict[str, object]:
    validate_season_slug(season)
    settings = get_settings()
    config = BenchmarkConfig(
        minimum_games=settings.benchmark_minimum_games,
        minimum_minutes_per_game=settings.benchmark_minimum_minutes_per_game,
        similar_minutes_tolerance=settings.benchmark_similar_minutes_tolerance,
    )
    with session_scope(create_session_factory()) as session:
        sync_run = SyncRun(source="analytics_rebuild", season=season, status="running")
        session.add(sync_run)
        session.flush()
        try:
            result = rebuild_season_analytics(session, season, config)
        except Exception as exc:
            sync_run.status = "failed"
            sync_run.finished_at = datetime.now(UTC)
            sync_run.failed_count = 1
            sync_run.error_message = str(exc)
            raise
        sync_run.status = "completed"
        sync_run.finished_at = datetime.now(UTC)
        sync_run.rows_processed = result.players_processed
        sync_run.inserted_count = result.summaries_created
        sync_run.updated_count = result.summaries_updated
        sync_run.rejected_count = len(result.warnings)
        return result.as_dict()


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--season")
    group.add_argument("--all-seasons", action="store_true")
    args = parser.parse_args()
    seasons = HISTORICAL_SEASONS if args.all_seasons else (args.season,)
    print(json.dumps([run(season) for season in seasons], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
