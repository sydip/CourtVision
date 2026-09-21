from __future__ import annotations

import dataclasses
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.similarity import (
    PlayerFeatureRow,
    compute_feature_values,
    is_eligible,
    rank_similar_players,
)
from app.db.session import get_db_session
from app.main import create_app
from app.models import Player, PlayerSeasonSummary, Team

# ---------------------------------------------------------------------------
# Pure-engine unit tests (deterministic, no database)
# ---------------------------------------------------------------------------


def _row(
    player_id: int,
    *,
    position: str,
    games_played: int = 60,
    minutes_per_game: float = 32.0,
    points_per_36: float = 20.0,
    rebounds_per_36: float = 5.0,
    assists_per_36: float = 5.0,
    steals_per_game: float | None = 1.2,
    blocks_per_game: float | None = 0.5,
    turnovers_per_36: float = 2.0,
    true_shooting_percentage: float | None = 0.58,
    usage_rate: float | None = 0.25,
) -> PlayerFeatureRow:
    return PlayerFeatureRow(
        player_id=player_id,
        games_played=games_played,
        minutes_per_game=minutes_per_game,
        position=position,
        values=compute_feature_values(
            minutes_per_game=minutes_per_game,
            points_per_36=points_per_36,
            rebounds_per_36=rebounds_per_36,
            assists_per_36=assists_per_36,
            turnovers_per_36=turnovers_per_36,
            steals_per_game=steals_per_game,
            blocks_per_game=blocks_per_game,
            true_shooting_percentage=true_shooting_percentage,
            usage_rate=usage_rate,
        ),
    )


def _pool() -> tuple[PlayerFeatureRow, list[PlayerFeatureRow]]:
    target = _row(1, position="G", points_per_36=30, assists_per_36=8, usage_rate=0.31)
    candidates = [
        # Near-clone of the target guard.
        _row(2, position="G", points_per_36=29, assists_per_36=7.6, usage_rate=0.30),
        # Rim-protecting big with an opposite profile.
        _row(
            3,
            position="C",
            points_per_36=18,
            rebounds_per_36=12,
            assists_per_36=1.5,
            blocks_per_game=2.4,
            usage_rate=0.19,
        ),
        # Low-usage role guard.
        _row(4, position="G", points_per_36=11, assists_per_36=2, usage_rate=0.14),
    ]
    return target, candidates


def test_per_36_derivation_and_missing_values() -> None:
    values = compute_feature_values(
        minutes_per_game=30.0,
        points_per_36=None,
        rebounds_per_36=None,
        assists_per_36=None,
        turnovers_per_36=None,
        steals_per_game=1.5,
        blocks_per_game=None,
        true_shooting_percentage=None,
        usage_rate=None,
    )
    # 1.5 steals across 30 minutes projects to 1.8 per 36.
    assert values["steals_per_36"] == 1.8
    # Missing inputs stay explicitly None rather than defaulting to zero.
    assert values["blocks_per_36"] is None
    assert values["usage_rate"] is None


def test_eligibility_thresholds() -> None:
    playable = _row(1, position="G", games_played=20, minutes_per_game=28.0)
    too_few_games = _row(2, position="G", games_played=5, minutes_per_game=28.0)
    too_few_minutes = _row(3, position="G", games_played=40, minutes_per_game=6.0)

    assert is_eligible(playable, minimum_games=15, minimum_minutes_per_game=10.0)
    assert not is_eligible(too_few_games, minimum_games=15, minimum_minutes_per_game=10.0)
    assert not is_eligible(too_few_minutes, minimum_games=15, minimum_minutes_per_game=10.0)


def test_ranks_closer_profiles_higher_and_excludes_ineligible() -> None:
    target, candidates = _pool()
    candidates.append(_row(9, position="G", games_played=4, minutes_per_game=25.0))

    results = rank_similar_players(
        target,
        candidates,
        minimum_games=15,
        minimum_minutes_per_game=10.0,
        limit=5,
    )

    ranked_ids = [result.player_id for result in results]
    assert ranked_ids[0] == 2  # near-clone guard ranks first
    assert 9 not in ranked_ids  # 4-game player is ineligible
    assert results[0].similarity_score > results[-1].similarity_score
    assert all(0 <= result.similarity_score <= 100 for result in results)


def test_selected_player_never_appears_in_results() -> None:
    target, candidates = _pool()
    # Even if the target is (incorrectly) present in the candidate list, it is dropped.
    results = rank_similar_players(
        target,
        [*candidates, target],
        minimum_games=15,
        minimum_minutes_per_game=10.0,
        limit=10,
    )
    assert all(result.player_id != target.player_id for result in results)


def test_same_position_only_filter() -> None:
    target, candidates = _pool()
    results = rank_similar_players(
        target,
        candidates,
        minimum_games=15,
        minimum_minutes_per_game=10.0,
        same_position_only=True,
        limit=10,
    )
    assert {result.player_id for result in results} == {2, 4}  # only guards, not the center


def test_results_are_stable_for_the_same_dataset() -> None:
    target, candidates = _pool()
    kwargs = {"minimum_games": 15, "minimum_minutes_per_game": 10.0, "limit": 5}
    first = rank_similar_players(target, candidates, **kwargs)
    second = rank_similar_players(target, candidates, **kwargs)
    assert [(r.player_id, r.similarity_score) for r in first] == [
        (r.player_id, r.similarity_score) for r in second
    ]


def test_missing_usage_is_handled_without_dropping_the_candidate() -> None:
    target, candidates = _pool()
    without_usage = dict(candidates[0].values)
    without_usage["usage_rate"] = None
    candidates[0] = dataclasses.replace(candidates[0], values=without_usage)

    results = rank_similar_players(
        target,
        candidates,
        minimum_games=15,
        minimum_minutes_per_game=10.0,
        limit=5,
    )
    match = next(result for result in results if result.player_id == 2)
    usage = next(c for c in match.feature_comparisons if c.feature == "usage_rate")
    assert usage.candidate_value is None  # explicitly reported as missing
    assert usage.player_value is not None


def test_feature_comparisons_and_insights_are_explanatory() -> None:
    target, candidates = _pool()
    results = rank_similar_players(
        target,
        candidates,
        minimum_games=15,
        minimum_minutes_per_game=10.0,
        limit=5,
    )
    clone = next(result for result in results if result.player_id == 2)
    center = next(result for result in results if result.player_id == 3)

    compared_features = {comparison.feature for comparison in clone.feature_comparisons}
    assert "points_per_36" in compared_features
    assert "true_shooting_percentage" in compared_features
    # The near-clone shares scoring/playmaking strengths with the target guard.
    assert clone.shared_strengths
    # The opposite-profile big is defined by its differences, not shared strengths.
    assert center.largest_differences


# ---------------------------------------------------------------------------
# API tests (endpoint wiring, thresholds, self-exclusion)
# ---------------------------------------------------------------------------


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_db_session() -> object:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)


def _summary(
    player: Player,
    team: Team,
    *,
    games_played: int,
    minutes_per_game: str,
    points_per_36: str,
    rebounds_per_36: str,
    assists_per_36: str,
    usage_rate: str | None = "0.250",
) -> PlayerSeasonSummary:
    return PlayerSeasonSummary(
        player=player,
        team=team,
        season="2025-26",
        games_played=games_played,
        minutes_per_game=Decimal(minutes_per_game),
        points_per_game=Decimal("20.00"),
        rebounds_per_game=Decimal("5.00"),
        assists_per_game=Decimal("4.00"),
        turnovers_per_game=Decimal("2.00"),
        steals_per_game=Decimal("1.20"),
        blocks_per_game=Decimal("0.40"),
        true_shooting_percentage=Decimal("0.590"),
        usage_rate=Decimal(usage_rate) if usage_rate is not None else None,
        points_per_36=Decimal(points_per_36),
        rebounds_per_36=Decimal(rebounds_per_36),
        assists_per_36=Decimal(assists_per_36),
        turnovers_per_36=Decimal("2.20"),
    )


def _seed_similarity_pool(db_session: Session) -> None:
    warriors = Team(
        nba_team_id=1610612744,
        abbreviation="GSW",
        city="Golden State",
        name="Warriors",
        conference="West",
        division="Pacific",
    )
    lakers = Team(
        nba_team_id=1610612747,
        abbreviation="LAL",
        city="Los Angeles",
        name="Lakers",
        conference="West",
        division="Pacific",
    )
    nuggets = Team(
        nba_team_id=1610612743,
        abbreviation="DEN",
        city="Denver",
        name="Nuggets",
        conference="West",
        division="Northwest",
    )

    curry = Player(
        nba_player_id=201939, slug="stephen-curry", full_name="Stephen Curry", position="G"
    )
    clone = Player(
        nba_player_id=1630000, slug="clone-guard", full_name="Clone Guard", position="G"
    )
    jokic = Player(
        nba_player_id=203999, slug="nikola-jokic", full_name="Nikola Jokic", position="C"
    )
    bench = Player(
        nba_player_id=1620000, slug="bench-guard", full_name="Bench Guard", position="G"
    )

    db_session.add_all(
        [
            warriors,
            lakers,
            nuggets,
            curry,
            clone,
            jokic,
            bench,
            # Selected player: high-usage scoring guard.
            _summary(
                curry,
                warriors,
                games_played=40,
                minutes_per_game="34.00",
                points_per_36="30.00",
                rebounds_per_36="5.00",
                assists_per_36="8.00",
                usage_rate="0.310",
            ),
            # Statistical near-clone.
            _summary(
                clone,
                lakers,
                games_played=40,
                minutes_per_game="33.00",
                points_per_36="29.00",
                rebounds_per_36="4.80",
                assists_per_36="7.60",
                usage_rate="0.300",
            ),
            # Opposite-profile big.
            _summary(
                jokic,
                nuggets,
                games_played=40,
                minutes_per_game="33.00",
                points_per_36="18.00",
                rebounds_per_36="13.00",
                assists_per_36="2.00",
                usage_rate="0.190",
            ),
            # Ineligible: only 3 games played.
            _summary(
                bench,
                lakers,
                games_played=3,
                minutes_per_game="30.00",
                points_per_36="28.00",
                rebounds_per_36="4.90",
                assists_per_36="7.80",
                usage_rate="0.290",
            ),
        ]
    )
    db_session.commit()


def test_similar_endpoint_returns_ranked_statistical_matches(db_session: Session) -> None:
    _seed_similarity_pool(db_session)
    client = _client(db_session)

    response = client.get("/api/players/201939/seasons/2025-26/similar", params={"limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["player_id"] == 1
    ids = [entry["player"]["full_name"] for entry in body["players"]]

    # Selected player is excluded; ineligible bench guard is excluded.
    assert "Stephen Curry" not in ids
    assert "Bench Guard" not in ids
    # Near-clone ranks ahead of the opposite-profile center.
    assert ids[0] == "Clone Guard"

    top = body["players"][0]
    assert 0 <= top["similarity_score"] <= 100
    assert top["shared_strengths"]
    assert top["largest_differences"]
    feature_keys = {comparison["feature"] for comparison in top["feature_comparisons"]}
    assert {"points_per_36", "true_shooting_percentage", "minutes_per_game"} <= feature_keys


def test_similar_endpoint_supports_same_position_filter(db_session: Session) -> None:
    _seed_similarity_pool(db_session)
    client = _client(db_session)

    response = client.get(
        "/api/players/201939/seasons/2025-26/similar",
        params={"same_position_only": "true"},
    )

    assert response.status_code == 200
    names = {entry["player"]["full_name"] for entry in response.json()["players"]}
    assert "Nikola Jokic" not in names  # center filtered out
    assert "Clone Guard" in names


def test_similar_endpoint_is_stable_across_calls(db_session: Session) -> None:
    _seed_similarity_pool(db_session)
    client = _client(db_session)

    first = client.get("/api/players/201939/seasons/2025-26/similar").json()
    second = client.get("/api/players/201939/seasons/2025-26/similar").json()

    def signature(body: dict[str, object]) -> list[tuple[str, float]]:
        return [
            (entry["player"]["full_name"], entry["similarity_score"])
            for entry in body["players"]  # type: ignore[attr-defined]
        ]

    assert signature(first) == signature(second)
