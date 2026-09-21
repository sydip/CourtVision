from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.session import create_session_factory, session_scope
from app.predictions.datasets import assert_no_future_leakage, build_dataset
from app.predictions.guardrails import TARGETS, require_target

ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "model_artifacts"


def run(target: str) -> dict[str, object]:
    require_target(target)
    with session_scope(create_session_factory()) as session:
        dataset = build_dataset(session, target)
        assert_no_future_leakage(dataset)
    destination = ARTIFACT_ROOT / target / "dataset.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(dataset.as_dict(), indent=2), encoding="utf-8")
    return {
        "target": target,
        "rows": len(dataset.rows),
        "path": str(destination),
        "training_seasons": list(dataset.training_seasons),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=TARGETS, required=True)
    print(json.dumps(run(parser.parse_args().target), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
