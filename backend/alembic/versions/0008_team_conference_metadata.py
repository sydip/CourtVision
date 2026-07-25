"""Populate canonical team conference and division metadata.

Revision ID: 0008_team_conference_metadata
Revises: 0007_intelligence_assistant
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_team_conference_metadata"
down_revision: str | None = "0007_intelligence_assistant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEAM_METADATA = {
    "ATL": ("East", "Southeast"),
    "BOS": ("East", "Atlantic"),
    "BKN": ("East", "Atlantic"),
    "CHA": ("East", "Southeast"),
    "CHI": ("East", "Central"),
    "CLE": ("East", "Central"),
    "DAL": ("West", "Southwest"),
    "DEN": ("West", "Northwest"),
    "DET": ("East", "Central"),
    "GSW": ("West", "Pacific"),
    "HOU": ("West", "Southwest"),
    "IND": ("East", "Central"),
    "LAC": ("West", "Pacific"),
    "LAL": ("West", "Pacific"),
    "MEM": ("West", "Southwest"),
    "MIA": ("East", "Southeast"),
    "MIL": ("East", "Central"),
    "MIN": ("West", "Northwest"),
    "NOP": ("West", "Southwest"),
    "NYK": ("East", "Atlantic"),
    "OKC": ("West", "Northwest"),
    "ORL": ("East", "Southeast"),
    "PHI": ("East", "Atlantic"),
    "PHX": ("West", "Pacific"),
    "POR": ("West", "Northwest"),
    "SAC": ("West", "Pacific"),
    "SAS": ("West", "Southwest"),
    "TOR": ("East", "Atlantic"),
    "UTA": ("West", "Northwest"),
    "WAS": ("East", "Southeast"),
}


def upgrade() -> None:
    connection = op.get_bind()
    for abbreviation, (conference, division) in TEAM_METADATA.items():
        connection.execute(
            sa.text(
                """
                UPDATE teams
                SET conference = COALESCE(NULLIF(conference, ''), :conference),
                    division = COALESCE(NULLIF(division, ''), :division)
                WHERE abbreviation = :abbreviation
                """
            ),
            {
                "abbreviation": abbreviation,
                "conference": conference,
                "division": division,
            },
        )


def downgrade() -> None:
    # Existing team metadata is valid independent of this migration revision.
    pass
