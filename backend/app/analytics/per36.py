from __future__ import annotations

from dataclasses import dataclass


def calculate_per_36(value: int | float | None, minutes: int | float | None) -> float | None:
    if value is None or minutes is None or minutes == 0:
        return None
    return (float(value) / float(minutes)) * 36


@dataclass(frozen=True)
class Per36Line:
    points: float | None
    rebounds: float | None
    assists: float | None
    turnovers: float | None


def calculate_per_36_line(
    *,
    points: int | float | None,
    rebounds: int | float | None,
    assists: int | float | None,
    turnovers: int | float | None,
    minutes: int | float | None,
) -> Per36Line:
    return Per36Line(
        points=calculate_per_36(points, minutes),
        rebounds=calculate_per_36(rebounds, minutes),
        assists=calculate_per_36(assists, minutes),
        turnovers=calculate_per_36(turnovers, minutes),
    )
