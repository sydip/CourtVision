from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.data.normalization import (
    normalize_game,
    normalize_league_player_statistic,
    normalize_player,
    normalize_player_game_log,
    normalize_player_profile,
    normalize_team,
)
from app.data.providers import BasketballDataProvider
from app.data.quality import (
    RejectedRecord,
    validate_games,
    validate_league_player_statistics,
    validate_player_game_logs,
    validate_player_profiles,
    validate_players,
    validate_teams,
)
from app.ingestion.upserts import (
    RecordRejectedError,
    UpsertOutcome,
    refresh_days_since_previous_game,
    upsert_game,
    upsert_player,
    upsert_player_game_stat,
    upsert_player_profile,
    upsert_player_season_summary,
    upsert_roster_membership,
    upsert_standing,
    upsert_team,
    upsert_team_game_stat,
)
from app.models import SyncRun

logger = logging.getLogger(__name__)

IngestionStep = Literal[
    "teams",
    "players",
    "profiles",
    "games",
    "game_logs",
    "league_statistics",
    "rosters",
    "team_game_logs",
    "standings",
]
ALL_INGESTION_STEPS: tuple[IngestionStep, ...] = (
    "teams",
    "players",
    "profiles",
    "games",
    "game_logs",
    "league_statistics",
    "rosters",
    "team_game_logs",
    "standings",
)
ProgressReporter = Callable[[str, "IngestionSummary"], None]


@dataclass
class IngestionSummary:
    source: str
    season: str
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    rejections: list[RejectedRecord] | None = None
    sync_run_id: int | None = None
    status: str = "running"
    error_message: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "season": self.season,
            "status": self.status,
            "fetched": self.fetched,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "rejected": self.rejected,
            "error_message": self.error_message,
            "sync_run_id": self.sync_run_id,
            "rejections": [asdict(rejection) for rejection in self.rejections or []],
        }


def run_fixture_ingestion(
    session: Session,
    provider: BasketballDataProvider,
    season: str,
    source: str = "fixture",
) -> IngestionSummary:
    return run_provider_ingestion(
        session,
        provider,
        season,
        source=source,
        steps=ALL_INGESTION_STEPS,
    )


def run_provider_ingestion(
    session: Session,
    provider: BasketballDataProvider,
    season: str,
    *,
    source: str,
    steps: tuple[IngestionStep, ...],
    progress: ProgressReporter | None = None,
    raise_on_failure: bool = True,
) -> IngestionSummary:
    summary = IngestionSummary(source=source, season=season, rejections=[])
    sync_run = SyncRun(source=source, season=season, status="running")
    session.add(sync_run)
    session.flush()
    summary.sync_run_id = sync_run.id

    try:
        for step in steps:
            _report_progress(progress, f"starting {step}", summary)
            if step == "teams":
                _ingest_teams(session, provider, summary)
            elif step == "players":
                _ingest_players(session, provider, summary)
            elif step == "profiles":
                _ingest_player_profiles(session, provider, summary)
            elif step == "games":
                _ingest_games(session, provider, summary)
            elif step == "game_logs":
                _ingest_player_game_logs(session, provider, season, summary)
            elif step == "league_statistics":
                _ingest_league_player_statistics(session, provider, season, summary)
            elif step == "rosters":
                _ingest_optional(
                    session,
                    provider,
                    "get_roster_memberships",
                    season,
                    summary,
                    upsert_roster_membership,
                )
            elif step == "team_game_logs":
                _ingest_optional(
                    session, provider, "get_team_game_logs", season, summary, upsert_team_game_stat
                )
            elif step == "standings":
                _ingest_optional(
                    session, provider, "get_standings", season, summary, upsert_standing
                )
            _report_progress(progress, f"completed {step}", summary)
        _finish_sync_run(sync_run, summary)
    except Exception as exc:
        error_message = str(exc)
        if raise_on_failure:
            sync_run.status = "failed"
            sync_run.finished_at = datetime.now(UTC)
            sync_run.error_message = error_message
            sync_run.failed_count = 1
            summary.status = "failed"
            summary.error_message = error_message
            raise
        session.rollback()
        failed_sync_run = SyncRun(
            source=source,
            season=season,
            status="failed",
            finished_at=datetime.now(UTC),
            rows_processed=summary.fetched,
            fetched_count=summary.fetched,
            inserted_count=summary.inserted,
            updated_count=summary.updated,
            rejected_count=summary.rejected,
            error_message=error_message,
            failed_count=1,
        )
        session.add(failed_sync_run)
        session.flush()
        summary.sync_run_id = failed_sync_run.id
        summary.status = "failed"
        summary.error_message = error_message
        _report_progress(progress, f"failed: {error_message}", summary)
        return summary

    session.flush()
    return summary


def _ingest_teams(
    session: Session,
    provider: BasketballDataProvider,
    summary: IngestionSummary,
) -> None:
    records = provider.get_teams()
    summary.fetched += len(records)
    validated = validate_teams(records)
    _record_rejections(summary, validated.rejected)
    for source_record in validated.accepted:
        _record_outcome(summary, upsert_team(session, normalize_team(source_record)))


def _ingest_players(
    session: Session,
    provider: BasketballDataProvider,
    summary: IngestionSummary,
) -> None:
    records = provider.get_players()
    summary.fetched += len(records)
    validated = validate_players(records)
    _record_rejections(summary, validated.rejected)
    for source_record in validated.accepted:
        try:
            outcome = upsert_player(session, normalize_player(source_record))
        except RecordRejectedError as exc:
            _record_rejections(
                summary,
                [
                    RejectedRecord(
                        entity="player",
                        source_id=str(source_record.nba_player_id),
                        reason=str(exc),
                        payload=source_record.model_dump(mode="json"),
                    )
                ],
            )
            continue
        _record_outcome(summary, outcome)


def _ingest_player_profiles(
    session: Session,
    provider: BasketballDataProvider,
    summary: IngestionSummary,
) -> None:
    records = provider.get_player_profiles()
    summary.fetched += len(records)
    validated = validate_player_profiles(records)
    _record_rejections(summary, validated.rejected)
    for source_record in validated.accepted:
        try:
            outcome = upsert_player_profile(session, normalize_player_profile(source_record))
        except RecordRejectedError as exc:
            _record_rejections(
                summary,
                [
                    RejectedRecord(
                        entity="player_profile",
                        source_id=str(source_record.nba_player_id),
                        reason=str(exc),
                        payload=source_record.model_dump(mode="json"),
                    )
                ],
            )
            continue
        _record_outcome(summary, outcome)


def _ingest_games(
    session: Session,
    provider: BasketballDataProvider,
    summary: IngestionSummary,
) -> None:
    records = provider.get_games()
    summary.fetched += len(records)
    validated = validate_games(records)
    _record_rejections(summary, validated.rejected)
    for source_record in validated.accepted:
        try:
            outcome = upsert_game(session, normalize_game(source_record))
        except RecordRejectedError as exc:
            _record_rejections(
                summary,
                [
                    RejectedRecord(
                        entity="game",
                        source_id=source_record.nba_game_id,
                        reason=str(exc),
                        payload=source_record.model_dump(mode="json"),
                    )
                ],
            )
            continue
        _record_outcome(summary, outcome)


def _ingest_player_game_logs(
    session: Session,
    provider: BasketballDataProvider,
    season: str,
    summary: IngestionSummary,
) -> None:
    records = provider.get_season_game_logs(season)
    summary.fetched += len(records)
    validated = validate_player_game_logs(records)
    _record_rejections(summary, validated.rejected)
    for source_record in validated.accepted:
        source_id = f"{source_record.nba_player_id}:{source_record.nba_game_id}"
        try:
            outcome = upsert_player_game_stat(session, normalize_player_game_log(source_record))
        except RecordRejectedError as exc:
            _record_rejections(
                summary,
                [
                    RejectedRecord(
                        entity="player_game_log",
                        source_id=source_id,
                        reason=str(exc),
                        payload=source_record.model_dump(mode="json"),
                    )
                ],
            )
            continue
        _record_outcome(summary, outcome)
    refresh_days_since_previous_game(session, season)


def _ingest_league_player_statistics(
    session: Session,
    provider: BasketballDataProvider,
    season: str,
    summary: IngestionSummary,
) -> None:
    records = provider.get_league_player_statistics(season)
    summary.fetched += len(records)
    validated = validate_league_player_statistics(records)
    _record_rejections(summary, validated.rejected)
    for source_record in validated.accepted:
        source_id = f"{source_record.nba_player_id}:{source_record.season}"
        try:
            outcome = upsert_player_season_summary(
                session,
                normalize_league_player_statistic(source_record),
            )
        except RecordRejectedError as exc:
            _record_rejections(
                summary,
                [
                    RejectedRecord(
                        entity="league_player_statistic",
                        source_id=source_id,
                        reason=str(exc),
                        payload=source_record.model_dump(mode="json"),
                    )
                ],
            )
            continue
        _record_outcome(summary, outcome)


def _record_outcome(summary: IngestionSummary, outcome: UpsertOutcome) -> None:
    if outcome == "inserted":
        summary.inserted += 1
    elif outcome == "updated":
        summary.updated += 1
    else:
        summary.unchanged += 1


def _ingest_optional(
    session: Session,
    provider: BasketballDataProvider,
    method_name: str,
    season: str,
    summary: IngestionSummary,
    upsert: Callable[..., UpsertOutcome],
) -> None:
    loader = getattr(provider, method_name, None)
    if loader is None:
        return
    records = loader(season)
    summary.fetched += len(records)
    for record in records:
        try:
            _record_outcome(summary, upsert(session, record))
        except (RecordRejectedError, ValueError) as exc:
            summary.rejected += 1
            logger.warning("Rejected %s record: %s", method_name, exc)


def _record_rejections(summary: IngestionSummary, rejections: list[RejectedRecord]) -> None:
    if not rejections:
        return
    if summary.rejections is None:
        summary.rejections = []
    for rejection in rejections:
        logger.warning(
            "Rejected %s record %s: %s",
            rejection.entity,
            rejection.source_id,
            rejection.reason,
        )
        summary.rejections.append(rejection)
    summary.rejected += len(rejections)


def _finish_sync_run(sync_run: SyncRun, summary: IngestionSummary) -> None:
    sync_run.status = "completed_with_rejections" if summary.rejected else "completed"
    summary.status = sync_run.status
    sync_run.finished_at = datetime.now(UTC)
    sync_run.rows_processed = summary.fetched
    sync_run.fetched_count = summary.fetched
    sync_run.inserted_count = summary.inserted
    sync_run.updated_count = summary.updated
    sync_run.rejected_count = summary.rejected


def _report_progress(
    progress: ProgressReporter | None, message: str, summary: IngestionSummary
) -> None:
    if progress is not None:
        progress(message, summary)


def stderr_progress(message: str, summary: IngestionSummary) -> None:
    print(
        (
            f"[{summary.source}] {message} "
            f"(fetched={summary.fetched}, inserted={summary.inserted}, "
            f"updated={summary.updated}, rejected={summary.rejected})"
        ),
        file=sys.stderr,
    )
