from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import fmean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.awards_predictor import predict_awards
from app.analytics.standings_predictor import predict_standings
from app.models import AwardHistory, TeamSeasonStat


@dataclass(frozen=True)
class BacktestResult:
    season: str
    award_hit_rate: float | None
    standings_mean_absolute_error: float | None
    evaluated_awards: int
    evaluated_teams: int
    warnings: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_backtest(session: Session, season: str) -> BacktestResult:
    warnings: list[str] = []
    award_rows = session.scalars(
        select(AwardHistory).where(
            AwardHistory.season == season,
            AwardHistory.player_id.is_not(None),
        )
    ).all()
    hits: list[float] = []
    for award_row in award_rows:
        try:
            prediction = predict_awards(
                session,
                season,
                award_row.award_type,
                limit=5,
                persist=False,
                _historical_backtest=True,
            )
        except ValueError:
            continue
        predicted_ids = {candidate.entity_id for candidate in prediction.candidates}
        actual_player = award_row.player_id
        hits.append(1.0 if actual_player in predicted_ids else 0.0)
    if not award_rows:
        warnings.append(f"No award history is stored for {season}.")

    actual_teams = {
        row.team_id: row
        for row in session.scalars(
            select(TeamSeasonStat).where(
                TeamSeasonStat.season == season,
                TeamSeasonStat.wins.is_not(None),
            )
        )
    }
    errors: list[float] = []
    if actual_teams:
        standings = predict_standings(
            session,
            season,
            persist=False,
            _historical_backtest=True,
        )
        for projected in standings.teams:
            actual_team = actual_teams.get(projected.team_id)
            if actual_team is not None and actual_team.wins is not None:
                errors.append(abs(projected.projected_wins - actual_team.wins))
    else:
        warnings.append(f"No completed team season records are stored for {season}.")

    return BacktestResult(
        season=season,
        award_hit_rate=fmean(hits) if hits else None,
        standings_mean_absolute_error=fmean(errors) if errors else None,
        evaluated_awards=len(hits),
        evaluated_teams=len(errors),
        warnings=warnings,
    )
