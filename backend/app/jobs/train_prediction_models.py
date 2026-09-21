from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from app.db.session import create_session_factory, session_scope
from app.jobs.build_prediction_dataset import ARTIFACT_ROOT
from app.models import PredictionRun
from app.predictions.datasets import build_dataset
from app.predictions.guardrails import PREDICTION_SEASON, TARGETS, require_target
from app.predictions.models import save_bundle
from app.predictions.training import train_model


def run(target: str) -> dict[str, object]:
    require_target(target)
    with session_scope(create_session_factory()) as session:
        dataset = build_dataset(session, target)
        tracking = PredictionRun(
            season=PREDICTION_SEASON,
            prediction_type=target,
            model_name="logistic_regression",
            model_version="logistic-v1",
            training_seasons=list(dataset.training_seasons),
            feature_set_version="features-v1",
            status="running",
            started_at=datetime.now(UTC),
        )
        session.add(tracking)
        try:
            bundle = train_model(dataset)
            destination = ARTIFACT_ROOT / target / "model.joblib"
            save_bundle(bundle, destination)
            metadata = {
                "target": target,
                "model_version": bundle.model_version,
                "feature_names": list(bundle.feature_names),
                "training_seasons": list(bundle.training_seasons),
                "experimental": True,
                "prediction_season": PREDICTION_SEASON,
                "rows": len(dataset.rows),
            }
            (destination.parent / "metadata.json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )
            tracking.status = "completed"
            tracking.completed_at = datetime.now(UTC)
            return {**metadata, "path": str(destination)}
        except Exception as exc:
            tracking.status = "failed"
            tracking.completed_at = datetime.now(UTC)
            tracking.error_message = str(exc)
            raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=TARGETS, required=True)
    print(json.dumps(run(parser.parse_args().target), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
