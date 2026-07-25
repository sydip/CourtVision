from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.system_prompt import SYSTEM_PROMPT
from app.assistant.tools import (
    compare_players,
    execute_tool,
    get_player,
    get_team,
    list_capabilities,
    predict_award,
    predict_league_standings,
)
from app.core.config import get_settings
from app.models import Player, Team

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_player",
        "description": "Look up a stored NBA player biography and season summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_team",
        "description": "Look up a stored NBA team, roster, and available record.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_or_abbr": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["name_or_abbr"],
        },
    },
    {
        "name": "compare_players",
        "description": "Compare stored season summaries for two or more NBA players.",
        "input_schema": {
            "type": "object",
            "properties": {
                "names": {"type": "array", "items": {"type": "string"}},
                "season": {"type": "string"},
            },
            "required": ["names"],
        },
    },
    {
        "name": "get_award_history",
        "description": "Return stored award history without inventing missing winners.",
        "input_schema": {
            "type": "object",
            "properties": {
                "award_type": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["award_type"],
        },
    },
    {
        "name": "predict_award",
        "description": (
            "Run the deterministic, explainable award projection engine. The stored "
            "2026 draft class is eligible for the 2026-27 ROY award."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "award_type": {"type": "string"},
                "season": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["award_type", "season"],
        },
    },
    {
        "name": "predict_standings",
        "description": "Run deterministic standings projections from stored roster data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "season": {"type": "string"},
                "conference": {"type": "string"},
            },
            "required": ["season"],
        },
    },
    {
        "name": "list_capabilities",
        "description": "Explain what grounded data and prediction tools are available.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search",
        "description": "Search stored player and team names.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


@dataclass
class ConversationContext:
    session_id: str
    last_entity_type: str | None = None
    last_entity_name: str | None = None


_CONVERSATIONS: dict[str, ConversationContext] = {}


def answer_message(
    session: Session,
    message: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    context = _context(session_id)
    settings = get_settings()
    if settings.anthropic_api_key:
        try:
            response = _answer_with_claude(session, message, context)
            session.commit()
            return response
        except (ImportError, RuntimeError, ValueError, KeyError, TypeError):
            session.rollback()
    response = _answer_locally(session, message, context)
    session.commit()
    return response


def _answer_with_claude(
    session: Session,
    message: str,
    context: ConversationContext,
) -> dict[str, Any]:
    anthropic = importlib.import_module("anthropic")
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": _message_with_context(message, context),
        }
    ]
    sources: list[dict[str, Any]] = []
    for _ in range(4):
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=900,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        blocks = list(response.content)
        tool_blocks = [block for block in blocks if getattr(block, "type", None) == "tool_use"]
        if not tool_blocks:
            text = "\n".join(
                str(getattr(block, "text", ""))
                for block in blocks
                if getattr(block, "type", None) == "text"
            ).strip()
            if not text:
                raise RuntimeError("Claude returned no grounded response.")
            return _response_payload(text, context, sources, "claude-tools")
        messages.append({"role": "assistant", "content": blocks})
        results: list[dict[str, Any]] = []
        for block in tool_blocks:
            tool_name = str(block.name)
            tool_input = dict(block.input)
            result = execute_tool(session, tool_name, tool_input)
            sources.append({"tool": tool_name, "arguments": tool_input})
            _update_context_from_tool(context, tool_name, tool_input)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                }
            )
        messages.append({"role": "user", "content": results})
    raise RuntimeError("Claude exceeded the grounded tool-call limit.")


def _answer_locally(
    session: Session,
    message: str,
    context: ConversationContext,
) -> dict[str, Any]:
    normalized = message.strip()
    lowered = normalized.lower()
    explicit_season = _extract_season(normalized)
    season = explicit_season or "2025-26"
    if any(phrase in lowered for phrase in ("what can you do", "help", "capabilities")):
        result = list_capabilities(session)
        text = (
            "I can search stored players and teams, compare season performance, explain "
            "analytics, and run transparent award or standings projections. "
            f"Available seasons: {', '.join(result['available_seasons']) or 'none'}."
        )
        return _response_payload(
            text,
            context,
            [{"tool": "list_capabilities", "arguments": {}}],
            "local-tools",
            result,
        )

    award = _award_from_message(lowered)
    if award == "ROY" and explicit_season is None:
        season = "2026-27"
    if award and any(word in lowered for word in ("predict", "favorite", "likely", "projection")):
        result = predict_award(session, award, season, limit=5)
        candidates = result["candidates"]
        if not candidates:
            text = f"No eligible {award} candidates are available from stored data."
        else:
            leader = candidates[0]
            drivers = leader["feature_attributions"][:3]
            why = ", ".join(
                f"{driver['feature'].replace('_', ' ')} {driver['raw_value']}"
                for driver in drivers
            )
            text = (
                f"{leader['name']} is the model's {award.replace('_', ' ')} favorite for "
                f"{season} at {leader['probability'] * 100:.1f}%. This is an estimate, "
                f"driven most by {why}. "
                f"The projection uses stored {result['source_season']} data."
            )
        return _response_payload(
            text,
            context,
            [{"tool": "predict_award", "arguments": {"award_type": award, "season": season}}],
            "local-tools",
            result,
        )

    if "standing" in lowered or "conference" in lowered:
        conference = "West" if "west" in lowered else "East" if "east" in lowered else None
        result = predict_league_standings(session, season, conference)
        leaders = result["teams"][:5]
        text = (
            f"Projected {conference or 'NBA'} leaders for {season}: "
            + ", ".join(
                f"{team['team_name']} ({team['projected_wins']}-{team['projected_losses']})"
                for team in leaders
            )
            + ". These are deterministic estimates from stored roster production, efficiency, "
            "plus-minus, continuity, and available health context."
        )
        return _response_payload(
            text,
            context,
            [
                {
                    "tool": "predict_standings",
                    "arguments": {"season": season, "conference": conference},
                }
            ],
            "local-tools",
            result,
        )

    player_names = _mentioned_players(session, normalized)
    if "compare" in lowered and len(player_names) >= 2:
        result = compare_players(session, player_names[:2], season)
        first = result["players"][0]
        second = result["players"][1]
        if not result["found"]:
            text = f"Missing stored data for: {', '.join(result['missing_players'])}."
        else:
            first_summary = first["summary"]
            second_summary = second["summary"]
            text = (
                f"In {season}, {first['player']['full_name']} averaged "
                f"{_display(first_summary, 'points_per_game')} PPG, "
                f"{_display(first_summary, 'rebounds_per_game')} RPG, and "
                f"{_display(first_summary, 'assists_per_game')} APG; "
                f"{second['player']['full_name']} averaged "
                f"{_display(second_summary, 'points_per_game')} PPG, "
                f"{_display(second_summary, 'rebounds_per_game')} RPG, and "
                f"{_display(second_summary, 'assists_per_game')} APG."
            )
        context.last_entity_type = "player"
        context.last_entity_name = player_names[0]
        return _response_payload(
            text,
            context,
            [
                {
                    "tool": "compare_players",
                    "arguments": {"names": player_names[:2], "season": season},
                }
            ],
            "local-tools",
            result,
        )

    if player_names:
        name = player_names[0]
        result = get_player(session, name, season)
        context.last_entity_type = "player"
        context.last_entity_name = name
        summary = result.get("summary")
        if summary is None:
            text = f"{name} is stored, but no {season} season summary is available."
        else:
            text = (
                f"{name} averaged {_display(summary, 'points_per_game')} points, "
                f"{_display(summary, 'rebounds_per_game')} rebounds, and "
                f"{_display(summary, 'assists_per_game')} assists in "
                f"{summary['games_played']} stored {season} games. "
                f"True shooting: {_percent(summary.get('true_shooting_percentage'))}."
            )
        return _response_payload(
            text,
            context,
            [{"tool": "get_player", "arguments": {"name": name, "season": season}}],
            "local-tools",
            result,
        )

    team_names = _mentioned_teams(session, normalized)
    if team_names:
        team_name = team_names[0]
        result = get_team(session, team_name, season)
        context.last_entity_type = "team"
        context.last_entity_name = team_name
        roster = result.get("roster", [])
        text = (
            f"{result['team']['name']} has {len(roster)} players with stored {season} "
            "season summaries. "
            + (
                f"Top rotation entries: {', '.join(player['full_name'] for player in roster[:5])}."
                if roster
                else "No roster summaries are stored for that season."
            )
        )
        return _response_payload(
            text,
            context,
            [{"tool": "get_team", "arguments": {"name_or_abbr": team_name, "season": season}}],
            "local-tools",
            result,
        )

    if context.last_entity_type == "player" and context.last_entity_name:
        result = get_player(session, context.last_entity_name, season)
        summary = result.get("summary")
        if summary is not None:
            text = (
                f"For {context.last_entity_name} in {season}: "
                f"{_display(summary, 'assists_per_game')} assists per game, "
                f"{_display(summary, 'minutes_per_game')} minutes per game, and "
                f"{_percent(summary.get('true_shooting_percentage'))} true shooting."
            )
            return _response_payload(
                text,
                context,
                [
                    {
                        "tool": "get_player",
                        "arguments": {"name": context.last_entity_name, "season": season},
                    }
                ],
                "local-tools",
                result,
            )

    text = (
        "I could not map that request to stored player, team, comparison, award, or standings "
        "data. Try naming a player or team, or ask what I can do."
    )
    return _response_payload(text, context, [], "local-tools")


def _response_payload(
    text: str,
    context: ConversationContext,
    sources: list[dict[str, Any]],
    mode: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "session_id": context.session_id,
        "message": text,
        "mode": mode,
        "sources": sources,
        "context": {
            "last_entity_type": context.last_entity_type,
            "last_entity_name": context.last_entity_name,
        },
        "data": data,
    }


def _context(session_id: str | None) -> ConversationContext:
    resolved = session_id or str(uuid4())
    if resolved not in _CONVERSATIONS:
        _CONVERSATIONS[resolved] = ConversationContext(session_id=resolved)
    return _CONVERSATIONS[resolved]


def _message_with_context(message: str, context: ConversationContext) -> str:
    if context.last_entity_name:
        return (
            f"Conversation context: last {context.last_entity_type} was "
            f"{context.last_entity_name}.\nUser: {message}"
        )
    return message


def _update_context_from_tool(
    context: ConversationContext,
    tool_name: str,
    arguments: dict[str, Any],
) -> None:
    if tool_name == "get_player":
        context.last_entity_type = "player"
        context.last_entity_name = str(arguments.get("name"))
    elif tool_name == "get_team":
        context.last_entity_type = "team"
        context.last_entity_name = str(arguments.get("name_or_abbr"))


def _mentioned_players(session: Session, message: str) -> list[str]:
    lowered = message.lower()
    names = [
        name
        for name in session.scalars(select(Player.full_name).order_by(Player.full_name))
        if name.lower() in lowered
    ]
    return sorted(names, key=lambda name: message.lower().find(name.lower()))


def _mentioned_teams(session: Session, message: str) -> list[str]:
    lowered = message.lower()
    matches: list[tuple[int, str]] = []
    for team in session.scalars(select(Team).order_by(Team.name)):
        variants = [team.name, team.abbreviation, f"{team.city} {team.name}"]
        for variant in variants:
            position = lowered.find(variant.lower())
            if position >= 0:
                matches.append((position, f"{team.city} {team.name}"))
                break
    return [name for _, name in sorted(matches)]


def _extract_season(message: str) -> str | None:
    match = re.search(r"\b(20\d{2}-\d{2})\b", message)
    return match.group(1) if match else None


def _award_from_message(message: str) -> str | None:
    mapping = {
        "sixth man": "SIXTH_MAN",
        "6moy": "SIXTH_MAN",
        "all defense": "ALL_DEFENSE_1",
        "all-defensive": "ALL_DEFENSE_1",
        "all nba": "ALL_NBA_1",
        "all-nba": "ALL_NBA_1",
        "all star": "ALL_STAR",
        "all-star": "ALL_STAR",
        "dpoy": "DPOY",
        "defensive player": "DPOY",
        "rookie": "ROY",
        "roy": "ROY",
        "most improved": "MIP",
        "mip": "MIP",
        "mvp": "MVP",
    }
    for phrase, award in mapping.items():
        if phrase in message:
            return award
    return None


def _display(summary: dict[str, Any] | None, key: str) -> str:
    if summary is None or summary.get(key) is None:
        return "unavailable"
    return f"{float(summary[key]):.1f}"


def _percent(value: Any) -> str:
    if value is None:
        return "unavailable"
    number = float(value)
    return f"{number * 100:.1f}%" if number <= 1 else f"{number:.1f}%"
