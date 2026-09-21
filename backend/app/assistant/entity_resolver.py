from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Player, Team

T = TypeVar("T")


@dataclass(frozen=True)
class Resolution(Generic[T]):
    matches: list[T]
    ambiguous: bool = False


def resolve_players(session: Session, question: str) -> Resolution[Player]:
    players = list(session.scalars(select(Player).order_by(Player.full_name)))
    lowered = question.casefold()
    exact = [player for player in players if player.full_name.casefold() in lowered]
    if exact:
        return Resolution(exact)
    tokens = set(_words(question))
    surname = [player for player in players if player.full_name.casefold().split()[-1] in tokens]
    if surname:
        return Resolution(surname, len(surname) > 1)
    scored = sorted(
        (
            (
                SequenceMatcher(None, question.casefold(), player.full_name.casefold()).ratio(),
                player,
            )
            for player in players
        ),
        key=lambda item: (-item[0], item[1].full_name),
    )
    matches = [player for score, player in scored if score >= 0.55]
    return Resolution(matches[:2], len(matches) > 1)


def resolve_teams(session: Session, question: str) -> Resolution[Team]:
    teams = list(session.scalars(select(Team).order_by(Team.name)))
    lowered = question.casefold()
    matches = []
    for team in teams:
        variants = {
            team.abbreviation.casefold(),
            team.city.casefold(),
            team.name.casefold(),
            f"{team.city} {team.name}".casefold(),
        }
        if any(re.search(rf"\b{re.escape(value)}\b", lowered) for value in variants):
            matches.append(team)
    return Resolution(matches, len(matches) > 1)


def _words(value: str) -> list[str]:
    return re.findall(r"[a-z'-]+", value.casefold())
