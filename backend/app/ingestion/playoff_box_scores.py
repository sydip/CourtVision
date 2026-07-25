from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_engine
from app.models import (
    Player,
    PlayoffGame,
    PlayoffPlayerBoxScore,
    PlayoffSeries,
    PlayoffTeamBoxScore,
    Team,
)

SEASON = "2025-26"
ROUND_NAME = "First Round"
DATA_SOURCE = "user-provided-2025-26-first-round-box-scores"
EXPECTED_FIRST_ROUND_GAMES = 48
DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "fixtures"
    / "playoffs_first_round_2025_26.md"
)

TEAM_ALIASES = {
    "Atlanta": "ATL",
    "Atlanta Hawks": "ATL",
    "Boston": "BOS",
    "Boston Celtics": "BOS",
    "Cleveland": "CLE",
    "Cleveland Cavaliers": "CLE",
    "Denver": "DEN",
    "Denver Nuggets": "DEN",
    "Detroit": "DET",
    "Detroit Pistons": "DET",
    "Houston": "HOU",
    "Houston Rockets": "HOU",
    "LA Lakers": "LAL",
    "Los Angeles Lakers": "LAL",
    "Minnesota": "MIN",
    "Minnesota Timberwolves": "MIN",
    "New York": "NYK",
    "New York Knicks": "NYK",
    "Oklahoma City": "OKC",
    "Oklahoma City Thunder": "OKC",
    "Orlando": "ORL",
    "Orlando Magic": "ORL",
    "Philadelphia": "PHI",
    "Philadelphia 76ers": "PHI",
    "Phoenix": "PHX",
    "Phoenix Suns": "PHX",
    "Portland": "POR",
    "Portland Trail Blazers": "POR",
    "San Antonio": "SAS",
    "San Antonio Spurs": "SAS",
    "Toronto": "TOR",
    "Toronto Raptors": "TOR",
}

SERIES_RE = re.compile(
    r"^### (?P<winner>.+?) def\. (?P<loser>.+?), "
    r"(?P<winner_wins>\d+)[\u2013-](?P<loser_wins>\d+)$"
)
GAME_RE = re.compile(
    r"^#### Game (?P<number>\d+): "
    r"(?P<first_team>.+?) (?P<first_score>\d+), "
    r"(?P<second_team>.+?) (?P<second_score>\d+) "
    r"\((?P<context>.+)\)$"
)
TEAM_TOTAL_RE = re.compile(
    r"(?P<team>[A-Z]{2,3}): "
    r"(?P<fg>\d+-\d+) FG, "
    r"(?P<three>\d+-\d+) 3PT, "
    r"(?P<ft>\d+-\d+) FT, "
    r"(?P<reb>\d+) REB, "
    r"(?P<ast>\d+) AST, "
    r"(?P<stl>\d+) STL, "
    r"(?P<blk>\d+) BLK, "
    r"(?P<turnovers>\d+) TO"
)


@dataclass
class ParsedPlayerBox:
    name: str
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    field_goals_made: int
    field_goals_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int
    plus_minus: int | None


@dataclass
class ParsedTeamBox:
    abbreviation: str
    field_goals_made: int
    field_goals_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    players: list[ParsedPlayerBox] = field(default_factory=list)


@dataclass
class ParsedGame:
    number: int
    home_team: str
    away_team: str
    scores: dict[str, int]
    overtime: bool
    team_boxes: dict[str, ParsedTeamBox] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class ParsedSeries:
    conference: str
    winner_team: str
    loser_team: str
    winner_wins: int
    loser_wins: int
    games: list[ParsedGame] = field(default_factory=list)


def parse_playoff_box_scores(source: Path = DEFAULT_SOURCE) -> list[ParsedSeries]:
    lines = source.read_text(encoding="utf-8").splitlines()
    series: list[ParsedSeries] = []
    conference: str | None = None
    current_series: ParsedSeries | None = None
    current_game: ParsedGame | None = None
    current_team: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("## EASTERN CONFERENCE"):
            conference = "East"
            continue
        if line.startswith("## WESTERN CONFERENCE"):
            conference = "West"
            continue

        series_match = SERIES_RE.match(line)
        if series_match:
            if conference is None:
                raise ValueError("Series encountered before a conference heading.")
            current_series = ParsedSeries(
                conference=conference,
                winner_team=_team_abbreviation(series_match["winner"]),
                loser_team=_team_abbreviation(series_match["loser"]),
                winner_wins=int(series_match["winner_wins"]),
                loser_wins=int(series_match["loser_wins"]),
            )
            series.append(current_series)
            current_game = None
            current_team = None
            continue

        game_match = GAME_RE.match(line)
        if game_match:
            if current_series is None:
                raise ValueError("Game encountered before a series heading.")
            first_team = _team_abbreviation(game_match["first_team"])
            second_team = _team_abbreviation(game_match["second_team"])
            context = game_match["context"]
            home_name = context.split("at ", maxsplit=1)[-1]
            home_team = _team_abbreviation(home_name)
            if home_team not in (first_team, second_team):
                raise ValueError(f"Home team does not match Game {game_match['number']}.")
            away_team = second_team if home_team == first_team else first_team
            current_game = ParsedGame(
                number=int(game_match["number"]),
                home_team=home_team,
                away_team=away_team,
                scores={
                    first_team: int(game_match["first_score"]),
                    second_team: int(game_match["second_score"]),
                },
                overtime="OT" in context,
            )
            current_series.games.append(current_game)
            current_team = None
            continue

        if line.startswith("**Team Totals:**"):
            if current_game is None:
                raise ValueError("Team totals encountered before a game heading.")
            for match in TEAM_TOTAL_RE.finditer(line):
                abbreviation = match["team"]
                fg_made, fg_attempted = _shot_pair(match["fg"])
                three_made, three_attempted = _shot_pair(match["three"])
                ft_made, ft_attempted = _shot_pair(match["ft"])
                current_game.team_boxes[abbreviation] = ParsedTeamBox(
                    abbreviation=abbreviation,
                    field_goals_made=fg_made,
                    field_goals_attempted=fg_attempted,
                    three_pointers_made=three_made,
                    three_pointers_attempted=three_attempted,
                    free_throws_made=ft_made,
                    free_throws_attempted=ft_attempted,
                    rebounds=int(match["reb"]),
                    assists=int(match["ast"]),
                    steals=int(match["stl"]),
                    blocks=int(match["blk"]),
                    turnovers=int(match["turnovers"]),
                )
            continue

        if line.startswith("*Note:"):
            if current_game is not None:
                current_game.notes.append(line.strip("*"))
            continue

        header_cells = _table_cells(line)
        if len(header_cells) == 11 and header_cells[1:] == [
            "PTS", "REB", "AST", "STL", "BLK", "TO", "FG", "3PT", "FT", "+/-"
        ]:
            current_team = header_cells[0]
            continue

        if (
            current_game is not None
            and current_team is not None
            and current_team in current_game.team_boxes
            and len(header_cells) == 11
            and header_cells[0] != "---"
        ):
            current_game.team_boxes[current_team].players.append(_parse_player(header_cells))

    _validate(series)
    return series


def ingest_playoff_box_scores(
    session: Session,
    source: Path = DEFAULT_SOURCE,
) -> dict[str, int]:
    parsed = parse_playoff_box_scores(source)
    teams = {team.abbreviation: team for team in session.scalars(select(Team)).all()}
    required = {
        abbreviation
        for playoff_series in parsed
        for game in playoff_series.games
        for abbreviation in (game.home_team, game.away_team)
    }
    missing = sorted(required.difference(teams))
    if missing:
        raise ValueError(f"Playoff ingestion is missing stored teams: {', '.join(missing)}.")

    players = {
        _normalize_name(player.full_name): player
        for player in session.scalars(select(Player)).all()
    }
    inserted = 0
    updated = 0
    player_rows = 0

    for parsed_series in parsed:
        winner = teams[parsed_series.winner_team]
        loser = teams[parsed_series.loser_team]
        stored_series = session.scalar(
            select(PlayoffSeries).where(
                PlayoffSeries.season == SEASON,
                PlayoffSeries.round_name == ROUND_NAME,
                PlayoffSeries.winner_team_id == winner.id,
                PlayoffSeries.loser_team_id == loser.id,
            )
        )
        if stored_series is None:
            stored_series = PlayoffSeries(
                season=SEASON,
                round_name=ROUND_NAME,
                conference=parsed_series.conference,
                winner_team_id=winner.id,
                loser_team_id=loser.id,
                winner_wins=parsed_series.winner_wins,
                loser_wins=parsed_series.loser_wins,
                data_source=DATA_SOURCE,
            )
            session.add(stored_series)
            inserted += 1
        else:
            stored_series.conference = parsed_series.conference
            stored_series.winner_wins = parsed_series.winner_wins
            stored_series.loser_wins = parsed_series.loser_wins
            stored_series.data_source = DATA_SOURCE
            updated += 1
        session.flush()

        for parsed_game in parsed_series.games:
            stored_game = session.scalar(
                select(PlayoffGame).where(
                    PlayoffGame.series_id == stored_series.id,
                    PlayoffGame.game_number == parsed_game.number,
                )
            )
            home = teams[parsed_game.home_team]
            away = teams[parsed_game.away_team]
            if stored_game is None:
                stored_game = PlayoffGame(
                    series_id=stored_series.id,
                    game_number=parsed_game.number,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    home_score=parsed_game.scores[parsed_game.home_team],
                    away_score=parsed_game.scores[parsed_game.away_team],
                    overtime=parsed_game.overtime,
                    data_note=" ".join(parsed_game.notes) or None,
                )
                session.add(stored_game)
                inserted += 1
            else:
                stored_game.home_team_id = home.id
                stored_game.away_team_id = away.id
                stored_game.home_score = parsed_game.scores[parsed_game.home_team]
                stored_game.away_score = parsed_game.scores[parsed_game.away_team]
                stored_game.overtime = parsed_game.overtime
                stored_game.data_note = " ".join(parsed_game.notes) or None
                updated += 1
            session.flush()

            existing_team_boxes = {
                row.team_id: row
                for row in session.scalars(
                    select(PlayoffTeamBoxScore).where(
                        PlayoffTeamBoxScore.game_id == stored_game.id
                    )
                )
            }
            existing_player_boxes = {
                (row.team_id, row.player_name): row
                for row in session.scalars(
                    select(PlayoffPlayerBoxScore).where(
                        PlayoffPlayerBoxScore.game_id == stored_game.id
                    )
                )
            }
            retained_players: set[tuple[int, str]] = set()

            for abbreviation, parsed_box in parsed_game.team_boxes.items():
                team = teams[abbreviation]
                team_box = existing_team_boxes.pop(team.id, None)
                values = _team_values(parsed_box, parsed_game.scores[abbreviation])
                if team_box is None:
                    team_box = PlayoffTeamBoxScore(
                        game_id=stored_game.id, team_id=team.id, **values
                    )
                    session.add(team_box)
                    inserted += 1
                else:
                    _assign(team_box, values)
                    updated += 1

                for parsed_player in parsed_box.players:
                    key = (team.id, parsed_player.name)
                    retained_players.add(key)
                    player_box = existing_player_boxes.get(key)
                    player = players.get(_normalize_name(parsed_player.name))
                    player_values = _player_values(parsed_player)
                    if player_box is None:
                        session.add(
                            PlayoffPlayerBoxScore(
                                game_id=stored_game.id,
                                team_id=team.id,
                                player_id=player.id if player is not None else None,
                                player_name=parsed_player.name,
                                **player_values,
                            )
                        )
                        inserted += 1
                    else:
                        player_box.player_id = player.id if player is not None else None
                        _assign(player_box, player_values)
                        updated += 1
                    player_rows += 1

            for stale_team_box in existing_team_boxes.values():
                session.delete(stale_team_box)
            for key, stale_player_box in existing_player_boxes.items():
                if key not in retained_players:
                    session.delete(stale_player_box)

    session.flush()
    return {
        "series": len(parsed),
        "games": sum(len(item.games) for item in parsed),
        "team_box_scores": sum(len(game.team_boxes) for item in parsed for game in item.games),
        "player_box_scores": player_rows,
        "inserted": inserted,
        "updated": updated,
    }


def _team_values(box: ParsedTeamBox, points: int) -> dict[str, int]:
    return {
        "points": points,
        "rebounds": box.rebounds,
        "assists": box.assists,
        "steals": box.steals,
        "blocks": box.blocks,
        "turnovers": box.turnovers,
        "field_goals_made": box.field_goals_made,
        "field_goals_attempted": box.field_goals_attempted,
        "three_pointers_made": box.three_pointers_made,
        "three_pointers_attempted": box.three_pointers_attempted,
        "free_throws_made": box.free_throws_made,
        "free_throws_attempted": box.free_throws_attempted,
    }


def _player_values(box: ParsedPlayerBox) -> dict[str, int | None]:
    return {
        "points": box.points,
        "rebounds": box.rebounds,
        "assists": box.assists,
        "steals": box.steals,
        "blocks": box.blocks,
        "turnovers": box.turnovers,
        "field_goals_made": box.field_goals_made,
        "field_goals_attempted": box.field_goals_attempted,
        "three_pointers_made": box.three_pointers_made,
        "three_pointers_attempted": box.three_pointers_attempted,
        "free_throws_made": box.free_throws_made,
        "free_throws_attempted": box.free_throws_attempted,
        "plus_minus": box.plus_minus,
    }


def _assign(record: object, values: Mapping[str, int | None]) -> None:
    for key, value in values.items():
        setattr(record, key, value)


def _parse_player(cells: list[str]) -> ParsedPlayerBox:
    fg_made, fg_attempted = _shot_pair(cells[7])
    three_made, three_attempted = _shot_pair(cells[8])
    ft_made, ft_attempted = _shot_pair(cells[9])
    return ParsedPlayerBox(
        name=cells[0],
        points=int(cells[1]),
        rebounds=int(cells[2]),
        assists=int(cells[3]),
        steals=int(cells[4]),
        blocks=int(cells[5]),
        turnovers=int(cells[6]),
        field_goals_made=fg_made,
        field_goals_attempted=fg_attempted,
        three_pointers_made=three_made,
        three_pointers_attempted=three_attempted,
        free_throws_made=ft_made,
        free_throws_attempted=ft_attempted,
        plus_minus=None if cells[10] == "--" else int(cells[10]),
    )


def _validate(series: list[ParsedSeries]) -> None:
    if not series:
        raise ValueError("No playoff series were parsed.")
    seen_games: set[tuple[str, str, int]] = set()
    for playoff_series in series:
        for game in playoff_series.games:
            key = (playoff_series.winner_team, playoff_series.loser_team, game.number)
            if key in seen_games:
                raise ValueError(f"Duplicate playoff game: {key}.")
            seen_games.add(key)
            expected_teams = {game.home_team, game.away_team}
            if set(game.team_boxes) != expected_teams:
                raise ValueError(f"Game {key} does not contain exactly two team totals.")


def _team_abbreviation(name: str) -> str:
    cleaned = name.strip()
    try:
        return TEAM_ALIASES[cleaned]
    except KeyError as exc:
        raise ValueError(f"Unknown playoff team name: {cleaned}.") from exc


def _shot_pair(value: str) -> tuple[int, int]:
    made, attempted = value.split("-", maxsplit=1)
    return int(made), int(attempted)


def _table_cells(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        return []
    return [cell.strip() for cell in line.strip("|").split("|")]


def _normalize_name(value: str) -> str:
    return value.replace("\u2019", "'").casefold().strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest supplied playoff box scores.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    SessionLocal.configure(bind=get_engine())
    with SessionLocal() as session:
        totals = ingest_playoff_box_scores(session, args.source)
        session.commit()
    print(
        "Playoff ingestion complete: "
        f"{totals['series']} series, {totals['games']} games, "
        f"{totals['team_box_scores']} team boxes, "
        f"{totals['player_box_scores']} player lines."
    )


if __name__ == "__main__":
    main()
