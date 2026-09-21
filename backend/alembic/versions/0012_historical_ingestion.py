"""Add team game statistics and sync failure totals.

Revision ID: 0012_historical_ingestion
Revises: 0011_multi_season_foundation
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_historical_ingestion"
down_revision: str | None = "0011_multi_season_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sync_runs", sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_table(
        "team_game_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=7), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("opponent_points", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=1), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "game_id", name="uq_team_game_stats_team_game"),
    )
    op.create_index("ix_team_game_stats_season", "team_game_stats", ["season"])
    op.create_index("ix_team_game_stats_team_id", "team_game_stats", ["team_id"])
    op.create_index("ix_team_game_stats_game_id", "team_game_stats", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_team_game_stats_game_id", table_name="team_game_stats")
    op.drop_index("ix_team_game_stats_team_id", table_name="team_game_stats")
    op.drop_index("ix_team_game_stats_season", table_name="team_game_stats")
    op.drop_table("team_game_stats")
    op.drop_column("sync_runs", "failed_count")
