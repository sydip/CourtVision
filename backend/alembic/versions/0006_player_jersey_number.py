"""Add jersey number to players.

Revision ID: 0006_player_jersey_number
Revises: 0005_extend_true_shooting_source
Create Date: 2026-07-07 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_player_jersey_number"
down_revision: str | None = "0005_extend_true_shooting_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("players", sa.Column("jersey_number", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("players", "jersey_number")
