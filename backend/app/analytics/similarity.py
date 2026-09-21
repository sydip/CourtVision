"""Statistical player-similarity engine.

Similarity is computed from a fixed per-role feature vector that is standardized
across the eligible player population (``StandardScaler``) and compared with
cosine similarity. The result describes *statistical* resemblance -- how alike
two players' production profiles are -- and deliberately says nothing about
identical play style.

The module is intentionally free of any ORM or FastAPI dependency so it can be
unit tested deterministically. Callers extract raw stats from storage, build
:class:`PlayerFeatureRow` values via :func:`compute_feature_values`, and hand the
rows to :func:`rank_similar_players`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from app.analytics.per36 import calculate_per_36


@dataclass(frozen=True)
class SimilarityFeature:
    """One dimension of the similarity feature vector."""

    key: str
    label: str
    unit: str  # "per36" | "percent" | "minutes"
    higher_is_better: bool = True
    optional: bool = False  # only used when present for the selected player


# Feature vector, in a fixed order so scaling and cosine math are deterministic.
SIMILARITY_FEATURES: tuple[SimilarityFeature, ...] = (
    SimilarityFeature("points_per_36", "Points / 36", "per36"),
    SimilarityFeature("rebounds_per_36", "Rebounds / 36", "per36"),
    SimilarityFeature("assists_per_36", "Assists / 36", "per36"),
    SimilarityFeature("steals_per_36", "Steals / 36", "per36"),
    SimilarityFeature("blocks_per_36", "Blocks / 36", "per36"),
    SimilarityFeature("turnovers_per_36", "Turnovers / 36", "per36", higher_is_better=False),
    SimilarityFeature("true_shooting_percentage", "True shooting %", "percent"),
    SimilarityFeature("usage_rate", "Usage %", "percent", optional=True),
    SimilarityFeature("minutes_per_game", "Minutes / game", "minutes"),
)

# A feature is a "shared strength" only when both players sit at least this many
# standard deviations on the favourable side of the league mean.
STRENGTH_Z_THRESHOLD = 0.5
# Neutral score returned when a profile is exactly league-average on every active
# feature (a zero vector, for which cosine similarity is undefined).
NEUTRAL_SCORE = 50.0
MAX_INSIGHTS = 3


@dataclass(frozen=True)
class PlayerFeatureRow:
    """A single player's eligibility metadata plus raw feature values."""

    player_id: int
    games_played: int
    minutes_per_game: float | None
    position: str | None
    values: dict[str, float | None]


@dataclass(frozen=True)
class FeatureComparison:
    """The selected player's and a candidate's value for one feature."""

    feature: str
    label: str
    unit: str
    player_value: float | None
    candidate_value: float | None
    difference: float | None


@dataclass(frozen=True)
class SimilarityResult:
    player_id: int
    similarity_score: float
    shared_strengths: list[str]
    largest_differences: list[str]
    feature_comparisons: list[FeatureComparison]


def compute_feature_values(
    *,
    minutes_per_game: float | None,
    points_per_36: float | None,
    rebounds_per_36: float | None,
    assists_per_36: float | None,
    turnovers_per_36: float | None,
    steals_per_game: float | None,
    blocks_per_game: float | None,
    true_shooting_percentage: float | None,
    usage_rate: float | None,
) -> dict[str, float | None]:
    """Assemble the raw feature-vector dict for a single player.

    Steals and blocks are stored per game, so they are converted to a per-36
    basis here (``per_game / minutes_per_game * 36``); every other feature is
    already stored in the target unit. Missing inputs stay ``None`` so callers
    can handle them explicitly.
    """

    return {
        "points_per_36": points_per_36,
        "rebounds_per_36": rebounds_per_36,
        "assists_per_36": assists_per_36,
        "steals_per_36": calculate_per_36(steals_per_game, minutes_per_game),
        "blocks_per_36": calculate_per_36(blocks_per_game, minutes_per_game),
        "turnovers_per_36": turnovers_per_36,
        "true_shooting_percentage": true_shooting_percentage,
        "usage_rate": usage_rate,
        "minutes_per_game": minutes_per_game,
    }


def is_eligible(
    row: PlayerFeatureRow,
    *,
    minimum_games: int,
    minimum_minutes_per_game: float,
) -> bool:
    """A player qualifies only with enough games and a real minutes load."""

    if row.games_played < minimum_games:
        return False
    if row.minutes_per_game is None or row.minutes_per_game < minimum_minutes_per_game:
        return False
    return True


def rank_similar_players(
    target: PlayerFeatureRow,
    candidates: Sequence[PlayerFeatureRow],
    *,
    minimum_games: int,
    minimum_minutes_per_game: float,
    same_position_only: bool = False,
    limit: int = 5,
) -> list[SimilarityResult]:
    """Rank candidates by statistical similarity to ``target``.

    The selected player is always excluded from the results. Candidates below
    the game/minute thresholds are dropped before scaling. Features are
    standardized across the selected player plus the eligible candidates, then
    scored with cosine similarity mapped onto a 0-100 scale.
    """

    eligible = [
        row
        for row in candidates
        if row.player_id != target.player_id
        and is_eligible(
            row,
            minimum_games=minimum_games,
            minimum_minutes_per_game=minimum_minutes_per_game,
        )
    ]
    if not eligible:
        return []

    # Deterministic population order: selected player first, then candidates by id.
    population = [target, *sorted(eligible, key=lambda row: row.player_id)]
    active = _active_features(target, population)
    if not active:
        return []

    scaled = _standardize(population, active)
    target_scaled = scaled[0]
    target_position = (target.position or "").casefold()

    scored: list[tuple[float, PlayerFeatureRow, list[float]]] = []
    for index, row in enumerate(population[1:], start=1):
        if same_position_only:
            if not target_position or (row.position or "").casefold() != target_position:
                continue
        raw_score = _cosine_score(target_scaled, scaled[index])
        scored.append((raw_score, row, scaled[index]))

    # Stable ordering: best score first, ties broken by player id.
    scored.sort(key=lambda item: (-item[0], item[1].player_id))

    results: list[SimilarityResult] = []
    for raw_score, row, row_scaled in scored[:limit]:
        results.append(
            SimilarityResult(
                player_id=row.player_id,
                similarity_score=round(raw_score, 1),
                shared_strengths=_shared_strengths(active, target_scaled, row_scaled),
                largest_differences=_largest_differences(active, target_scaled, row_scaled),
                feature_comparisons=_feature_comparisons(active, target, row),
            )
        )
    return results


def _active_features(
    target: PlayerFeatureRow,
    population: Sequence[PlayerFeatureRow],
) -> list[SimilarityFeature]:
    """Features usable for this comparison.

    Optional features (usage rate) are only used when the selected player has a
    value, and any feature with no data across the whole population is dropped so
    standardization never operates on an empty column.
    """

    active: list[SimilarityFeature] = []
    for feature in SIMILARITY_FEATURES:
        if feature.optional and target.values.get(feature.key) is None:
            continue
        if not any(row.values.get(feature.key) is not None for row in population):
            continue
        active.append(feature)
    return active


def _standardize(
    population: Sequence[PlayerFeatureRow],
    active: Sequence[SimilarityFeature],
) -> list[list[float]]:
    """Build the imputed feature matrix and standardize each column.

    Missing values are imputed with the column mean over present values, which
    maps to 0 after standardization (a neutral, league-average stand-in).
    """

    column_means: dict[str, float] = {}
    for feature in active:
        present = [
            value
            for row in population
            if (value := row.values.get(feature.key)) is not None
        ]
        column_means[feature.key] = sum(present) / len(present) if present else 0.0

    matrix = [
        [
            value if (value := row.values.get(feature.key)) is not None
            else column_means[feature.key]
            for feature in active
        ]
        for row in population
    ]
    scaled = StandardScaler().fit_transform(matrix)
    return [[float(value) for value in row] for row in scaled]


def _cosine_score(target_scaled: list[float], candidate_scaled: list[float]) -> float:
    """Map cosine similarity of two standardized vectors onto 0-100."""

    if not any(target_scaled) or not any(candidate_scaled):
        return NEUTRAL_SCORE
    cosine = float(cosine_similarity([target_scaled], [candidate_scaled])[0][0])
    cosine = max(-1.0, min(1.0, cosine))
    return (cosine + 1.0) / 2.0 * 100.0


def _shared_strengths(
    active: Sequence[SimilarityFeature],
    target_scaled: list[float],
    candidate_scaled: list[float],
) -> list[str]:
    """Features where both players rate clearly above the league mean."""

    ranked: list[tuple[float, str]] = []
    for index, feature in enumerate(active):
        target_edge = float(target_scaled[index])
        candidate_edge = float(candidate_scaled[index])
        if not feature.higher_is_better:
            target_edge, candidate_edge = -target_edge, -candidate_edge
        if target_edge >= STRENGTH_Z_THRESHOLD and candidate_edge >= STRENGTH_Z_THRESHOLD:
            ranked.append((min(target_edge, candidate_edge), feature.label))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [label for _, label in ranked[:MAX_INSIGHTS]]


def _largest_differences(
    active: Sequence[SimilarityFeature],
    target_scaled: list[float],
    candidate_scaled: list[float],
) -> list[str]:
    """Features where the two standardized profiles diverge the most."""

    gaps = [
        (abs(float(target_scaled[index]) - float(candidate_scaled[index])), feature.label)
        for index, feature in enumerate(active)
    ]
    gaps.sort(key=lambda item: (-item[0], item[1]))
    return [label for _, label in gaps[:MAX_INSIGHTS]]


def _feature_comparisons(
    active: Sequence[SimilarityFeature],
    target: PlayerFeatureRow,
    candidate: PlayerFeatureRow,
) -> list[FeatureComparison]:
    comparisons: list[FeatureComparison] = []
    for feature in active:
        player_value = target.values.get(feature.key)
        candidate_value = candidate.values.get(feature.key)
        difference = (
            candidate_value - player_value
            if player_value is not None and candidate_value is not None
            else None
        )
        comparisons.append(
            FeatureComparison(
                feature=feature.key,
                label=feature.label,
                unit=feature.unit,
                player_value=_round(player_value),
                candidate_value=_round(candidate_value),
                difference=_round(difference),
            )
        )
    return comparisons


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)
