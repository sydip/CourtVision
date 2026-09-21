from __future__ import annotations

from collections import Counter

from app.predictions.datasets import PredictionDataset, assert_no_future_leakage
from app.predictions.models import ModelBundle, create_logistic_pipeline


def train_model(dataset: PredictionDataset, random_seed: int = 42) -> ModelBundle:
    assert_no_future_leakage(dataset)
    if not dataset.rows:
        raise ValueError("Prediction dataset is empty.")
    if len(Counter(dataset.labels)) < 2:
        raise ValueError("Prediction dataset requires positive and negative examples.")
    pipeline = create_logistic_pipeline(random_seed)
    pipeline.fit(dataset.matrix(), dataset.labels)
    return ModelBundle(dataset.target, dataset.feature_names, dataset.training_seasons, pipeline)
