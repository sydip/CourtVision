# HoopsIQ Project Plan

Phase 0 status: complete.

Date: 2026-06-25

This phase audits the current workspace and defines the implementation plan for HoopsIQ. It does not implement product features, database models, API routes, ingestion jobs, analytics, or UI flows.

## Current Workspace Audit

The inspected workspace is `C:\Users\saide\OneDrive\Documents\Playground`.

Top-level directories observed:

- `.git/`: Git repository metadata.
- `Build4Good/`: unrelated static React project named Quiet Skies.
- `chrome-pdf-profile/`: generated Chrome profile artifacts.
- `node_modules/`: existing JavaScript dependencies, but no root package manifest was found.
- `outputs/`: generated analysis artifacts.
- `tmp/`, `tmplp9u7n8f/`, `__pycache__/`: temporary/cache artifacts.

Top-level files observed:

- `Circle_Data_Updated.xlsx`
- `generate_circle_excel.py`
- `Homework 4 Answers.html`
- `Homework 4 Answers.md`
- `Homework 4 Answers.pdf`
- `homework4.txt`
- `lab6_analysis.json`
- `lab6_analysis.py`
- `lab6_builder.mjs`
- `slides_algorithms.txt`
- `slides_functions.txt`

## Existing Configuration By Area

Frontend:

- Existing: `Build4Good/index.html`, `Build4Good/styles.css`, vendored React bundles, and JavaScript under `Build4Good/js/`.
- Missing for HoopsIQ: Next.js App Router, TypeScript, Tailwind CSS, Recharts, TanStack Query, Zod, Vitest, React Testing Library, and Playwright setup.

Backend:

- Existing: unrelated Python snapshot script under `Build4Good/scripts/fetch_neo_snapshot.py`.
- Missing for HoopsIQ: FastAPI application, Pydantic schemas, settings module, structured logging, provider interfaces, ingestion jobs, and service layer.

Database:

- Existing: no PostgreSQL, SQLAlchemy, or Alembic configuration found.
- Missing for HoopsIQ: database connection settings, SQLAlchemy models, Alembic migrations, uniqueness constraints, upsert helpers, raw response persistence, and `sync_runs`.

Testing:

- Existing: `Build4Good/tests/test_snapshot_builder.py`, using Python `unittest` for the unrelated Quiet Skies project.
- Missing for HoopsIQ: Pytest, Vitest, React Testing Library, Playwright, fixture data, test database setup, and offline provider tests.

Docker and CI:

- Existing: no HoopsIQ Docker or CI configuration found.
- Missing for HoopsIQ: Docker Compose, Dockerfiles, `.env.example`, GitHub Actions workflow, and local dev commands.

Repository hygiene:

- Most visible workspace files are untracked.
- No unrelated files were deleted during phase 0.
- HoopsIQ phase 0 artifacts should be placed at `C:\Users\saide\.vscode\HoopsIQ`.

## Missing Dependencies And Configuration

Backend dependencies to add in later phases:

- `fastapi`
- `uvicorn`
- `pydantic`
- `pydantic-settings`
- `sqlalchemy`
- `alembic`
- `psycopg[binary]` or `asyncpg`
- `pandas`
- `numpy`
- `scikit-learn`
- `nba_api`
- `httpx`
- `tenacity`
- `structlog`
- `pytest`
- `pytest-cov`
- `ruff`
- `mypy`

Frontend dependencies to add in later phases:

- `next`
- `react`
- `react-dom`
- `typescript`
- `tailwindcss`
- `postcss`
- `autoprefixer`
- `recharts`
- `@tanstack/react-query`
- `zod`
- `vitest`
- `@testing-library/react`
- `@testing-library/jest-dom`
- `@playwright/test`
- `eslint`

Configuration to add in later phases:

- Root `.gitignore`, `.env.example`, and README.
- Frontend `package.json`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `postcss.config.mjs`, Vitest config, and Playwright config.
- Backend `pyproject.toml`, FastAPI settings, Pytest config, Ruff/Mypy config, and structured logging setup.
- Database `alembic.ini`, `migrations/env.py`, and migration versions.
- Docker Compose and service Dockerfiles.
- GitHub Actions CI workflow.

## Proposed Final Repository Structure

```text
HoopsIQ/
|-- PROJECT_PLAN.md
|-- DECISIONS.md
|-- README.md
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|-- apps/
|   |-- web/
|   |   |-- app/
|   |   |-- components/
|   |   |-- features/
|   |   |-- lib/
|   |   |   |-- api/
|   |   |   |-- query/
|   |   |   `-- schemas/
|   |   |-- tests/
|   |   `-- playwright/
|   `-- api/
|       `-- Dockerfile
|-- hoopsiq/
|   |-- api/
|   |   `-- routes/
|   |-- analytics/
|   |-- ingestion/
|   |   |-- jobs/
|   |   `-- normalization/
|   |-- persistence/
|   |-- providers/
|   |-- repositories/
|   |-- reports/
|   |-- schemas/
|   `-- similarity/
|-- migrations/
|   |-- env.py
|   `-- versions/
|-- data/
|   |-- fixtures/
|   `-- raw-cache/
|-- docs/
|-- scripts/
`-- tests/
    |-- api/
    |-- analytics/
    |-- integration/
    |-- providers/
    `-- persistence/
```

This structure separates frontend, backend API, data ingestion, analytics, persistence, providers, reports, similarity, fixture data, and tests.

## Phase Checklist

### Phase 0: Repository Audit And Implementation Plan

- [x] Inspect current files and directories.
- [x] Identify existing frontend, backend, database, testing, Docker, and CI configuration.
- [x] Identify missing dependencies and configuration.
- [x] Propose final repository structure.
- [x] Create `PROJECT_PLAN.md`.
- [x] Create `DECISIONS.md`.
- [x] Avoid deleting unrelated files.
- [x] Stop before implementing product behavior.

### Phase 1: Repository And Docker Setup

- [ ] Create the HoopsIQ project scaffold.
- [ ] Add root README, `.gitignore`, and `.env.example`.
- [ ] Scaffold Next.js App Router with TypeScript.
- [ ] Scaffold FastAPI with Python 3.11.
- [ ] Add Docker Compose for web, API, PostgreSQL, and ingestion commands.
- [ ] Add baseline lint, type-check, and test commands.
- [ ] Add CI skeleton.

### Phase 2: Database Models And Migrations

- [ ] Define `players`, `teams`, `games`, `player_game_stats`, `player_season_summaries`, and `sync_runs`.
- [ ] Add optional `performance_reports` only if report persistence is needed.
- [ ] Add raw provider response persistence.
- [ ] Add uniqueness constraints and indexes.
- [ ] Create Alembic migration and migration tests.

### Phase 3: Mock Dashboard

- [ ] Build mock dashboard UI without live NBA data.
- [ ] Add player search, profile, game log, splits, trends, benchmarks, report, and comparison mock views.
- [ ] Add loading, error, and empty states.
- [ ] Add frontend component tests.

### Phase 4: Provider Interfaces And Fixture Provider

- [ ] Define `BasketballDataProvider`.
- [ ] Implement `FixtureProvider`.
- [ ] Add provider payload validation.
- [ ] Add offline provider tests.

### Phase 5: `nba_api` Provider And Raw-Response Cache

- [ ] Implement `NbaApiProvider` for batch jobs only.
- [ ] Implement `CachedResponseProvider`.
- [ ] Add request timeouts and retries.
- [ ] Save raw responses before normalization.

### Phase 6: Data Normalization And Upserts

- [ ] Normalize players, teams, games, and player game stats.
- [ ] Validate external data before writes.
- [ ] Use database upserts.
- [ ] Record sync runs.
- [ ] Preserve last successful data on failure.

### Phase 7: Season-Summary Analytics

- [ ] Calculate season averages.
- [ ] Calculate true-shooting percentage.
- [ ] Calculate five-game and ten-game rolling averages.
- [ ] Calculate home/away and rest-day splits.
- [ ] Calculate league and position percentiles.
- [ ] Add trend classifications and sample-size warnings.

### Phase 8: Player Search And Profile API

- [ ] Implement required season, player, health, and data-status API routes.
- [ ] Add Pydantic schemas at API boundaries.
- [ ] Add fixture-backed API tests.

### Phase 9: Player Profile Interface

- [ ] Connect search and player pages to the API.
- [ ] Display profile, averages, game logs, rolling averages, splits, benchmarks, trends, reports, and freshness.

### Phase 10: Comparison Engine And Page

- [ ] Compare two players side by side.
- [ ] Compare each player against league and position averages.
- [ ] Add comparison API and UI tests.

### Phase 11: Report Generator

- [ ] Generate deterministic reports from structured analytics.
- [ ] Trace every numeric sentence to input fields.
- [ ] Include warnings and trend classifications.

### Phase 12: Similarity Engine

- [ ] Standardize per-36, efficiency, usage, and minutes features.
- [ ] Use cosine similarity.
- [ ] Exclude players below configurable minute thresholds.
- [ ] Describe results as statistical similarity.

### Phase 13: Automated Tests

- [ ] Expand Pytest, Vitest, React Testing Library, and Playwright coverage.
- [ ] Ensure tests use fixtures and do not require internet access.
- [ ] Add CI enforcement.

### Phase 14: Deployment And Documentation

- [ ] Document setup, ingestion, API routes, operations, and deployment.
- [ ] Confirm no secrets or raw credentials are committed.

## Phase 0 Acceptance Criteria

- [x] Existing code has been inspected.
- [x] No unrelated files were deleted.
- [x] `PROJECT_PLAN.md` exists.
- [x] `DECISIONS.md` exists.
- [x] Proposed structure separates frontend, backend, data ingestion, analytics, and tests.
- [x] The next phase can begin without architectural ambiguity.

## Commands Run During Phase 0

```powershell
Get-ChildItem -Force
rg --files -g '!node_modules/**' -g '!chrome-pdf-profile/**' -g '!__pycache__/**' -g '!outputs/**' -g '!tmp/**' -g '!tmplp9u7n8f/**'
rg --files -g 'package.json' -g 'pyproject.toml' -g 'alembic.ini' -g 'Dockerfile' -g 'docker-compose*.yml' -g '.gitignore'
git status --short
```

## Tests Executed

No tests were executed. Phase 0 is documentation and planning only.

## Recommended Git Commit Message

```text
docs: add HoopsIQ phase 0 plan
```
