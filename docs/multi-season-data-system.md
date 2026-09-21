# Multi-season data system

## Scope

CourtVision stores global player and team identities once and connects season-dependent records to canonical `YYYY-YY` season slugs. Historical analytics are supported for `2021-22`, `2022-23`, `2023-24`, `2024-25`, and `2025-26`. `2026-27` is the gated prediction season.

## Data lifecycle

```text
Explicit batch job
  -> nba_api provider
  -> timestamped raw JSON cache
  -> validation and normalization
  -> PostgreSQL upserts
  -> season-scoped analytics rebuild
  -> FastAPI database responses
  -> season-aware frontend queries
```

Frontend and ordinary API page requests stop at the database layer; they do not call the external NBA provider. Raw cache envelopes identify the source endpoint, season, fetch time, query parameters, and payload. Unique constraints plus upserts make repeated ingestion idempotent and sync runs record fetched, inserted, updated, rejected, and failed counts.

## Season isolation

Season-dependent repository queries must include a season predicate. The global selector persists its canonical slug in the URL and local storage, and frontend query keys include the selected season. An explicitly unsupported season is rejected rather than silently replaced with `2025-26`.

Players and teams are global identities. Game statistics, summaries, standings snapshots, roster memberships, awards, injuries where available, synchronization records, and predictions carry a season. Roster memberships permit multiple teams per player in one season so trades can be represented.

## Operational sequence

Run from `backend/`:

```powershell
python -m alembic upgrade head
python -m app.jobs.ingest_all_seasons --from-season 2021-22 --to-season 2025-26
python -m app.jobs.rebuild_analytics --all-seasons
```

Verify each season independently:

```powershell
python -m app.jobs.verify_season --season 2021-22
python -m app.jobs.verify_season --season 2022-23
python -m app.jobs.verify_season --season 2023-24
python -m app.jobs.verify_season --season 2024-25
python -m app.jobs.verify_season --season 2025-26
```

An ingestion failure should be investigated from its sync-run totals and cached response. Do not repair gaps with fabricated rows.

## Deterministic analytics

Analytics load only the requested season’s game logs and sort them by game date. Stored outputs include season totals and averages, per-36 production, rolling 5- and 10-game values, home/away and rest splits, true shooting and effective field goal percentage, eligible league/position/minutes-tier percentiles, and similarity vectors.

Small samples, missing minutes or usage, zero attempts, trades, and incomplete logs generate warnings or missing values. Percentile populations and similarity candidates are season-specific.

Historical standings use stored team summaries and snapshots. A snapshot is identified as current, final regular season, or projected. Projected records must never be presented as observed historical results.

## Grounded assistant retrieval

The assistant parses a supported intent, resolves player/team names and abbreviations, extracts season/date/opponent/stat filters, and calls predefined repository-backed tools. It does not execute arbitrary SQL supplied by a language model.

Evidence accompanies answers when records exist. Exact player-game questions require a matching stored game date, player, and optional opponent. Missing or ambiguous records produce explicit no-data or clarification responses. Prediction questions are routed separately and remain subject to the 2026–27 gate.

## Limitations

Coverage reflects completed ingestion and upstream availability. Historical injuries, awards, lineups, and roster transaction dates may be incomplete. External endpoint behavior can change, and raw data redistribution may be restricted. Keep caches private unless their terms permit publication.
