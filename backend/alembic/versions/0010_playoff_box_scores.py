"""Add persisted playoff series and box scores.

Revision ID: 0010_playoff_box_scores
Revises: 0009_draft_picks
Create Date: 2026-07-25 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_playoff_box_scores"
down_revision: str | None = "0009_draft_picks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "playoff_series",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("round_name", sa.String(length=48), nullable=False),
        sa.Column("conference", sa.String(length=16), nullable=False),
        sa.Column("winner_team_id", sa.Integer(), nullable=False),
        sa.Column("loser_team_id", sa.Integer(), nullable=False),
        sa.Column("winner_wins", sa.Integer(), nullable=False),
        sa.Column("loser_wins", sa.Integer(), nullable=False),
        sa.Column("data_source", sa.String(length=120), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["winner_team_id"], ["teams.id"],
            name="fk_playoff_series_winner_team_id_teams", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["loser_team_id"], ["teams.id"],
            name="fk_playoff_series_loser_team_id_teams", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "season", "round_name", "winner_team_id", "loser_team_id",
            name="uq_playoff_series_season_round_teams",
        ),
    )
    op.create_index("ix_playoff_series_season_round", "playoff_series", ["season", "round_name"])
    op.create_index("ix_playoff_series_winner_team_id", "playoff_series", ["winner_team_id"])
    op.create_index("ix_playoff_series_loser_team_id", "playoff_series", ["loser_team_id"])

    op.create_table(
        "playoff_games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("game_number", sa.Integer(), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("overtime", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("data_note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["series_id"], ["playoff_series.id"],
            name="fk_playoff_games_series_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"], ["teams.id"],
            name="fk_playoff_games_home_team_id_teams", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["away_team_id"], ["teams.id"],
            name="fk_playoff_games_away_team_id_teams", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "game_number", name="uq_playoff_games_series_game"),
    )
    op.create_index("ix_playoff_games_series_id", "playoff_games", ["series_id"])
    op.create_index("ix_playoff_games_home_team_id", "playoff_games", ["home_team_id"])
    op.create_index("ix_playoff_games_away_team_id", "playoff_games", ["away_team_id"])

    op.create_table(
        "playoff_team_box_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("rebounds", sa.Integer(), nullable=False),
        sa.Column("assists", sa.Integer(), nullable=False),
        sa.Column("steals", sa.Integer(), nullable=False),
        sa.Column("blocks", sa.Integer(), nullable=False),
        sa.Column("turnovers", sa.Integer(), nullable=False),
        sa.Column("field_goals_made", sa.Integer(), nullable=False),
        sa.Column("field_goals_attempted", sa.Integer(), nullable=False),
        sa.Column("three_pointers_made", sa.Integer(), nullable=False),
        sa.Column("three_pointers_attempted", sa.Integer(), nullable=False),
        sa.Column("free_throws_made", sa.Integer(), nullable=False),
        sa.Column("free_throws_attempted", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["game_id"], ["playoff_games.id"],
            name="fk_playoff_team_box_scores_game_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"],
            name="fk_playoff_team_box_scores_team_id", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "team_id", name="uq_playoff_team_box_scores_game_team"),
    )
    op.create_index("ix_playoff_team_box_scores_game_id", "playoff_team_box_scores", ["game_id"])
    op.create_index("ix_playoff_team_box_scores_team_id", "playoff_team_box_scores", ["team_id"])

    op.create_table(
        "playoff_player_box_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("rebounds", sa.Integer(), nullable=False),
        sa.Column("assists", sa.Integer(), nullable=False),
        sa.Column("steals", sa.Integer(), nullable=False),
        sa.Column("blocks", sa.Integer(), nullable=False),
        sa.Column("turnovers", sa.Integer(), nullable=False),
        sa.Column("field_goals_made", sa.Integer(), nullable=False),
        sa.Column("field_goals_attempted", sa.Integer(), nullable=False),
        sa.Column("three_pointers_made", sa.Integer(), nullable=False),
        sa.Column("three_pointers_attempted", sa.Integer(), nullable=False),
        sa.Column("free_throws_made", sa.Integer(), nullable=False),
        sa.Column("free_throws_attempted", sa.Integer(), nullable=False),
        sa.Column("plus_minus", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["game_id"], ["playoff_games.id"],
            name="fk_playoff_player_box_scores_game_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"],
            name="fk_playoff_player_box_scores_team_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"],
            name="fk_playoff_player_box_scores_player_id", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id", "team_id", "player_name",
            name="uq_playoff_player_box_scores_game_team_player",
        ),
    )
    op.create_index(
        "ix_playoff_player_box_scores_game_id", "playoff_player_box_scores", ["game_id"]
    )
    op.create_index(
        "ix_playoff_player_box_scores_team_id", "playoff_player_box_scores", ["team_id"]
    )
    op.create_index(
        "ix_playoff_player_box_scores_player_id", "playoff_player_box_scores", ["player_id"]
    )
    op.create_index(
        "ix_playoff_player_box_scores_player_name", "playoff_player_box_scores", ["player_name"]
    )


def downgrade() -> None:
    op.drop_table("playoff_player_box_scores")
    op.drop_table("playoff_team_box_scores")
    op.drop_table("playoff_games")
    op.drop_table("playoff_series")


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
