from __future__ import annotations

import argparse
import json
from typing import cast

from app.data.providers.base import BasketballDataProvider
from app.db.session import create_session_factory, session_scope
from app.ingestion.pipeline import ALL_INGESTION_STEPS, run_provider_ingestion, stderr_progress
from app.jobs.common import build_provider
from app.services.seasons import validate_season_slug


def run(season: str) -> dict[str, object]:
    validate_season_slug(season)
    factory = create_session_factory()
    with session_scope(factory) as session:
        summary = run_provider_ingestion(
            session,
            cast(BasketballDataProvider, build_provider(season)),
            season,
            source="nba_api:historical-season",
            steps=ALL_INGESTION_STEPS,
            progress=stderr_progress,
            raise_on_failure=False,
        )
        return summary.as_dict()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True)
    args = parser.parse_args()
    result = run(args.season)
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
