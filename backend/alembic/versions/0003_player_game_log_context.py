"""Add normalized player game log context.

Revision ID: 0003_player_game_log_context
Revises: 0002_sync_run_totals
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_player_game_log_context"
down_revision: str | None = "0002_sync_run_totals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("player_game_stats", sa.Column("matchup", sa.String(length=32), nullable=True))
    op.add_column("player_game_stats", sa.Column("is_home", sa.Boolean(), nullable=True))
    op.add_column("player_game_stats", sa.Column("result", sa.String(length=1), nullable=True))
    op.add_column(
        "player_game_stats",
        sa.Column("days_since_previous_game", sa.Integer(), nullable=True),
    )
    op.add_column(
        "player_game_stats",
        sa.Column(
            "personal_fouls",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("player_game_stats", "personal_fouls")
    op.drop_column("player_game_stats", "days_since_previous_game")
    op.drop_column("player_game_stats", "result")
    op.drop_column("player_game_stats", "is_home")
    op.drop_column("player_game_stats", "matchup")
