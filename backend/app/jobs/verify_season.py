from __future__ import annotations

import argparse
import json

from app.db.session import create_session_factory, session_scope
from app.services.ingestion_verification import verify_season


def run(season: str) -> dict[str, object]:
    with session_scope(create_session_factory()) as session:
        return verify_season(session, season).as_dict()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True)
    args = parser.parse_args()
    result = run(args.season)
    print(json.dumps(result, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
