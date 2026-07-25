"""Extend true shooting source label length.

Revision ID: 0005_extend_true_shooting_source
Revises: 0004_analytics_summary_fields
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_extend_true_shooting_source"
down_revision: str | None = "0004_analytics_summary_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("player_season_summaries") as batch_op:
        batch_op.alter_column(
            "true_shooting_source",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("player_season_summaries") as batch_op:
        batch_op.alter_column(
            "true_shooting_source",
            existing_type=sa.String(length=64),
            type_=sa.String(length=32),
            existing_nullable=True,
        )
