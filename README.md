# HoopsIQ

HoopsIQ is a full-stack NBA player analytics and comparison application. Phase 8 adds the data-backed frontend home and player profile pages on top of the FastAPI, PostgreSQL, ingestion, analytics, and application API foundations.

## Project Layout

```text
HoopsIQ/
|-- frontend/          # Next.js App Router + TypeScript + Tailwind CSS
|-- backend/           # FastAPI + Python 3.11 project, SQLAlchemy, Alembic
|-- docker-compose.yml # PostgreSQL service for local development
|-- .env.example       # Root local development defaults
|-- PROJECT_PLAN.md
`-- DECISIONS.md
```

## Environment Files

Copy the examples before running services:

```powershell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env.local
Copy-Item backend\.env.example backend\.env
```

Expected variables:

- `DATABASE_URL`
- `NEXT_PUBLIC_API_BASE_URL`
- `NBA_SEASON`
- `RAW_DATA_DIR`
- `API_REQUEST_TIMEOUT_SECONDS`
- `BENCHMARK_MINIMUM_GAMES`
- `BENCHMARK_MINIMUM_MINUTES_PER_GAME`
- `BENCHMARK_SIMILAR_MINUTES_TOLERANCE`

The example values are local development placeholders only.

## Start PostgreSQL

```powershell
docker compose up db
```

The database will listen on `localhost:5432`.

## Backend Setup

Use Python 3.11 for the backend environment.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoint:

```text
GET http://localhost:8000/api/health
```

Backend checks:

```powershell
python -m ruff check .
python -m mypy app
python -m pytest
```

Database commands:

```powershell
python -m alembic upgrade head
python -m alembic downgrade base
```

More database setup notes live in `backend/README.md`.

Offline fixture ingestion:

```powershell
cd backend
python -m alembic upgrade head
python -m app.ingestion.cli fixtures --season 2025-26
```

Small live `nba_api` sample ingestion:

```powershell
cd backend
python -m alembic upgrade head
python -m app.ingestion.cli sync-sample-player --season 2025-26 --player-id 201939
```

Successful live responses are cached as timestamped JSON files under `data/raw/{season}/{endpoint}/`. Existing raw responses are never overwritten, and normal app routes should use database data instead of contacting `nba_api`.

Full selected-season ingestion:

```powershell
cd backend
python -m alembic upgrade head
python -m app.ingestion.cli sync-season --season 2025-26
```

Persist the supplied 2026 NBA Draft results idempotently:

```powershell
cd backend
python -m alembic upgrade head
python -m app.ingestion.draft_results
```

Data status endpoint:

```text
GET http://localhost:8000/api/data-status
```

Application API routes:

```text
GET /api/seasons
GET /api/teams
GET /api/positions
GET /api/drafts/2026
GET /api/players
GET /api/players/{id}
GET /api/players/{id}/seasons/{season}/summary
GET /api/players/{id}/seasons/{season}/games
GET /api/players/{id}/seasons/{season}/trends
GET /api/players/{id}/seasons/{season}/splits
GET /api/players/{id}/seasons/{season}/benchmarks
GET /api/compare
POST /api/assistant/chat
GET /api/assistant/capabilities
GET /api/predictions/awards/{award_type}
GET /api/predictions/standings
GET /api/predictions
GET /api/predictions/backtest/{season}
```

Player game logs support `limit`, `offset`, `location`, `opponent`, `result`, and `sort` query parameters. These routes read stored PostgreSQL data and must not contact `nba_api`.

Rebuild stored analytics without downloading new data:

```powershell
cd backend
python -m alembic upgrade head
python -m app.ingestion.cli rebuild-analytics --season 2025-26
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000`. The home page supports player search and data freshness, and player profiles are available at:

```text
http://localhost:3000/players/{nba_player_id}
```

Example:

```text
http://localhost:3000/players/201939
```

Frontend API calls use `NEXT_PUBLIC_API_BASE_URL`, which defaults to the FastAPI service at `http://localhost:8000`.

Frontend checks:

```powershell
npm run lint
npm run typecheck
npm run prettier:check
npm run test
npm run build
```

## NBA Intelligence Assistant

Jordan is a grounded assistant layered on HoopsIQ's PostgreSQL player, team, game-log,
and analytics data. It never uses model memory for NBA facts. Each response records the
database or prediction tool that produced it, and all projections are deterministic,
versioned estimates with feature attributions.

The preseason 2026-27 ROY model uses the stored 2026 draft class. Its score is 75%
draft-position value, 17% opportunity inferred from the destination team's stored
2025-26 rotation, and 8% opportunity after accounting for other 2026 selections on
that team. It does not invent rookie production or use unsupplied college statistics.

The existing `nba_api` ingestion remains the source of real stored player data. New
assistant tables add team-season history, player-team seasons, award history, injuries,
and an append-only prediction log. Rows explicitly carry `data_source` and
`is_synthetic` metadata where applicable.

Open the web assistant at:

```text
http://localhost:3000/assistant
```

Run the same grounded agent from a terminal:

```powershell
cd backend
python -m app.assistant.cli
```

Claude tool-calling is optional. Without an API key, Jordan uses its local deterministic
tool router and remains fully functional:

```dotenv
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

Example questions:

- `What can you do?`
- `Compare Stephen Curry and LeBron James in 2025-26.`
- `Who is your MVP favorite for 2025-26?`
- `Predict the Western Conference standings.`

Prediction probabilities and confidence values are estimates, not guarantees. Award
scores use documented award-specific weighted z-scores followed by softmax. Standings
aggregate rotation production, true shooting, plus-minus, continuity, and stored injury
context before converting projected point differential to an 82-game record.

## Current Scope

Included:

- Next.js App Router frontend with TypeScript.
- Tailwind CSS setup.
- Recharts dependency.
- FastAPI backend with `GET /api/health`.
- PostgreSQL service in Docker Compose.
- ESLint, Prettier, Ruff, MyPy, and Pytest configuration.
- Minimal frontend page that checks backend connectivity.
- SQLAlchemy models for teams, players, games, player game stats, player season summaries, sync runs, and performance report caches.
- Alembic configuration and initial migration.
- Database session helpers and repository modules.
- Persistence tests for model creation, constraints, relationships, session lifecycle, and migration upgrade/downgrade.
- Offline fixture provider, cached response provider, source schemas, validation, normalization, fixture ingestion, and database upserts.
- Sync run totals for fetched, inserted, updated, and rejected records.
- Live `nba_api` provider for CLI ingestion.
- Raw-response caching with newest-cache fallback.
- Sample-first CLI commands for players, profiles, game logs, league statistics, and one-player end-to-end sync.
- Full selected-season ingestion command with step-level progress reporting.
- Normalized matchup, home/away, W/L result, fouls, plus-minus, and rest-day fields on player game logs.
- `GET /api/data-status` for current season counts and sync history.
- Pure analytics modules for efficiency, rolling averages, splits, trends, benchmarks, and per-36 calculations.
- Rebuild analytics command that updates season summaries from stored game logs without network access.
- Configurable benchmark thresholds and sample-size warnings.
- Application-facing FastAPI routes for seasons, teams, positions, player search/detail, season analytics, game logs, splits, trends, benchmarks, comparison, health, and data status.
- Pydantic API response schemas, validation errors, pagination metadata, CORS, OpenAPI descriptions, and integration tests.
- Data-backed frontend home dashboard with season selection, player search, data freshness, sample players, loading states, empty states, and error states.
- Data-backed player profile page with player header, team/position, season summary cards, rolling chart, recent game logs, home/away splits, rest-day splits, percentile bars, and trend badges.
- Typed frontend API clients with Zod response validation and TanStack Query request state.
- Component tests for the home dashboard and player profile views.
- Grounded Jordan assistant with optional Claude tool-calling and a local fallback.
- Explainable, versioned award and standings projections with append-only audit logs.
- Prediction backtesting support with honest missing-history warnings.
- Responsive assistant interface with chat, source badges, probability charts, and model drivers.

Not included yet:

- A learned secondary prediction model; the transparent heuristic remains the required baseline.
- Complete historical award and team-season outcome imports for multi-season backtesting.
