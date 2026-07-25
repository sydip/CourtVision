"""Add sync run ingestion totals.

Revision ID: 0002_sync_run_totals
Revises: 0001_initial_schema
Create Date: 2026-06-30 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_sync_run_totals"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sync_runs",
        sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sync_runs",
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sync_runs",
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sync_runs",
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("sync_runs", "rejected_count")
    op.drop_column("sync_runs", "updated_count")
    op.drop_column("sync_runs", "inserted_count")
    op.drop_column("sync_runs", "fetched_count")
