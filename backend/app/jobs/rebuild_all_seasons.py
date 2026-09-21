from __future__ import annotations

import json

from app.jobs.rebuild_analytics import run as rebuild_season
from app.services.seasons import HISTORICAL_SEASONS


def run() -> list[dict[str, object]]:
    return [rebuild_season(season) for season in HISTORICAL_SEASONS]


def main() -> int:
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
