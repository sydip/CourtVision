"""Add intelligence assistant prediction and history schema.

Revision ID: 0007_intelligence_assistant
Revises: 0006_player_jersey_number
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_intelligence_assistant"
down_revision: str | None = "0006_player_jersey_number"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("arena", sa.String(length=120), nullable=True))
    op.add_column("teams", sa.Column("head_coach", sa.String(length=120), nullable=True))
    op.add_column("teams", sa.Column("general_manager", sa.String(length=120), nullable=True))
    op.add_column("teams", sa.Column("founded_year", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("country", sa.String(length=80), nullable=True))
    op.add_column("players", sa.Column("college", sa.String(length=120), nullable=True))
    op.add_column("players", sa.Column("draft_year", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("draft_round", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("draft_pick", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("years_pro", sa.Integer(), nullable=True))
    op.add_column(
        "player_season_summaries",
        sa.Column(
            "data_source",
            sa.String(length=80),
            nullable=False,
            server_default="nba_api",
        ),
    )
    op.add_column(
        "player_season_summaries",
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "team_season_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=True),
        sa.Column("losses", sa.Integer(), nullable=True),
        sa.Column("conference_rank", sa.Integer(), nullable=True),
        sa.Column("division_rank", sa.Integer(), nullable=True),
        sa.Column("offensive_rating", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("defensive_rating", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("net_rating", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("pace", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("made_playoffs", sa.Boolean(), nullable=True),
        sa.Column("playoff_result", sa.String(length=120), nullable=True),
        sa.Column("data_source", sa.String(length=80), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_team_season_stats_team_id_teams",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_team_season_stats"),
        sa.UniqueConstraint(
            "team_id",
            "season",
            name="uq_team_season_stats_team_id_season",
        ),
    )
    op.create_index("ix_team_season_stats_team_id", "team_season_stats", ["team_id"])
    op.create_index("ix_team_season_stats_season", "team_season_stats", ["season"])

    op.create_table(
        "player_team_seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_started", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_player_team_seasons_player_id_players",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_player_team_seasons_team_id_teams",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_player_team_seasons"),
        sa.UniqueConstraint(
            "player_id",
            "team_id",
            "season",
            name="uq_player_team_seasons_player_team_season",
        ),
    )
    op.create_index("ix_player_team_seasons_player_id", "player_team_seasons", ["player_id"])
    op.create_index("ix_player_team_seasons_team_id", "player_team_seasons", ["team_id"])
    op.create_index("ix_player_team_seasons_season", "player_team_seasons", ["season"])

    op.create_table(
        "awards_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("award_type", sa.String(length=32), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("voting_share", sa.Numeric(precision=7, scale=5), nullable=True),
        sa.Column("data_source", sa.String(length=80), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_awards_history_player_id_players",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_awards_history_team_id_teams",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_awards_history"),
    )
    op.create_index("ix_awards_history_season", "awards_history", ["season"])
    op.create_index("ix_awards_history_award_type", "awards_history", ["award_type"])
    op.create_index("ix_awards_history_player_id", "awards_history", ["player_id"])
    op.create_index("ix_awards_history_team_id", "awards_history", ["team_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("target_season", sa.String(length=16), nullable=False),
        sa.Column("prediction_type", sa.String(length=48), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_predictions"),
    )
    op.create_index("ix_predictions_created_at", "predictions", ["created_at"])
    op.create_index("ix_predictions_target_season", "predictions", ["target_season"])
    op.create_index("ix_predictions_prediction_type", "predictions", ["prediction_type"])

    op.create_table(
        "injuries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("games_missed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_injuries_player_id_players",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_injuries"),
    )
    op.create_index("ix_injuries_player_id", "injuries", ["player_id"])
    op.create_index("ix_injuries_season", "injuries", ["season"])
    op.create_index("ix_injuries_status", "injuries", ["status"])


def downgrade() -> None:
    op.drop_index("ix_injuries_status", table_name="injuries")
    op.drop_index("ix_injuries_season", table_name="injuries")
    op.drop_index("ix_injuries_player_id", table_name="injuries")
    op.drop_table("injuries")
    op.drop_index("ix_predictions_prediction_type", table_name="predictions")
    op.drop_index("ix_predictions_target_season", table_name="predictions")
    op.drop_index("ix_predictions_created_at", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_awards_history_team_id", table_name="awards_history")
    op.drop_index("ix_awards_history_player_id", table_name="awards_history")
    op.drop_index("ix_awards_history_award_type", table_name="awards_history")
    op.drop_index("ix_awards_history_season", table_name="awards_history")
    op.drop_table("awards_history")
    op.drop_index("ix_player_team_seasons_season", table_name="player_team_seasons")
    op.drop_index("ix_player_team_seasons_team_id", table_name="player_team_seasons")
    op.drop_index("ix_player_team_seasons_player_id", table_name="player_team_seasons")
    op.drop_table("player_team_seasons")
    op.drop_index("ix_team_season_stats_season", table_name="team_season_stats")
    op.drop_index("ix_team_season_stats_team_id", table_name="team_season_stats")
    op.drop_table("team_season_stats")
    op.drop_column("player_season_summaries", "is_synthetic")
    op.drop_column("player_season_summaries", "data_source")
    op.drop_column("players", "years_pro")
    op.drop_column("players", "draft_pick")
    op.drop_column("players", "draft_round")
    op.drop_column("players", "draft_year")
    op.drop_column("players", "college")
    op.drop_column("players", "country")
    op.drop_column("teams", "founded_year")
    op.drop_column("teams", "general_manager")
    op.drop_column("teams", "head_coach")
    op.drop_column("teams", "arena")
