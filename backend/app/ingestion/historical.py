from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import cast

from app.data.providers.base import BasketballDataProvider
from app.data.source_schemas import (
    SourceGame,
    SourceRosterMembership,
    SourceStanding,
    SourceTeamGameLog,
)

EASTERN_TEAMS = {
    "ATL",
    "BOS",
    "BKN",
    "CHA",
    "CHI",
    "CLE",
    "DET",
    "IND",
    "MIA",
    "MIL",
    "NYK",
    "ORL",
    "PHI",
    "TOR",
    "WAS",
}


class HistoricalProvider:
    """Adds deterministic season records derived from a batch provider's raw results."""

    def __init__(self, provider: BasketballDataProvider) -> None:
        self.provider = provider

    def __getattr__(self, name: str) -> object:
        return getattr(self.provider, name)

    def get_games(self) -> list[SourceGame]:
        games = self.provider.get_games()
        native_loader = getattr(self.provider, "get_team_game_logs", None)
        if native_loader is None:
            return games
        logs = native_loader(games[0].season) if games else []
        logs_by_game: dict[str, list[SourceTeamGameLog]] = defaultdict(list)
        for log in logs:
            logs_by_game[log.nba_game_id].append(log)
        return [
            game.model_copy(
                update={
                    "home_score": next(
                        (log.points for log in logs_by_game[game.nba_game_id] if log.is_home),
                        game.home_score,
                    ),
                    "away_score": next(
                        (log.points for log in logs_by_game[game.nba_game_id] if not log.is_home),
                        game.away_score,
                    ),
                }
            )
            for game in games
        ]

    def get_roster_memberships(self, season: str) -> list[SourceRosterMembership]:
        return [
            SourceRosterMembership(
                nba_player_id=player.nba_player_id,
                nba_team_id=player.team_nba_id,
                season=season,
                position=player.position,
            )
            for player in self.provider.get_players()
            if player.team_nba_id is not None
        ]

    def get_team_game_logs(self, season: str) -> list[SourceTeamGameLog]:
        native_loader = getattr(self.provider, "get_team_game_logs", None)
        if native_loader is not None:
            return cast(list[SourceTeamGameLog], native_loader(season))
        rows: list[SourceTeamGameLog] = []
        for game in self.provider.get_games():
            if game.season != season or game.home_score is None or game.away_score is None:
                continue
            rows.extend(
                [
                    SourceTeamGameLog(
                        nba_team_id=game.home_team_nba_id,
                        nba_game_id=game.nba_game_id,
                        season=season,
                        is_home=True,
                        points=game.home_score,
                        opponent_points=game.away_score,
                        result="W" if game.home_score > game.away_score else "L",
                    ),
                    SourceTeamGameLog(
                        nba_team_id=game.away_team_nba_id,
                        nba_game_id=game.nba_game_id,
                        season=season,
                        is_home=False,
                        points=game.away_score,
                        opponent_points=game.home_score,
                        result="W" if game.away_score > game.home_score else "L",
                    ),
                ]
            )
        return rows

    def get_standings(self, season: str) -> list[SourceStanding]:
        native_loader = getattr(self.provider, "get_standings", None)
        if native_loader is not None:
            return cast(list[SourceStanding], native_loader(season))
        records = self.get_team_game_logs(season)
        totals: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        for record in records:
            totals[record.nba_team_id][0 if record.result == "W" else 1] += 1
        teams = {team.nba_team_id: team for team in self.provider.get_teams()}
        by_conference: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
        for team_id, (wins, losses) in totals.items():
            team = teams[team_id]
            conference = team.conference or (
                "East" if team.abbreviation.upper() in EASTERN_TEAMS else "West"
            )
            by_conference[conference].append((team_id, wins, losses))
        standings: list[SourceStanding] = []
        for conference, values in by_conference.items():
            ordered = sorted(values, key=lambda value: (-value[1], value[2], value[0]))
            for rank, (team_id, wins, losses) in enumerate(ordered, start=1):
                games = wins + losses
                standings.append(
                    SourceStanding(
                        nba_team_id=team_id,
                        season=season,
                        conference=conference,
                        rank=rank,
                        wins=wins,
                        losses=losses,
                        win_pct=Decimal(wins) / Decimal(games) if games else Decimal(0),
                    )
                )
        return standings
