# HoopsIQ Backend

## Database Initialization

Start PostgreSQL from the repository root:

```powershell
docker compose up -d db
```

Install backend dependencies from `backend/`:

```powershell
python -m pip install -e ".[dev]"
```

Apply the schema:

```powershell
python -m alembic upgrade head
```

Rollback the schema when you need to test downgrade behavior:

```powershell
python -m alembic downgrade base
```

The default `DATABASE_URL` is:

```text
postgresql://hoopsiq:hoopsiq_dev_password@localhost:5432/hoopsiq
```

The app normalizes that URL to SQLAlchemy's `postgresql+psycopg://` driver form at runtime. Tests use an isolated temporary SQLite database by default, while Alembic and the application target PostgreSQL for local development.

## Phase 2 Scope

Included:

- SQLAlchemy models for teams, players, games, player game stats, player season summaries, sync runs, and deterministic performance report caches.
- Alembic initial migration with upgrade and downgrade paths.
- Session factory, FastAPI session dependency, and transactional session scope helper.
- Repository modules for player lookup/search and player game stats.
- Tests for model creation, uniqueness, relationships, duplicate player-game stats, session lifecycle, and migration upgrade/downgrade.

Not included:

- Production report generation.

## Fixture Ingestion

Phase 3 adds an offline provider and fixture ingestion path. It uses local JSON fixtures and does not require internet access.

Run from `backend/` after applying migrations:

```powershell
python -m alembic upgrade head
python -m app.ingestion.cli fixtures --season 2025-26
```

To test with a disposable SQLite database:

```powershell
python -m app.ingestion.cli fixtures --season 2025-26 --database-url sqlite:///./hoopsiq_fixture_check.db --init-schema
```

The fixture command:

- validates source records with Pydantic schemas,
- rejects bad records with logged reasons,
- normalizes provider data into internal records,
- upserts teams, players, profiles, games, player game logs, and player season summaries,
- records fetched, inserted, updated, and rejected totals in `sync_runs`.

## Live NBA API Ingestion

Phase 4 adds a live `nba_api` provider for CLI-only ingestion. Phase 5 extends that provider into a selected-season pipeline with normalized matchups, home/away status, W/L result, fouls, plus-minus, and rest-day calculations. Application routes should read from the database and must not call the live provider directly.

Raw successful responses are stored without modification beneath:

```text
../data/raw/{season}/{endpoint}/{timestamp}.json
```

Each successful response creates a new timestamped file. Existing raw responses are never overwritten. If a live request fails, the provider falls back to the newest cached response for that endpoint. If no cache exists, the command fails with a clear error and leaves existing database data intact.

Start with one explicit player before broader runs:

```powershell
python -m alembic upgrade head
python -m app.ingestion.cli sync-sample-player --season 2025-26 --player-id 201939
```

Targeted live sync commands:

```powershell
python -m app.ingestion.cli sync-players --season 2025-26 --player-limit 1
python -m app.ingestion.cli sync-profiles --season 2025-26 --player-id 201939
python -m app.ingestion.cli sync-game-logs --season 2025-26 --player-id 201939
python -m app.ingestion.cli sync-league-statistics --season 2025-26 --player-id 201939
```

Full selected-season sync:

```powershell
python -m app.ingestion.cli sync-season --season 2025-26
```

Live commands print step-level progress to stderr by default. Add `--quiet` to suppress progress output.

Useful live-provider options:

- `--player-id 201939` can be repeated for a small controlled sample.
- `--player-limit 1` is the default when no explicit player IDs are supplied.
- `--all-players` disables the sample limit.
- `--timeout-seconds`, `--max-retries`, `--backoff-seconds`, and `--request-delay-seconds` control request behavior.

## Data Status API

Phase 5 adds:

```text
GET /api/data-status
```

The response reports the configured season, player count, game count, player-game record count, last successful sync, and last failed sync.

## Application API

Phase 7 adds database-backed FastAPI routes for the frontend. These routes read stored PostgreSQL records and should not call `nba_api`.

Reference data:

```text
GET /api/seasons
GET /api/teams
GET /api/positions
```

Players and analytics:

```text
GET /api/players
GET /api/players/{id}
GET /api/players/{id}/seasons/{season}/summary
GET /api/players/{id}/seasons/{season}/games
GET /api/players/{id}/seasons/{season}/trends
GET /api/players/{id}/seasons/{season}/splits
GET /api/players/{id}/seasons/{season}/benchmarks
GET /api/compare
```

`GET /api/players` supports partial, case-insensitive name search with `q`, `limit`, and `offset`. `GET /api/players/{id}` accepts either the internal player ID or NBA player ID.

Game-log filters:

- `limit`
- `offset`
- `location=home|away`
- `opponent`, by abbreviation or NBA team ID
- `result=W|L`
- `sort=asc|desc`

Errors use a consistent `{"error": {"code": "...", "message": "..."}}` envelope. Paginated endpoints include `meta` with `limit`, `offset`, `total`, `next_offset`, and `previous_offset`.

## Analytics Rebuild

Phase 6 adds pure analytics modules for efficiency, rolling averages, splits, trends, benchmarks, and per-36 calculations. The rebuild job reads stored game logs only; it does not call `nba_api` or download new data.

```powershell
python -m app.ingestion.cli rebuild-analytics --season 2025-26
```

Benchmark thresholds are configurable:

```powershell
python -m app.ingestion.cli rebuild-analytics --season 2025-26 --minimum-games 15 --minimum-minutes-per-game 10 --similar-minutes-tolerance 3
```

Environment defaults:

- `BENCHMARK_MINIMUM_GAMES`
- `BENCHMARK_MINIMUM_MINUTES_PER_GAME`
- `BENCHMARK_SIMILAR_MINUTES_TOLERANCE`

The job updates `player_season_summaries` with calculated true-shooting percentage, per-game metrics, per-36 metrics, benchmark percentiles, trend classifications, exact trend payloads, sample-size warnings, and rebuild timestamp.
