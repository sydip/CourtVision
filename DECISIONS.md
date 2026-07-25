# HoopsIQ Decisions

This document records architecture decisions for phase 0. It should guide later phases without implying that product behavior has been implemented.

## Architecture Decisions

1. HoopsIQ will use a monorepo-style project structure rooted at `HoopsIQ/`.
2. `apps/web` will own the Next.js App Router frontend.
3. `hoopsiq/api` will own FastAPI route registration and API boundary logic.
4. `hoopsiq/providers` will own basketball data provider contracts and implementations.
5. `hoopsiq/ingestion` will own batch sync orchestration, raw-response capture, validation, and normalization.
6. `hoopsiq/persistence` will own SQLAlchemy models, sessions, and database configuration.
7. `hoopsiq/repositories` will own database reads, writes, and upserts.
8. `hoopsiq/analytics` will own season summaries, rolling averages, TS%, splits, benchmarks, and trends.
9. `hoopsiq/reports` will own deterministic report generation once created.
10. `hoopsiq/similarity` will own statistical player similarity once created.
11. PostgreSQL is the source of truth for normal API and page requests.
12. External NBA data access is allowed only in batch ingestion jobs.
13. The MVP must not use an LLM for report generation.

## Data-Flow Rules

Canonical flow:

```text
batch ingestion command
-> BasketballDataProvider
-> raw response cache
-> validation
-> normalization
-> database upserts
-> analytics services
-> FastAPI routes
-> Next.js UI
```

Rules:

- Browser requests must never call `nba_api`.
- FastAPI route handlers for normal requests must never call `nba_api`.
- `NbaApiProvider` may call `nba_api` only from ingestion commands.
- `CachedResponseProvider` replays stored raw provider responses.
- `FixtureProvider` supplies deterministic offline test data.
- Raw provider responses are saved before normalization.
- Malformed records are counted, logged, and surfaced; they are not silently discarded.
- Database writes use upserts and uniqueness constraints.
- Every sync attempt is recorded in `sync_runs`.
- Failed syncs preserve the last successful data.
- API responses expose data-freshness timestamps when data-bearing endpoints are implemented.
- UTC is used internally for timestamps.

## Database Decisions

Planned MVP tables:

- `teams`
- `players`
- `games`
- `player_game_stats`
- `player_season_summaries`
- `sync_runs`
- `raw_provider_responses`
- Optional `performance_reports`

Core uniqueness constraints:

- `teams.provider_team_id`
- `players.provider_player_id`
- `games.provider_game_id`
- `player_game_stats(player_id, game_id)`
- `player_season_summaries(player_id, season)`
- `raw_provider_responses(provider, endpoint, cache_key)`

## Naming Conventions

Python:

- Modules and functions use `snake_case`.
- Classes use `PascalCase`.
- Provider classes end with `Provider`.
- Repository classes end with `Repository`.
- Pydantic schemas end with `Request`, `Response`, or `DTO` when helpful.

TypeScript:

- React components use `PascalCase`.
- Hooks start with `use`.
- Zod schemas end with `Schema`.
- API client functions use verb-noun names, such as `getPlayerSummary`.

Database:

- Tables and columns use `snake_case`.
- Tables use plural names.
- Constraint names use prefixes such as `uq_`, `ix_`, and `fk_`.
- Provider IDs keep source names explicit, such as `nba_api_player_id`.

Environment:

- Application-specific variables use the `HOOPSIQ_` prefix.
- `.env.example` uses safe placeholder values.
- Real credentials are not committed.

## Testing Strategy

Backend:

- Use Pytest.
- Use fixture data by default.
- Do not require internet access.
- Test providers, validation failures, ingestion, raw-response persistence, upserts, sync failure behavior, analytics calculations, API schemas, and deterministic reports.

Frontend:

- Use Vitest and React Testing Library.
- Validate API boundaries with typed fixtures and Zod schemas.
- Test loading, error, empty, stale, and success states.
- Test search, profile, game logs, charts, splits, benchmarks, reports, and comparison components as they are implemented.

End to end:

- Use Playwright after the dashboard is interactive.
- Run against fixture-backed services.
- Cover player search, profile, comparison, report, and data-freshness flows.

CI:

- Run backend linting, type checks, and Pytest.
- Run frontend linting, TypeScript checks, Vitest, and Playwright.
- Avoid network-dependent checks.

## Deferred Features

Out of scope for the MVP:

- Authentication.
- Live scores.
- Predictions.
- Fantasy scoring.
- Betting functionality.
- Injury tracking.
- Shot charts.
- Multiple seasons.
- Mobile apps.
- LLM-generated analysis.

Deferred until their planned phases:

- Live `nba_api` ingestion.
- Data normalization and upserts.
- Season analytics.
- Player profile API and UI.
- Comparison engine.
- Deterministic reports.
- Statistical similarity.
- Deployment hardening.

## Phase Boundary Rules

- Phase 0 is documentation, audit, and planning only.
- Phase 1 should create and verify repository and Docker setup.
- Later phases should not start automatically.
- Every phase should finish with summary, files changed, migrations, commands, tests, limitations, commit message, and acceptance status.
