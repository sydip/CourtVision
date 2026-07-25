from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from math import exp, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.analytics.features import resolve_source_season
from app.analytics.prediction_types import AwardPredictionResult, RankedCandidate
from app.models import DraftPick, PlayerSeasonSummary, Team

ROY_MODEL_VERSION = "hoopsiq-draft-roy-v1"


@dataclass(frozen=True)
class RookieProjectionFeatures:
    draft_pick_id: int
    player_name: str
    school_country: str
    team_id: int
    team_name: str
    team_abbreviation: str
    overall_pick: int
    draft_position_value: float
    roster_opportunity: float
    same_team_opportunity: float


def load_rookie_projection_features(
    session: Session,
    target_season: str,
) -> tuple[str, list[RookieProjectionFeatures]]:
    draft_year = _season_start_year(target_season)
    draft_picks = session.scalars(
        select(DraftPick)
        .options(joinedload(DraftPick.team))
        .where(DraftPick.draft_year == draft_year)
        .order_by(DraftPick.overall_pick)
    ).all()
    if not draft_picks:
        return "", []

    source_season = resolve_source_season(session, target_season)
    roster_opportunity = _team_roster_opportunity(session, source_season)
    same_team_opportunity = _same_team_draft_opportunity(draft_picks)
    return source_season, [
        RookieProjectionFeatures(
            draft_pick_id=pick.id,
            player_name=pick.player_name,
            school_country=pick.school_country,
            team_id=pick.team.id,
            team_name=f"{pick.team.city} {pick.team.name}",
            team_abbreviation=pick.team.abbreviation,
            overall_pick=pick.overall_pick,
            draft_position_value=1 / sqrt(pick.overall_pick),
            roster_opportunity=roster_opportunity.get(pick.team.id, 0.5),
            same_team_opportunity=same_team_opportunity[pick.id],
        )
        for pick in draft_picks
    ]


def score_rookie_candidates(
    features: list[RookieProjectionFeatures],
    *,
    target_season: str,
    source_season: str,
    limit: int = 10,
) -> AwardPredictionResult:
    if not features:
        raise ValueError(f"No stored draft class is available for {target_season}.")

    weights = {
        "overall_pick": 0.75,
        "roster_opportunity": 0.17,
        "same_team_opportunity": 0.08,
    }
    scored: list[tuple[RookieProjectionFeatures, float, list[dict[str, float | str]]]] = []
    for rookie in features:
        draft_contribution = weights["overall_pick"] * rookie.draft_position_value
        roster_contribution = weights["roster_opportunity"] * rookie.roster_opportunity
        team_contribution = (
            weights["same_team_opportunity"] * rookie.same_team_opportunity
        )
        contributions: list[dict[str, float | str]] = [
            {
                "feature": "overall_pick",
                "raw_value": float(rookie.overall_pick),
                "normalized_value": round(rookie.draft_position_value, 4),
                "weight": weights["overall_pick"],
                "contribution": round(draft_contribution, 4),
            },
            {
                "feature": "roster_opportunity",
                "raw_value": round(rookie.roster_opportunity, 4),
                "normalized_value": round(rookie.roster_opportunity, 4),
                "weight": weights["roster_opportunity"],
                "contribution": round(roster_contribution, 4),
            },
            {
                "feature": "same_team_opportunity",
                "raw_value": round(rookie.same_team_opportunity, 4),
                "normalized_value": round(rookie.same_team_opportunity, 4),
                "weight": weights["same_team_opportunity"],
                "contribution": round(team_contribution, 4),
            },
        ]
        scored.append(
            (
                rookie,
                draft_contribution + roster_contribution + team_contribution,
                contributions,
            )
        )

    scored.sort(key=lambda row: (-row[1], row[0].overall_pick, row[0].player_name))
    probabilities = _softmax([score for _, score, _ in scored], temperature=0.14)
    ranked = [
        RankedCandidate(
            rank=rank,
            entity_id=rookie.draft_pick_id,
            name=rookie.player_name,
            team=rookie.team_name,
            position=None,
            probability=round(probability, 6),
            score=round(score, 6),
            features={
                "overall_pick": float(rookie.overall_pick),
                "draft_position_value": round(rookie.draft_position_value, 4),
                "roster_opportunity": round(rookie.roster_opportunity, 4),
                "same_team_opportunity": round(rookie.same_team_opportunity, 4),
            },
            feature_attributions=sorted(
                contributions,
                key=lambda item: abs(float(item["contribution"])),
                reverse=True,
            ),
            warnings=[
                "Preseason estimate: the rookie class has no NBA game sample yet.",
                f"Team opportunity uses stored {source_season} rotation data.",
            ],
        )
        for rank, ((rookie, score, contributions), probability) in enumerate(
            zip(scored[:limit], probabilities[:limit], strict=True),
            start=1,
        )
    ]
    return AwardPredictionResult(
        prediction_id=None,
        award_type="ROY",
        target_season=target_season,
        source_season=source_season,
        model_version=ROY_MODEL_VERSION,
        candidates=ranked,
        warnings=[
            "This is a preseason opportunity model; no 2026-27 NBA performance data exists.",
            "College production is not included because it was not supplied with "
            "the draft results.",
        ],
        methodology=(
            "Deterministic preseason ROY estimate: 75% draft position value, 17% "
            "opportunity inferred from the destination team's stored rotation, and 8% "
            "opportunity after accounting for other 2026 picks on that team. Softmax "
            "converts scores across all 60 drafted players to estimates. Probabilities "
            "are not guarantees."
        ),
    )


def _team_roster_opportunity(session: Session, source_season: str) -> dict[int, float]:
    rows = session.execute(
        select(PlayerSeasonSummary, Team)
        .join(Team, PlayerSeasonSummary.team_id == Team.id)
        .where(PlayerSeasonSummary.season == source_season)
    ).all()
    by_team: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for summary, team in rows:
        minutes = float(summary.minutes_per_game or 0)
        points = float(summary.points_per_game or 0)
        by_team[team.id].append((minutes, points))

    competition: dict[int, float] = {}
    for team_id, roster in by_team.items():
        rotation = sorted(roster, key=lambda item: (-item[0], -item[1]))[:8]
        if not rotation:
            competition[team_id] = 0
            continue
        average_minutes = sum(minutes for minutes, _ in rotation) / len(rotation)
        top_scorers = sorted((points for _, points in rotation), reverse=True)[:3]
        average_top_scoring = sum(top_scorers) / len(top_scorers)
        competition[team_id] = 0.55 * (average_minutes / 36) + 0.45 * (
            average_top_scoring / 30
        )
    if not competition:
        return {}
    low = min(competition.values())
    high = max(competition.values())
    spread = high - low
    if spread == 0:
        return {team_id: 0.5 for team_id in competition}
    return {
        team_id: round(1 - ((value - low) / spread), 6)
        for team_id, value in competition.items()
    }


def _same_team_draft_opportunity(
    draft_picks: Sequence[DraftPick],
) -> dict[int, float]:
    by_team: dict[int, list[DraftPick]] = defaultdict(list)
    for pick in draft_picks:
        by_team[pick.team_id].append(pick)
    competition = {
        pick.id: sum(
            1 / sqrt(other.overall_pick)
            for other in by_team[pick.team_id]
            if other.id != pick.id
        )
        for pick in draft_picks
    }
    high = max(competition.values(), default=0)
    if high == 0:
        return {pick.id: 1 for pick in draft_picks}
    return {
        pick_id: round(1 - (value / high), 6)
        for pick_id, value in competition.items()
    }


def _softmax(scores: list[float], temperature: float) -> list[float]:
    maximum = max(scores)
    exponents = [exp((score - maximum) / temperature) for score in scores]
    denominator = sum(exponents)
    return [value / denominator for value in exponents]


def _season_start_year(season: str) -> int:
    try:
        return int(season.split("-", maxsplit=1)[0])
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Invalid season '{season}'. Expected YYYY-YY.") from exc
