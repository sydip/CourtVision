"""One-off backfill of player bios (CommonPlayerInfo) for players missing a profile.

Bios are season-independent, so every player who appears in any stored season but
lacks a position is fetched once here. Runs in small batches so a single bad record
cannot roll back the whole backfill.
"""

from __future__ import annotations

from sqlalchemy import exists, select

from app.core.config import get_settings
from app.data.providers.nba_api import NbaApiProvider
from app.db.session import create_session_factory, session_scope
from app.ingestion.pipeline import run_provider_ingestion
from app.models import Player, PlayerSeasonSummary

BATCH_SIZE = 40
NOMINAL_SEASON = "2024-25"


def main() -> int:
    settings = get_settings()
    factory = create_session_factory()
    with session_scope(factory) as session:
        appears = exists().where(PlayerSeasonSummary.player_id == Player.id)
        ids = list(
            session.scalars(
                select(Player.nba_player_id).where(appears, Player.position.is_(None))
            ).all()
        )

    print(f"backfilling bios for {len(ids)} players in batches of {BATCH_SIZE}", flush=True)
    done = 0
    failed_batches = 0
    for start in range(0, len(ids), BATCH_SIZE):
        batch = ids[start : start + BATCH_SIZE]
        provider = NbaApiProvider(
            season=NOMINAL_SEASON,
            raw_data_dir=settings.raw_data_dir,
            timeout_seconds=settings.api_request_timeout_seconds,
            player_ids=batch,
            player_limit=None,
            request_delay_seconds=0.6,
        )
        try:
            with session_scope(factory) as session:
                run_provider_ingestion(
                    session,
                    provider,
                    NOMINAL_SEASON,
                    source="nba_api:profile-backfill",
                    steps=("profiles",),
                    progress=None,
                    raise_on_failure=True,
                )
            done += len(batch)
        except Exception as exc:  # noqa: BLE001 - keep going past a bad batch
            failed_batches += 1
            print(f"  batch {start // BATCH_SIZE} failed: {exc}", flush=True)
        print(f"  progress: {done}/{len(ids)} bios written", flush=True)

    print(f"DONE bios={done} failed_batches={failed_batches}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
