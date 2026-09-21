"""Add canonical seasons, standings, rosters, and normalized predictions.

Revision ID: 0011_multi_season_foundation
Revises: 0010_playoff_box_scores
Create Date: 2026-08-03 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_multi_season_foundation"
down_revision: str | None = "0010_playoff_box_scores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    seasons = op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=7), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=32), nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("supports_predictions", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "supports_jordan_predictions", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "length(slug) = 7 AND substr(slug, 5, 1) = '-'", name="ck_seasons_slug_format"
        ),
        sa.CheckConstraint("end_year = start_year + 1", name="ck_seasons_year_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_seasons_slug"),
        sa.UniqueConstraint("start_year", name="uq_seasons_start_year"),
    )
    op.bulk_insert(
        seasons,
        [
            _season(2021, completed=True),
            _season(2022, completed=True),
            _season(2023, completed=True),
            _season(2024, completed=True),
            _season(2025, current=True, jordan=True),
            _season(2026, predictions=True),
        ],
    )

    for _name, column in (
        ("conference", sa.Column("conference", sa.String(length=24), nullable=True)),
        ("division", sa.Column("division", sa.String(length=48), nullable=True)),
        ("win_pct", sa.Column("win_pct", sa.Numeric(precision=6, scale=3), nullable=True)),
        (
            "points_per_game",
            sa.Column("points_per_game", sa.Numeric(precision=6, scale=2), nullable=True),
        ),
        (
            "points_allowed_per_game",
            sa.Column("points_allowed_per_game", sa.Numeric(precision=6, scale=2), nullable=True),
        ),
    ):
        op.add_column("team_season_stats", column)

    op.create_table(
        "standings_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=7), nullable=False),
        sa.Column("snapshot_type", sa.String(length=32), nullable=False),
        sa.Column("conference", sa.String(length=24), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("win_pct", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("games_back", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("conference_record", sa.String(length=16), nullable=True),
        sa.Column("division_record", sa.String(length=16), nullable=True),
        sa.Column("home_record", sa.String(length=16), nullable=True),
        sa.Column("away_record", sa.String(length=16), nullable=True),
        sa.Column("last_10", sa.String(length=16), nullable=True),
        sa.Column("streak", sa.String(length=16), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(_season_check(), name="ck_standings_snapshots_season_format"),
        sa.CheckConstraint(
            "snapshot_type IN ('final_regular_season', 'current', 'projected')",
            name="ck_standings_snapshots_type",
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "season", "snapshot_type", "team_id", name="uq_standings_snapshot_season_type_team"
        ),
    )
    op.create_index("ix_standings_snapshots_season", "standings_snapshots", ["season"])
    op.create_index("ix_standings_snapshots_team_id", "standings_snapshots", ["team_id"])

    op.create_table(
        "roster_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=7), nullable=False),
        sa.Column("jersey_number", sa.String(length=8), nullable=True),
        sa.Column("position", sa.String(length=32), nullable=True),
        sa.Column("roster_status", sa.String(length=24), nullable=False),
        sa.Column("is_projected_starter", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("depth_order", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(_season_check(), name="ck_roster_memberships_season_format"),
        sa.CheckConstraint(
            "roster_status IN ('active', 'inactive', 'two_way', 'waived', 'traded', 'free_agent')",
            name="ck_roster_memberships_status",
        ),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id",
            "team_id",
            "season",
            "start_date",
            name="uq_roster_memberships_player_team_season_start",
        ),
    )
    op.create_index("ix_roster_memberships_player_id", "roster_memberships", ["player_id"])
    op.create_index("ix_roster_memberships_team_id", "roster_memberships", ["team_id"])
    op.create_index("ix_roster_memberships_season", "roster_memberships", ["season"])

    op.create_table(
        "prediction_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=7), nullable=False),
        sa.Column("prediction_type", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("training_seasons", sa.JSON(), nullable=False),
        sa.Column("feature_set_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(_season_check(), name="ck_prediction_runs_season_format"),
        sa.CheckConstraint(
            "prediction_type IN ('all_nba', 'standings', 'finals_winner')",
            name="ck_prediction_runs_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_prediction_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_runs_season", "prediction_runs", ["season"])
    op.create_index("ix_prediction_runs_type", "prediction_runs", ["prediction_type"])

    op.create_table(
        "prediction_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_run_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=7), nullable=False),
        sa.Column("prediction_type", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=16), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("predicted_rank", sa.Integer(), nullable=True),
        sa.Column("predicted_label", sa.String(length=120), nullable=True),
        sa.Column("probability", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("score", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("explanation_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(_season_check(), name="ck_prediction_results_season_format"),
        sa.CheckConstraint(
            "entity_type IN ('player', 'team')", name="ck_prediction_results_entity_type"
        ),
        sa.ForeignKeyConstraint(["prediction_run_id"], ["prediction_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_results_run_id", "prediction_results", ["prediction_run_id"])
    op.create_index("ix_prediction_results_season", "prediction_results", ["season"])


def downgrade() -> None:
    op.drop_index("ix_prediction_results_season", table_name="prediction_results")
    op.drop_index("ix_prediction_results_run_id", table_name="prediction_results")
    op.drop_table("prediction_results")
    op.drop_index("ix_prediction_runs_type", table_name="prediction_runs")
    op.drop_index("ix_prediction_runs_season", table_name="prediction_runs")
    op.drop_table("prediction_runs")
    op.drop_index("ix_roster_memberships_season", table_name="roster_memberships")
    op.drop_index("ix_roster_memberships_team_id", table_name="roster_memberships")
    op.drop_index("ix_roster_memberships_player_id", table_name="roster_memberships")
    op.drop_table("roster_memberships")
    op.drop_index("ix_standings_snapshots_team_id", table_name="standings_snapshots")
    op.drop_index("ix_standings_snapshots_season", table_name="standings_snapshots")
    op.drop_table("standings_snapshots")
    for column in (
        "points_allowed_per_game",
        "points_per_game",
        "win_pct",
        "division",
        "conference",
    ):
        op.drop_column("team_season_stats", column)
    op.drop_table("seasons")


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def _season(
    start_year: int,
    *,
    completed: bool = False,
    current: bool = False,
    predictions: bool = False,
    jordan: bool = False,
) -> dict[str, object]:
    end_year = start_year + 1
    slug = f"{start_year}-{str(end_year)[-2:]}"
    return {
        "slug": slug,
        "start_year": start_year,
        "end_year": end_year,
        "display_name": f"{start_year}\u2013{str(end_year)[-2:]} Season",
        "is_completed": completed,
        "is_current": current,
        "supports_predictions": predictions,
        "supports_jordan_predictions": jordan,
    }


def _season_check() -> str:
    return "length(season) = 7 AND substr(season, 5, 1) = '-'"
