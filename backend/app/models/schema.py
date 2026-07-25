from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("nba_team_id", name="uq_teams_nba_team_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nba_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    conference: Mapped[str | None] = mapped_column(String(24))
    division: Mapped[str | None] = mapped_column(String(48))
    arena: Mapped[str | None] = mapped_column(String(120))
    head_coach: Mapped[str | None] = mapped_column(String(120))
    general_manager: Mapped[str | None] = mapped_column(String(120))
    founded_year: Mapped[int | None] = mapped_column(Integer)

    players: Mapped[list[Player]] = relationship(back_populates="team")
    home_games: Mapped[list[Game]] = relationship(
        back_populates="home_team",
        foreign_keys="Game.home_team_id",
    )
    away_games: Mapped[list[Game]] = relationship(
        back_populates="away_team",
        foreign_keys="Game.away_team_id",
    )
    player_game_stats: Mapped[list[PlayerGameStat]] = relationship(back_populates="team")
    season_summaries: Mapped[list[PlayerSeasonSummary]] = relationship(back_populates="team")
    team_season_stats: Mapped[list[TeamSeasonStat]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )
    player_team_seasons: Mapped[list[PlayerTeamSeason]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )
    draft_picks: Mapped[list[DraftPick]] = relationship(back_populates="team")


class Player(TimestampMixin, Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("nba_player_id", name="uq_players_nba_player_id"),
        UniqueConstraint("slug", name="uq_players_slug"),
        Index("ix_players_full_name", "full_name"),
        Index("ix_players_slug", "slug"),
        Index("ix_players_team_id", "team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nba_player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", name="fk_players_team_id_teams", ondelete="SET NULL"),
    )
    position: Mapped[str | None] = mapped_column(String(32))
    height: Mapped[str | None] = mapped_column(String(16))
    weight_pounds: Mapped[int | None] = mapped_column(Integer)
    birthdate: Mapped[date | None] = mapped_column(Date)
    jersey_number: Mapped[str | None] = mapped_column(String(8))
    country: Mapped[str | None] = mapped_column(String(80))
    college: Mapped[str | None] = mapped_column(String(120))
    draft_year: Mapped[int | None] = mapped_column(Integer)
    draft_round: Mapped[int | None] = mapped_column(Integer)
    draft_pick: Mapped[int | None] = mapped_column(Integer)
    years_pro: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    team: Mapped[Team | None] = relationship(back_populates="players")
    game_stats: Mapped[list[PlayerGameStat]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )
    season_summaries: Mapped[list[PlayerSeasonSummary]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )
    performance_reports: Mapped[list[PerformanceReport]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )
    team_seasons: Mapped[list[PlayerTeamSeason]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )
    injuries: Mapped[list[Injury]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )


class Game(TimestampMixin, Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("nba_game_id", name="uq_games_nba_game_id"),
        Index("ix_games_game_date", "game_date"),
        Index("ix_games_season", "season"),
        Index("ix_games_home_team_id", "home_team_id"),
        Index("ix_games_away_team_id", "away_team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nba_game_id: Mapped[str] = mapped_column(String(32), nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_games_home_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_games_away_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)

    home_team: Mapped[Team] = relationship(
        back_populates="home_games",
        foreign_keys=[home_team_id],
    )
    away_team: Mapped[Team] = relationship(
        back_populates="away_games",
        foreign_keys=[away_team_id],
    )
    player_stats: Mapped[list[PlayerGameStat]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )


class PlayerGameStat(TimestampMixin, Base):
    __tablename__ = "player_game_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_player_game_stats_player_id_game_id"),
        Index("ix_player_game_stats_player_id", "player_id"),
        Index("ix_player_game_stats_game_id", "game_id"),
        Index("ix_player_game_stats_team_id", "team_id"),
        Index("ix_player_game_stats_season", "season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", name="fk_player_game_stats_player_id_players", ondelete="CASCADE"),
        nullable=False,
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", name="fk_player_game_stats_game_id_games", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", name="fk_player_game_stats_team_id_teams", ondelete="SET NULL"),
    )
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    matchup: Mapped[str | None] = mapped_column(String(32))
    is_home: Mapped[bool | None] = mapped_column(Boolean)
    result: Mapped[str | None] = mapped_column(String(1))
    days_since_previous_game: Mapped[int | None] = mapped_column(Integer)
    minutes: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    steals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    blocks: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    turnovers: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    personal_fouls: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    field_goals_made: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    field_goals_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    three_pointers_made: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    three_pointers_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    free_throws_made: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    free_throws_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    plus_minus: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    player: Mapped[Player] = relationship(back_populates="game_stats")
    game: Mapped[Game] = relationship(back_populates="player_stats")
    team: Mapped[Team | None] = relationship(back_populates="player_game_stats")


class PlayoffSeries(TimestampMixin, Base):
    __tablename__ = "playoff_series"
    __table_args__ = (
        UniqueConstraint(
            "season", "round_name", "winner_team_id", "loser_team_id",
            name="uq_playoff_series_season_round_teams",
        ),
        Index("ix_playoff_series_season_round", "season", "round_name"),
        Index("ix_playoff_series_winner_team_id", "winner_team_id"),
        Index("ix_playoff_series_loser_team_id", "loser_team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    round_name: Mapped[str] = mapped_column(String(48), nullable=False)
    conference: Mapped[str] = mapped_column(String(16), nullable=False)
    winner_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_playoff_series_winner_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    loser_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_playoff_series_loser_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    winner_wins: Mapped[int] = mapped_column(Integer, nullable=False)
    loser_wins: Mapped[int] = mapped_column(Integer, nullable=False)
    data_source: Mapped[str] = mapped_column(String(120), nullable=False)

    winner_team: Mapped[Team] = relationship(foreign_keys=[winner_team_id])
    loser_team: Mapped[Team] = relationship(foreign_keys=[loser_team_id])
    games: Mapped[list[PlayoffGame]] = relationship(
        back_populates="series", cascade="all, delete-orphan",
        order_by="PlayoffGame.game_number",
    )


class PlayoffGame(TimestampMixin, Base):
    __tablename__ = "playoff_games"
    __table_args__ = (
        UniqueConstraint("series_id", "game_number", name="uq_playoff_games_series_game"),
        Index("ix_playoff_games_series_id", "series_id"),
        Index("ix_playoff_games_home_team_id", "home_team_id"),
        Index("ix_playoff_games_away_team_id", "away_team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("playoff_series.id", name="fk_playoff_games_series_id", ondelete="CASCADE"),
        nullable=False,
    )
    game_number: Mapped[int] = mapped_column(Integer, nullable=False)
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_playoff_games_home_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_playoff_games_away_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overtime: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    data_note: Mapped[str | None] = mapped_column(Text)

    series: Mapped[PlayoffSeries] = relationship(back_populates="games")
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    team_box_scores: Mapped[list[PlayoffTeamBoxScore]] = relationship(
        back_populates="game", cascade="all, delete-orphan",
    )
    player_box_scores: Mapped[list[PlayoffPlayerBoxScore]] = relationship(
        back_populates="game", cascade="all, delete-orphan",
    )


class PlayoffTeamBoxScore(TimestampMixin, Base):
    __tablename__ = "playoff_team_box_scores"
    __table_args__ = (
        UniqueConstraint("game_id", "team_id", name="uq_playoff_team_box_scores_game_team"),
        Index("ix_playoff_team_box_scores_game_id", "game_id"),
        Index("ix_playoff_team_box_scores_team_id", "team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey(
            "playoff_games.id",
            name="fk_playoff_team_box_scores_game_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_playoff_team_box_scores_team_id", ondelete="RESTRICT"),
        nullable=False,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    rebounds: Mapped[int] = mapped_column(Integer, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, nullable=False)
    steals: Mapped[int] = mapped_column(Integer, nullable=False)
    blocks: Mapped[int] = mapped_column(Integer, nullable=False)
    turnovers: Mapped[int] = mapped_column(Integer, nullable=False)
    field_goals_made: Mapped[int] = mapped_column(Integer, nullable=False)
    field_goals_attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    three_pointers_made: Mapped[int] = mapped_column(Integer, nullable=False)
    three_pointers_attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    free_throws_made: Mapped[int] = mapped_column(Integer, nullable=False)
    free_throws_attempted: Mapped[int] = mapped_column(Integer, nullable=False)

    game: Mapped[PlayoffGame] = relationship(back_populates="team_box_scores")
    team: Mapped[Team] = relationship()


class PlayoffPlayerBoxScore(TimestampMixin, Base):
    __tablename__ = "playoff_player_box_scores"
    __table_args__ = (
        UniqueConstraint(
            "game_id", "team_id", "player_name",
            name="uq_playoff_player_box_scores_game_team_player",
        ),
        Index("ix_playoff_player_box_scores_game_id", "game_id"),
        Index("ix_playoff_player_box_scores_team_id", "team_id"),
        Index("ix_playoff_player_box_scores_player_id", "player_id"),
        Index("ix_playoff_player_box_scores_player_name", "player_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey(
            "playoff_games.id",
            name="fk_playoff_player_box_scores_game_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_playoff_player_box_scores_team_id", ondelete="RESTRICT"),
        nullable=False,
    )
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", name="fk_playoff_player_box_scores_player_id", ondelete="SET NULL")
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    rebounds: Mapped[int] = mapped_column(Integer, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, nullable=False)
    steals: Mapped[int] = mapped_column(Integer, nullable=False)
    blocks: Mapped[int] = mapped_column(Integer, nullable=False)
    turnovers: Mapped[int] = mapped_column(Integer, nullable=False)
    field_goals_made: Mapped[int] = mapped_column(Integer, nullable=False)
    field_goals_attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    three_pointers_made: Mapped[int] = mapped_column(Integer, nullable=False)
    three_pointers_attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    free_throws_made: Mapped[int] = mapped_column(Integer, nullable=False)
    free_throws_attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    plus_minus: Mapped[int | None] = mapped_column(Integer)

    game: Mapped[PlayoffGame] = relationship(back_populates="player_box_scores")
    team: Mapped[Team] = relationship()
    player: Mapped[Player | None] = relationship()


class PlayerSeasonSummary(TimestampMixin, Base):
    __tablename__ = "player_season_summaries"
    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uq_player_season_summaries_player_id_season"),
        Index("ix_player_season_summaries_lookup", "player_id", "season"),
        Index("ix_player_season_summaries_player_id", "player_id"),
        Index("ix_player_season_summaries_team_id", "team_id"),
        Index("ix_player_season_summaries_season", "season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey(
            "players.id", name="fk_player_season_summaries_player_id_players", ondelete="CASCADE"
        ),
        nullable=False,
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "teams.id", name="fk_player_season_summaries_team_id_teams", ondelete="SET NULL"
        ),
    )
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    games_played: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    minutes_per_game: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    points_per_game: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    rebounds_per_game: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    assists_per_game: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    turnovers_per_game: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    plus_minus_per_game: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    true_shooting_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    true_shooting_source: Mapped[str | None] = mapped_column(String(64))
    usage_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    points_per_36: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    rebounds_per_36: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    assists_per_36: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    turnovers_per_36: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    league_percentiles: Mapped[dict[str, object] | None] = mapped_column(JSON)
    position_percentiles: Mapped[dict[str, object] | None] = mapped_column(JSON)
    minutes_tier_percentiles: Mapped[dict[str, object] | None] = mapped_column(JSON)
    production_trend: Mapped[str | None] = mapped_column(String(24))
    production_trend_value: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    efficiency_trend: Mapped[str | None] = mapped_column(String(24))
    efficiency_trend_value: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    trend_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    analytics_warnings: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    analytics_rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_source: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="nba_api",
        server_default="nba_api",
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    player: Mapped[Player] = relationship(back_populates="season_summaries")
    team: Mapped[Team | None] = relationship(back_populates="season_summaries")


class SyncRun(TimestampMixin, Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        Index("ix_sync_runs_source", "source"),
        Index("ix_sync_runs_season", "season"),
        Index("ix_sync_runs_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    season: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    fetched_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    inserted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    rejected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(Text)


class PerformanceReport(TimestampMixin, Base):
    __tablename__ = "performance_reports"
    __table_args__ = (
        UniqueConstraint("report_key", name="uq_performance_reports_report_key"),
        Index("ix_performance_reports_player_id", "player_id"),
        Index("ix_performance_reports_season", "season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "players.id", name="fk_performance_reports_player_id_players", ondelete="CASCADE"
        ),
    )
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    report_type: Mapped[str] = mapped_column(String(48), nullable=False)
    report_key: Mapped[str] = mapped_column(String(180), nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    player: Mapped[Player | None] = relationship(back_populates="performance_reports")


class TeamSeasonStat(TimestampMixin, Base):
    __tablename__ = "team_season_stats"
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season_stats_team_id_season"),
        Index("ix_team_season_stats_team_id", "team_id"),
        Index("ix_team_season_stats_season", "season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_team_season_stats_team_id_teams", ondelete="CASCADE"),
        nullable=False,
    )
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    wins: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    conference_rank: Mapped[int | None] = mapped_column(Integer)
    division_rank: Mapped[int | None] = mapped_column(Integer)
    offensive_rating: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    defensive_rating: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    net_rating: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    pace: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    made_playoffs: Mapped[bool | None] = mapped_column(Boolean)
    playoff_result: Mapped[str | None] = mapped_column(String(120))
    data_source: Mapped[str] = mapped_column(String(80), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    team: Mapped[Team] = relationship(back_populates="team_season_stats")


class PlayerTeamSeason(TimestampMixin, Base):
    __tablename__ = "player_team_seasons"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "team_id",
            "season",
            name="uq_player_team_seasons_player_team_season",
        ),
        Index("ix_player_team_seasons_player_id", "player_id"),
        Index("ix_player_team_seasons_team_id", "team_id"),
        Index("ix_player_team_seasons_season", "season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey(
            "players.id",
            name="fk_player_team_seasons_player_id_players",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey(
            "teams.id",
            name="fk_player_team_seasons_team_id_teams",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    games_played: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    games_started: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    player: Mapped[Player] = relationship(back_populates="team_seasons")
    team: Mapped[Team] = relationship(back_populates="player_team_seasons")


class DraftPick(TimestampMixin, Base):
    __tablename__ = "draft_picks"
    __table_args__ = (
        UniqueConstraint(
            "draft_year",
            "overall_pick",
            name="uq_draft_picks_year_overall_pick",
        ),
        Index("ix_draft_picks_draft_year", "draft_year"),
        Index("ix_draft_picks_round", "round"),
        Index("ix_draft_picks_team_id", "team_id"),
        Index("ix_draft_picks_player_name", "player_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_year: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_pick: Mapped[int] = mapped_column(Integer, nullable=False)
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    school_country: Mapped[str] = mapped_column(String(160), nullable=False)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_draft_picks_team_id_teams", ondelete="RESTRICT"),
        nullable=False,
    )
    transaction_note: Mapped[str | None] = mapped_column(Text)
    data_source: Mapped[str] = mapped_column(String(120), nullable=False)

    team: Mapped[Team] = relationship(back_populates="draft_picks")


class AwardHistory(TimestampMixin, Base):
    __tablename__ = "awards_history"
    __table_args__ = (
        Index("ix_awards_history_season", "season"),
        Index("ix_awards_history_award_type", "award_type"),
        Index("ix_awards_history_player_id", "player_id"),
        Index("ix_awards_history_team_id", "team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    award_type: Mapped[str] = mapped_column(String(32), nullable=False)
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", name="fk_awards_history_player_id_players", ondelete="SET NULL"),
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", name="fk_awards_history_team_id_teams", ondelete="SET NULL"),
    )
    voting_share: Mapped[Decimal | None] = mapped_column(Numeric(7, 5))
    data_source: Mapped[str] = mapped_column(String(80), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_created_at", "created_at"),
        Index("ix_predictions_target_season", "target_season"),
        Index("ix_predictions_prediction_type", "prediction_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    target_season: Mapped[str] = mapped_column(String(16), nullable=False)
    prediction_type: Mapped[str] = mapped_column(String(48), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    random_seed: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class Injury(TimestampMixin, Base):
    __tablename__ = "injuries"
    __table_args__ = (
        Index("ix_injuries_player_id", "player_id"),
        Index("ix_injuries_season", "season"),
        Index("ix_injuries_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", name="fk_injuries_player_id_players", ondelete="CASCADE"),
        nullable=False,
    )
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    games_missed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)

    player: Mapped[Player] = relationship(back_populates="injuries")
