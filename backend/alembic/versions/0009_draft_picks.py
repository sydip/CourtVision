"""Add persisted NBA draft results.

Revision ID: 0009_draft_picks
Revises: 0008_team_conference_metadata
Create Date: 2026-07-25 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_draft_picks"
down_revision: str | None = "0008_team_conference_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "draft_picks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_year", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("overall_pick", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("school_country", sa.String(length=160), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("transaction_note", sa.Text(), nullable=True),
        sa.Column("data_source", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_draft_picks_team_id_teams",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "draft_year",
            "overall_pick",
            name="uq_draft_picks_year_overall_pick",
        ),
    )
    op.create_index("ix_draft_picks_draft_year", "draft_picks", ["draft_year"])
    op.create_index("ix_draft_picks_round", "draft_picks", ["round"])
    op.create_index("ix_draft_picks_team_id", "draft_picks", ["team_id"])
    op.create_index("ix_draft_picks_player_name", "draft_picks", ["player_name"])


def downgrade() -> None:
    op.drop_index("ix_draft_picks_player_name", table_name="draft_picks")
    op.drop_index("ix_draft_picks_team_id", table_name="draft_picks")
    op.drop_index("ix_draft_picks_round", table_name="draft_picks")
    op.drop_index("ix_draft_picks_draft_year", table_name="draft_picks")
    op.drop_table("draft_picks")
