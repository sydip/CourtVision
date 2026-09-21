# 2026–27 prediction methodology

## Guardrail

The new prediction pipeline only accepts `season=2026-27`. It cannot be used for hypothetical or retrospective predictions for 2021–22 through 2025–26. Historical seasons remain available for factual analysis. The separate Jordan prediction implementation is isolated to 2025–26 and its outputs are not mixed with this pipeline.

## Training data and leakage control

The configured training seasons are:

- `2021-22`
- `2022-23`
- `2023-24`
- `2024-25`
- `2025-26`

Dataset construction rejects feature rows from a season after their label season and rejects `2026-27` training features. Dataset JSON, trained bundles, and metadata are written under `backend/model_artifacts/{target}/` for auditing.

## Targets

### All-NBA

Eligible player rows require at least 40 games and 20 minutes per game. Features include games and minutes, scoring and box-score production, turnovers, true shooting, effective field goal percentage, usage, team wins/rank, previous-season production, and prior All-NBA counts. Stored All-NBA awards provide binary training labels. 2026–27 inference is limited to projected active/two-way roster memberships.

### Standings

Features include previous-season record and ratings, pace, returning minutes/points/rebounds/assists, roster continuity, top-player production, and available conference-strength signals. Some planned inputs, such as roster age and injury risk, can be missing and are retained as missing values for the model pipeline. The current binary training label represents teams reaching 40 wins; displayed ranks and records are experimental transformations of model output, not official schedules or results.

### Finals winner

Features include projected wins/rank/playoff probability, previous-season wins and net rating, top-player strength, continuity, offensive/defensive ratings, conference strength, and available playoff signals. Champion labels come from stored Finals series winners. Because there is only one champion per completed season, this target has very few positive examples and is the least certain model.

## Model family and outputs

Each target uses a scikit-learn logistic-regression-style classification pipeline with deterministic training defaults. Persisted runs record model/version, feature-set version, training seasons, status, timestamps, errors, and results. Result probabilities are model estimates. Top factors are explanations derived from stored feature metadata; they do not establish causation.

## Commands

Run from `backend/` after ingestion, analytics rebuilds, and migrations:

```powershell
python -m app.jobs.build_prediction_dataset --target all_nba
python -m app.jobs.build_prediction_dataset --target standings
python -m app.jobs.build_prediction_dataset --target finals_winner

python -m app.jobs.train_prediction_models --target all_nba
python -m app.jobs.train_prediction_models --target standings
python -m app.jobs.train_prediction_models --target finals_winner
```

An explicit API run requires corresponding artifacts and eligible 2026–27 feature rows:

```http
POST /api/predictions/2026-27/run
Content-Type: application/json

{"predictionType":"all_nba"}
```

## Limitations and prohibited use

- Five historical seasons are a small training sample.
- Missing labels or features can prevent training or reduce confidence.
- Projected rosters can change after inference.
- Trades, role changes, injuries, and availability are difficult to anticipate.
- A probability is not a factual outcome or guarantee.
- Finals probabilities are especially uncertain because positive labels are scarce.
- Outputs are experimental and must not be used as betting advice.
- The assistant may summarize stored model results but must not invent a run or probability.
