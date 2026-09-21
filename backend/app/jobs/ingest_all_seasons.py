from __future__ import annotations

import argparse
import json

from app.jobs.ingest_season import run as ingest_season
from app.services.seasons import season_range


def run(from_season: str, to_season: str) -> list[dict[str, object]]:
    return [ingest_season(season) for season in season_range(from_season, to_season)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-season", default="2021-22")
    parser.add_argument("--to-season", default="2025-26")
    args = parser.parse_args()
    results = run(args.from_season, args.to_season)
    print(json.dumps(results, indent=2))
    return 1 if any(result["status"] == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
