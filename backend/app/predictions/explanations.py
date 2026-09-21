from __future__ import annotations

from typing import Any

from app.predictions.models import ModelBundle


def explain_row(
    bundle: ModelBundle, row: list[float | None], limit: int = 5
) -> list[dict[str, Any]]:
    imputer = bundle.pipeline.named_steps["imputer"]
    scaler = bundle.pipeline.named_steps["scaler"]
    classifier = bundle.pipeline.named_steps["classifier"]
    transformed = scaler.transform(imputer.transform([row]))[0]
    contributions = transformed * classifier.coef_[0]
    ranked = sorted(
        zip(bundle.feature_names, row, contributions, strict=True),
        key=lambda item: abs(float(item[2])),
        reverse=True,
    )
    return [
        {"feature": name, "raw_value": value, "contribution": round(float(contribution), 6)}
        for name, value, contribution in ranked[:limit]
    ]
