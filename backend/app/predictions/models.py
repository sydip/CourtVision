from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]


@dataclass
class ModelBundle:
    target: str
    feature_names: tuple[str, ...]
    training_seasons: tuple[str, ...]
    pipeline: Pipeline
    model_version: str = "logistic-v1"
    experimental: bool = True


def create_logistic_pipeline(random_seed: int = 42) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000, class_weight="balanced", random_state=random_seed
                ),
            ),
        ]
    )


def save_bundle(bundle: ModelBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)


def load_bundle(path: Path) -> ModelBundle:
    value: Any = joblib.load(path)
    if not isinstance(value, ModelBundle):
        raise TypeError("Artifact is not a CourtVision model bundle.")
    return value
