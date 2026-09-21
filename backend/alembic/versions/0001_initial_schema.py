"""Create initial CourtVision persistence schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-26 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nba_team_id", sa.Integer(), nullable=False),
        sa.Column("abbreviation", sa.String(length=5), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("conference", sa.String(length=24), nullable=True),
        sa.Column("division", sa.String(length=48), nullable=True),
        *timestamp_columns(),
        sa.UniqueConstraint("nba_team_id", name="uq_teams_nba_team_id"),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nba_player_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=True),
        sa.Column("last_name", sa.String(length=80), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.String(length=32), nullable=True),
        sa.Column("height", sa.String(length=16), nullable=True),
        sa.Column("weight_pounds", sa.Integer(), nullable=True),
        sa.Column("birthdate", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name="fk_players_team_id_teams", ondelete="SET NULL"
        ),
        sa.UniqueConstraint("nba_player_id", name="uq_players_nba_player_id"),
        sa.UniqueConstraint("slug", name="uq_players_slug"),
    )
    op.create_index("ix_players_full_name", "players", ["full_name"])
    op.create_index("ix_players_slug", "players", ["slug"])
    op.create_index("ix_players_team_id", "players", ["team_id"])

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nba_game_id", sa.String(length=32), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["away_team_id"], ["teams.id"], name="fk_games_away_team_id_teams", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"], ["teams.id"], name="fk_games_home_team_id_teams", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("nba_game_id", name="uq_games_nba_game_id"),
    )
    op.create_index("ix_games_away_team_id", "games", ["away_team_id"])
    op.create_index("ix_games_game_date", "games", ["game_date"])
    op.create_index("ix_games_home_team_id", "games", ["home_team_id"])
    op.create_index("ix_games_season", "games", ["season"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        *timestamp_columns(),
    )
    op.create_index("ix_sync_runs_season", "sync_runs", ["season"])
    op.create_index("ix_sync_runs_source", "sync_runs", ["source"])
    op.create_index("ix_sync_runs_status", "sync_runs", ["status"])

    op.create_table(
        "player_game_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("minutes", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rebounds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("steals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("turnovers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("field_goals_made", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("field_goals_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("three_pointers_made", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("three_pointers_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("free_throws_made", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("free_throws_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plus_minus", sa.Numeric(precision=6, scale=2), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"], name="fk_player_game_stats_game_id_games", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_player_game_stats_player_id_players",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_player_game_stats_team_id_teams",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("player_id", "game_id", name="uq_player_game_stats_player_id_game_id"),
    )
    op.create_index("ix_player_game_stats_game_id", "player_game_stats", ["game_id"])
    op.create_index("ix_player_game_stats_player_id", "player_game_stats", ["player_id"])
    op.create_index("ix_player_game_stats_season", "player_game_stats", ["season"])
    op.create_index("ix_player_game_stats_team_id", "player_game_stats", ["team_id"])

    op.create_table(
        "player_season_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minutes_per_game", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("points_per_game", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("rebounds_per_game", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("assists_per_game", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("true_shooting_percentage", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("usage_rate", sa.Numeric(precision=6, scale=3), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_player_season_summaries_player_id_players",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_player_season_summaries_team_id_teams",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "player_id", "season", name="uq_player_season_summaries_player_id_season"
        ),
    )
    op.create_index(
        "ix_player_season_summaries_lookup", "player_season_summaries", ["player_id", "season"]
    )
    op.create_index(
        "ix_player_season_summaries_player_id", "player_season_summaries", ["player_id"]
    )
    op.create_index("ix_player_season_summaries_season", "player_season_summaries", ["season"])
    op.create_index("ix_player_season_summaries_team_id", "player_season_summaries", ["team_id"])

    op.create_table(
        "performance_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("report_type", sa.String(length=48), nullable=False),
        sa.Column("report_key", sa.String(length=180), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_performance_reports_player_id_players",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("report_key", name="uq_performance_reports_report_key"),
    )
    op.create_index("ix_performance_reports_player_id", "performance_reports", ["player_id"])
    op.create_index("ix_performance_reports_season", "performance_reports", ["season"])


def downgrade() -> None:
    op.drop_index("ix_performance_reports_season", table_name="performance_reports")
    op.drop_index("ix_performance_reports_player_id", table_name="performance_reports")
    op.drop_table("performance_reports")

    op.drop_index("ix_player_season_summaries_team_id", table_name="player_season_summaries")
    op.drop_index("ix_player_season_summaries_season", table_name="player_season_summaries")
    op.drop_index("ix_player_season_summaries_player_id", table_name="player_season_summaries")
    op.drop_index("ix_player_season_summaries_lookup", table_name="player_season_summaries")
    op.drop_table("player_season_summaries")

    op.drop_index("ix_player_game_stats_team_id", table_name="player_game_stats")
    op.drop_index("ix_player_game_stats_season", table_name="player_game_stats")
    op.drop_index("ix_player_game_stats_player_id", table_name="player_game_stats")
    op.drop_index("ix_player_game_stats_game_id", table_name="player_game_stats")
    op.drop_table("player_game_stats")

    op.drop_index("ix_sync_runs_status", table_name="sync_runs")
    op.drop_index("ix_sync_runs_source", table_name="sync_runs")
    op.drop_index("ix_sync_runs_season", table_name="sync_runs")
    op.drop_table("sync_runs")

    op.drop_index("ix_games_season", table_name="games")
    op.drop_index("ix_games_home_team_id", table_name="games")
    op.drop_index("ix_games_game_date", table_name="games")
    op.drop_index("ix_games_away_team_id", table_name="games")
    op.drop_table("games")

    op.drop_index("ix_players_team_id", table_name="players")
    op.drop_index("ix_players_slug", table_name="players")
    op.drop_index("ix_players_full_name", table_name="players")
    op.drop_table("players")

    op.drop_table("teams")
