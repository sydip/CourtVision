from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ParsedQuery:
    question: str
    season: str
    game_date: str | None
    stat: str | None
    conference: str | None
    limit: int | None


def parse_query(question: str, selected_season: str | None) -> ParsedQuery:
    season_match = re.search(r"\b(20\d{2}-\d{2})\b", question)
    season = season_match.group(1) if season_match else selected_season or "2025-26"
    lowered = question.casefold()
    stat = next(
        (
            name
            for name in ("points", "rebounds", "assists", "steals", "blocks", "turnovers")
            if name.rstrip("s") in lowered
        ),
        None,
    )
    conference = "East" if "east" in lowered else "West" if "west" in lowered else None
    limit = 5 if "top 5" in lowered or "top five" in lowered else None
    return ParsedQuery(question, season, _extract_date(question), stat, conference, limit)


def _extract_date(question: str) -> str | None:
    match = re.search(r"\b([A-Za-z]+\s+\d{1,2},?\s+20\d{2})\b", question)
    if not match:
        return None
    normalized = match.group(1).replace(",", "")
    try:
        return datetime.strptime(normalized, "%B %d %Y").date().isoformat()
    except ValueError:
        return None
