"""Persist deterministic multi-season analytics outputs.

Revision ID: 0013_multi_season_analytics
Revises: 0012_historical_ingestion
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_multi_season_analytics"
down_revision: str | None = "0012_historical_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("player_season_summaries", sa.Column("steals_per_game", sa.Numeric(5, 2)))
    op.add_column("player_season_summaries", sa.Column("blocks_per_game", sa.Numeric(5, 2)))
    op.add_column(
        "player_season_summaries",
        sa.Column("effective_field_goal_percentage", sa.Numeric(6, 3)),
    )
    for name in ("totals", "rolling_averages", "split_payload", "similarity_vector"):
        op.add_column("player_season_summaries", sa.Column(name, sa.JSON()))
    op.add_column("team_season_stats", sa.Column("leaders", sa.JSON()))


def downgrade() -> None:
    op.drop_column("team_season_stats", "leaders")
    for name in ("similarity_vector", "split_payload", "rolling_averages", "totals"):
        op.drop_column("player_season_summaries", name)
    op.drop_column("player_season_summaries", "effective_field_goal_percentage")
    op.drop_column("player_season_summaries", "blocks_per_game")
    op.drop_column("player_season_summaries", "steals_per_game")
