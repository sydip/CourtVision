"""Add analytics fields to season summaries.

Revision ID: 0004_analytics_summary_fields
Revises: 0003_player_game_log_context
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_analytics_summary_fields"
down_revision: str | None = "0003_player_game_log_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "player_season_summaries",
        sa.Column("turnovers_per_game", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("plus_minus_per_game", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("true_shooting_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("points_per_36", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("rebounds_per_36", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("assists_per_36", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("turnovers_per_36", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column("player_season_summaries", sa.Column("league_percentiles", sa.JSON()))
    op.add_column("player_season_summaries", sa.Column("position_percentiles", sa.JSON()))
    op.add_column("player_season_summaries", sa.Column("minutes_tier_percentiles", sa.JSON()))
    op.add_column(
        "player_season_summaries",
        sa.Column("production_trend", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("production_trend_value", sa.Numeric(8, 4), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("efficiency_trend", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("efficiency_trend_value", sa.Numeric(8, 4), nullable=True),
    )
    op.add_column("player_season_summaries", sa.Column("trend_payload", sa.JSON()))
    op.add_column("player_season_summaries", sa.Column("analytics_warnings", sa.JSON()))
    op.add_column(
        "player_season_summaries",
        sa.Column("analytics_rebuilt_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("player_season_summaries", "analytics_rebuilt_at")
    op.drop_column("player_season_summaries", "analytics_warnings")
    op.drop_column("player_season_summaries", "trend_payload")
    op.drop_column("player_season_summaries", "efficiency_trend_value")
    op.drop_column("player_season_summaries", "efficiency_trend")
    op.drop_column("player_season_summaries", "production_trend_value")
    op.drop_column("player_season_summaries", "production_trend")
    op.drop_column("player_season_summaries", "minutes_tier_percentiles")
    op.drop_column("player_season_summaries", "position_percentiles")
    op.drop_column("player_season_summaries", "league_percentiles")
    op.drop_column("player_season_summaries", "turnovers_per_36")
    op.drop_column("player_season_summaries", "assists_per_36")
    op.drop_column("player_season_summaries", "rebounds_per_36")
    op.drop_column("player_season_summaries", "points_per_36")
    op.drop_column("player_season_summaries", "true_shooting_source")
    op.drop_column("player_season_summaries", "plus_minus_per_game")
    op.drop_column("player_season_summaries", "turnovers_per_game")
