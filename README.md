# CourtVision

CourtVision (repository package name: CourtVision) is a multi-season NBA statistics and analytics application. It combines a Next.js frontend, FastAPI backend, PostgreSQL storage, batch NBA data ingestion, deterministic historical analytics, a database-grounded assistant, and experimental 2026–27 prediction models.

Supported historical seasons are `2021-22` through `2025-26`. The `2026-27` season is reserved for the new All-NBA, standings, and Finals prediction services. Normal page requests read PostgreSQL and never call NBA.com or `nba_api`.

## Repository layout

```text
frontend/             Next.js, TypeScript, Zod, Recharts, Vitest
backend/              FastAPI, SQLAlchemy, Alembic, analytics and prediction jobs
data/raw/{season}/    Timestamped raw ingestion cache (not application responses)
docs/                 System and operator documentation
backend/docs/         Backend-specific prediction documentation
docker-compose.yml    Local PostgreSQL service
```

## Local setup

Requirements:

- Python 3.11 or newer
- Node.js 20 or newer
- Docker with Docker Compose

Create local environment files:

```powershell
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```

Start PostgreSQL:

```powershell
docker compose up -d db
```

Install the backend and frontend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cd ..\frontend
npm install
```

## Environment variables

| Variable                              | Purpose                                 | Typical local value                                                |
| ------------------------------------- | --------------------------------------- | ------------------------------------------------------------------ |
| `DATABASE_URL`                        | SQLAlchemy PostgreSQL connection        | `postgresql://courtvision:courtvision_dev_password@localhost:5432/courtvision` |
| `NEXT_PUBLIC_API_BASE_URL`            | Browser-visible FastAPI base URL        | `http://localhost:8000`                                            |
| `NBA_SEASON`                          | Legacy/default application season       | `2025-26`                                                          |
| `RAW_DATA_DIR`                        | Raw ingestion cache location            | `../data/raw` from `backend/`                                      |
| `API_REQUEST_TIMEOUT_SECONDS`         | External provider timeout               | `20`                                                               |
| `BENCHMARK_MINIMUM_GAMES`             | Minimum sample for benchmarks           | `15`                                                               |
| `BENCHMARK_MINIMUM_MINUTES_PER_GAME`  | Benchmark minutes threshold             | `10`                                                               |
| `BENCHMARK_SIMILAR_MINUTES_TOLERANCE` | Similar-player minutes tolerance        | `3`                                                                |
| `ANTHROPIC_API_KEY`                   | Optional legacy Jordan tool-calling key | blank                                                              |
| `ANTHROPIC_MODEL`                     | Optional legacy Jordan model identifier | configured in the example file                                     |

Do not commit populated `.env` files or provider credentials.

## Database migrations

All backend commands below run from `backend/` with the virtual environment active.

```powershell
python -m alembic upgrade head
python -m alembic current
```

To test the immediately preceding downgrade during migration development:

```powershell
python -m alembic downgrade -1
python -m alembic upgrade head
```

Avoid `alembic downgrade base` against a database containing data you need to preserve.

## Historical ingestion

Ingestion is the only normal workflow allowed to contact the external NBA provider. Every successful raw response is cached before normalization and database upsert.

Ingest one season:

```powershell
python -m app.jobs.ingest_season --season 2021-22
python -m app.jobs.ingest_season --season 2025-26
```

Ingest all supported historical seasons:

```powershell
python -m app.jobs.ingest_all_seasons --from-season 2021-22 --to-season 2025-26
```

Verify a season after ingestion:

```powershell
python -m app.jobs.verify_season --season 2023-24
```

Jobs are season-parameterized and use database constraints/upserts to avoid duplicate rows. Raw payloads are written below `data/raw/{season}/{endpoint}/`. Provider availability, rate limiting, and incomplete upstream records can still require a retry.

## Analytics rebuilds

Analytics rebuilds are database-only and do not download data.

```powershell
python -m app.jobs.rebuild_analytics --season 2024-25
python -m app.jobs.rebuild_analytics --all-seasons
```

Rebuilds calculate season summaries, totals, per-game and per-36 values, rolling windows, splits, efficiency, percentiles, similarity vectors, team leaders, and standings summaries using only the requested season.

## Prediction datasets and training

Predictions are experimental and strictly gated to `2026-27`. Training data comes from stored `2021-22` through `2025-26` records. Valid targets are `all_nba`, `standings`, and `finals_winner`.

Build auditable JSON datasets:

```powershell
python -m app.jobs.build_prediction_dataset --target all_nba
python -m app.jobs.build_prediction_dataset --target standings
python -m app.jobs.build_prediction_dataset --target finals_winner
```

Train model artifacts:

```powershell
python -m app.jobs.train_prediction_models --target all_nba
python -m app.jobs.train_prediction_models --target standings
python -m app.jobs.train_prediction_models --target finals_winner
```

Artifacts are stored under `backend/model_artifacts/{target}/`. Training fails when required labels or eligible rows are unavailable; do not substitute invented labels or results.

After training and after projected 2026–27 feature rows/rosters exist, request an explicit prediction run:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/predictions/2026-27/run -ContentType application/json -Body '{"predictionType":"all_nba"}'
```

Repeat with `standings` or `finals_winner`. Prediction API requests for other seasons are rejected.

## Run the application

Backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm run dev
```

- Frontend: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- Methodology page: `http://localhost:3000/methodology`
- AI Assistant: `http://localhost:3000/ai-assistant`

## Tests and quality checks

Backend:

```powershell
cd backend
python -m ruff check .
python -m mypy app
python -m pytest
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm run lint
npm run prettier:check
npm test
npm run build
```

Backend ingestion tests use fixtures and mocks; test runs must not depend on live NBA.com responses.

## Assistant and prediction safety

The assistant resolves supported players, teams, dates, seasons, opponents, and statistics to predefined repository queries. Factual answers must be backed by PostgreSQL evidence. Missing records remain missing; arbitrary model-generated SQL and invented NBA facts are not allowed.

The new prediction family is available only for 2026–27. The separate legacy Jordan prediction experience remains limited to 2025–26. Prediction probabilities are model estimates, not facts, guarantees, or betting recommendations.

## Data limitations

- External NBA endpoints can be rate-limited, unavailable, or incomplete.
- Historical roster, injury, award, and lineup coverage depends on what has been ingested.
- Missing minutes, attempts, positions, and usage fields can limit analytics.
- Traded players can have multiple team memberships within one season.
- Percentiles and similarity results depend on the eligible population for that season.
- Five training seasons are a small sample; the Finals target has especially few positive examples.
- Projected rosters, injuries, trades, and role changes can materially reduce 2026–27 prediction accuracy.

## Copyright-safe public assets

CourtVision is an independent analytics project and is not affiliated with or endorsed by the NBA or its teams. NBA and team names, statistics, logos, player likenesses, broadcast footage, and related marks may be owned by their respective rights holders.

For a public GitHub repository:

- Use original interface artwork, CSS shapes, and self-created icons.
- Use licensed, public-domain, or permission-cleared photographs and fonts.
- Record the source and license for every third-party asset.
- Do not commit NBA/team logos, player photographs, broadcast screenshots, video, or scraped media unless redistribution rights are documented.
- Do not imply official NBA or team affiliation.
- Keep raw data caches, secrets, model artifacts containing restricted data, and large generated files out of Git unless their redistribution terms are clear.

See [docs/multi-season-data-system.md](docs/multi-season-data-system.md) and [backend/docs/prediction-methodology.md](backend/docs/prediction-methodology.md) for implementation details.
