from __future__ import annotations

from typing import Literal

AssistantIntent = Literal[
    "player_season_stats",
    "player_game_stats_exact",
    "player_game_log_filter",
    "team_season_summary",
    "standings_lookup",
    "roster_lookup",
    "team_leaders",
    "player_comparison",
    "similar_players",
    "methodology_explanation",
    "data_availability",
    "unsupported_request",
]


def classify_intent(question: str) -> AssistantIntent:
    value = question.casefold()
    if any(word in value for word in ("predict", "projection", "bet", "wager", "odds")):
        return "unsupported_request"
    if "methodolog" in value or "how is" in value or "how do you calculate" in value:
        return "methodology_explanation"
    if "available" in value or "what data" in value:
        return "data_availability"
    if "compare" in value or " versus " in value:
        return "player_comparison"
    if "similar" in value:
        return "similar_players"
    if "roster" in value or "played for" in value:
        return "roster_lookup"
    if "led" in value or "leader" in value:
        return "team_leaders"
    if "standing" in value or "top 5" in value or "top five" in value:
        return "standings_lookup"
    if "record" in value:
        return "team_season_summary"
    if "game log" in value or "games against" in value:
        return "player_game_log_filter"
    if any(month in value for month in _MONTHS) and any(stat in value for stat in _STATS):
        return "player_game_stats_exact"
    return "player_season_stats"


_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_STATS = ("point", "rebound", "assist", "steal", "block", "turnover")
