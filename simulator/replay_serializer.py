"""Structured replay serialization for the simulation viewer."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from simulator.game_manager import GameState


SCHEMA_VERSION = 1


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _card_id(card: Any) -> str:
    return str(getattr(card, "id", "") or "unknown")


def _card_name(card: Any) -> str:
    return str(getattr(card, "name", "") or _card_id(card))


def _normalize_color(color: Any) -> str:
    value = str(color or "").strip()
    if not value or value == "-":
        return "Neutral"
    return value


def serialize_card(
    card: Any,
    *,
    instance_id: Optional[str] = None,
    zone: Optional[str] = None,
    index: Optional[int] = None,
    rested: Optional[bool] = None,
) -> Dict[str, Any]:
    """Serialize a card-like object for display in replay zones."""
    card_type = str(getattr(card, "type", "") or "CARD")
    data: Dict[str, Any] = {
        "instanceId": instance_id or f"{zone or 'card'}:{index if index is not None else _card_id(card)}:{_card_id(card)}",
        "cardId": _card_id(card),
        "name": _card_name(card),
        "type": card_type,
        "color": _normalize_color(getattr(card, "color", "")),
        "level": getattr(card, "level", 0),
        "cost": getattr(card, "cost", 0),
        "ap": getattr(card, "ap", 0),
        "hp": getattr(card, "hp", 0),
        "traits": list(getattr(card, "traits", []) or []),
    }
    if rested is not None:
        data["rested"] = rested
    return data


def serialize_pilot(
    pilot: Any,
    *,
    instance_id: Optional[str] = None,
    paired_unit: Any = None,
) -> Optional[Dict[str, Any]]:
    if pilot is None:
        return None
    card = getattr(pilot, "card_data", pilot)
    data = serialize_card(card, instance_id=instance_id, zone="pilot")
    data.update(
        {
            "ownerId": getattr(pilot, "owner_id", None),
            "type": "PILOT",
            "pairedUnit": (
                {
                    "cardId": _card_id(getattr(paired_unit, "card_data", paired_unit)),
                    "name": _card_name(getattr(paired_unit, "card_data", paired_unit)),
                    "linked": bool(getattr(paired_unit, "is_linked", False)),
                }
                if paired_unit is not None
                else None
            ),
        }
    )
    return data


def serialize_unit(unit: Any, *, zone: str, index: int) -> Dict[str, Any]:
    """Serialize a UnitInstance including mutable stats and attached pilot."""
    card = getattr(unit, "card_data", unit)
    data = serialize_card(
        card,
        instance_id=f"p{getattr(unit, 'owner_id', 'x')}:{zone}:{index}:{_card_id(card)}",
        zone=zone,
        index=index,
        rested=bool(getattr(unit, "is_rested", False)),
    )
    data.update(
        {
            "ownerId": getattr(unit, "owner_id", None),
            "type": "UNIT",
            "ap": getattr(unit, "ap", getattr(card, "ap", 0)),
            "hp": getattr(unit, "hp", getattr(card, "hp", 0)),
            "currentHp": getattr(unit, "current_hp", getattr(card, "hp", 0)),
            "maxHp": getattr(unit, "hp", getattr(card, "hp", 0)),
            "turnDeployed": getattr(unit, "turn_deployed", None),
            "destroyed": bool(getattr(unit, "is_destroyed", False)),
            "linked": bool(getattr(unit, "is_linked", False)),
            "keywords": dict(getattr(unit, "keywords", {}) or {}),
            "attachedPilot": serialize_pilot(
                getattr(unit, "paired_pilot", None),
                instance_id=f"p{getattr(unit, 'owner_id', 'x')}:{zone}:{index}:pilot",
                paired_unit=unit,
            ),
        }
    )
    return data


def serialize_base(base: Any, *, player_id: int, index: int) -> Dict[str, Any]:
    card = getattr(base, "card_data", None)
    if card is not None:
        data = serialize_card(
            card,
            instance_id=f"p{player_id}:shield:base:{index}:{_card_id(card)}",
            zone="shield",
            index=index,
            rested=bool(getattr(base, "is_rested", False)),
        )
        data.update(
            {
                "type": "BASE",
                "ownerId": player_id,
                "ap": getattr(base, "ap", getattr(card, "ap", 0)),
                "hp": getattr(base, "hp", getattr(card, "hp", 0)),
                "currentHp": getattr(base, "current_hp", getattr(card, "hp", 0)),
                "maxHp": getattr(base, "hp", getattr(card, "hp", 0)),
                "turnDeployed": getattr(base, "turn_deployed", None),
                "isExBase": False,
            }
        )
        return data

    return {
        "instanceId": f"p{player_id}:shield:base:{index}:EX_BASE",
        "cardId": "EX_BASE",
        "name": str(getattr(base, "name", "EX Base")),
        "type": "BASE",
        "color": "Neutral",
        "ap": getattr(base, "ap", 0),
        "hp": getattr(base, "hp", 0),
        "currentHp": getattr(base, "current_hp", getattr(base, "hp", 0)),
        "maxHp": getattr(base, "hp", 0),
        "rested": bool(getattr(base, "is_rested", False)),
        "ownerId": player_id,
        "isExBase": True,
    }


def serialize_player(game_state: GameState, player_id: int) -> Dict[str, Any]:
    player = game_state.players[player_id]
    rested_resources = set(getattr(player, "_rested_resource_indices", set()) or set())
    shields = [
        serialize_card(card, instance_id=f"p{player_id}:shield:{idx}:{_card_id(card)}", zone="shield", index=idx)
        for idx, card in enumerate(player.shield_area)
    ]
    bases = [
        serialize_base(base, player_id=player_id, index=idx)
        for idx, base in enumerate(getattr(player, "bases", []) or [])
    ]

    return {
        "playerId": player_id,
        "hand": [
            serialize_card(card, instance_id=f"p{player_id}:hand:{idx}:{_card_id(card)}", zone="hand", index=idx)
            for idx, card in enumerate(player.hand)
        ],
        "deck": {
            "count": len(player.main_deck),
            "resourceDeckCount": len(player.resource_deck),
        },
        "trash": [
            serialize_card(card, instance_id=f"p{player_id}:trash:{idx}:{_card_id(card)}", zone="trash", index=idx)
            for idx, card in enumerate(player.trash)
        ],
        "shields": shields,
        "bases": bases,
        "resourceArea": [
            serialize_card(
                card,
                instance_id=f"p{player_id}:resource:{idx}:{_card_id(card)}",
                zone="resource",
                index=idx,
                rested=idx in rested_resources,
            )
            for idx, card in enumerate(player.resource_area)
        ],
        "field": [
            serialize_unit(unit, zone="field", index=idx)
            for idx, unit in enumerate(player.battle_area)
        ],
        "exiled": [
            serialize_card(card, instance_id=f"p{player_id}:exiled:{idx}:{_card_id(card)}", zone="exiled", index=idx)
            for idx, card in enumerate(player.banished)
        ],
        "exResources": player.ex_resources,
        "activeResources": player.get_active_resources(game_state),
        "totalResources": player.get_total_resources(),
    }


def serialize_game_state(game_state: GameState) -> Dict[str, Any]:
    """Serialize the complete visible game state for a replay frame."""
    pending_burst = getattr(game_state, "pending_burst_decision", None)
    return {
        "turn": game_state.turn_number,
        "phase": _enum_value(game_state.current_phase),
        "activePlayer": game_state.turn_player,
        "decisionPlayer": getattr(game_state, "decision_player_id", None),
        "inBattle": bool(getattr(game_state, "in_battle", False)),
        "battlePhase": _enum_value(getattr(game_state, "battle_phase", None)),
        "inActionStep": bool(getattr(game_state, "in_action_step", False)),
        "actionStepPriorityPlayer": getattr(game_state, "action_step_priority_player", None),
        "pendingBurst": (
            {
                "playerId": pending_burst.get("player_id"),
                "card": serialize_card(pending_burst.get("card"), zone="pendingBurst"),
            }
            if pending_burst
            else None
        ),
        "gameResult": _enum_value(game_state.game_result),
        "winner": game_state.winner,
        "players": {
            str(player_id): serialize_player(game_state, player_id)
            for player_id in sorted(game_state.players.keys())
        },
    }


def _unit_highlight(unit: Any, role: str) -> Optional[Dict[str, Any]]:
    if unit is None:
        return None
    card = getattr(unit, "card_data", unit)
    return {
        "role": role,
        "instanceId": getattr(unit, "_replay_instance_id", None),
        "cardId": _card_id(card),
        "ownerId": getattr(unit, "owner_id", None),
    }


def _attach_field_instance_ids(game_state: GameState) -> None:
    for player_id, player in game_state.players.items():
        for idx, unit in enumerate(getattr(player, "battle_area", []) or []):
            card = getattr(unit, "card_data", unit)
            setattr(unit, "_replay_instance_id", f"p{player_id}:field:{idx}:{_card_id(card)}")


def compute_frame_highlights(
    game_state: GameState,
    action: Any = None,
    summary: str = "",
) -> list[Dict[str, Any]]:
    """Derive board highlight roles for the current replay frame."""
    _attach_field_instance_ids(game_state)
    highlights: list[Dict[str, Any]] = []
    seen: set[tuple] = set()

    def add(highlight: Optional[Dict[str, Any]]) -> None:
        if not highlight:
            return
        key = (highlight["role"], highlight.get("instanceId"), highlight["cardId"], highlight.get("ownerId"))
        if key in seen:
            return
        seen.add(key)
        if highlight.get("instanceId") is None:
            highlight.pop("instanceId", None)
        highlights.append(highlight)

    if action is not None and hasattr(action, "action_type"):
        from simulator.random_agent import ActionType

        action_type = action.action_type
        if action_type in (ActionType.ATTACK_PLAYER, ActionType.ATTACK_UNIT):
            add(_unit_highlight(getattr(action, "unit", None), "attacking"))
            if action_type == ActionType.ATTACK_UNIT:
                add(_unit_highlight(getattr(action, "target", None), "defending"))
        elif action_type == ActionType.BLOCK:
            add(_unit_highlight(getattr(action, "unit", None), "blocking"))
        elif action_type in (
            ActionType.PLAY_UNIT,
            ActionType.PLAY_BASE,
            ActionType.PLAY_COMMAND,
            ActionType.PLAY_PILOT,
        ):
            card = getattr(action, "card", None)
            if card is not None:
                owner_id = getattr(game_state, "decision_player_id", None)
                if owner_id is None:
                    owner_id = game_state.turn_player
                add(
                    {
                        "role": "deploying",
                        "cardId": _card_id(card),
                        "ownerId": owner_id,
                    }
                )
            if action_type == ActionType.PLAY_PILOT:
                add(_unit_highlight(getattr(action, "target", None), "pairing"))

    text = summary or ""
    if text.startswith("Attack Step:"):
        add(_unit_highlight(getattr(game_state, "battle_attacker", None), "attacking"))
        add(_unit_highlight(getattr(game_state, "battle_defender", None), "defending"))
    elif text.startswith("Block Step:") and "blocks!" in text:
        add(_unit_highlight(getattr(game_state, "battle_defender", None), "blocking"))
    elif text.startswith("Damage Step:") and " vs " in text:
        add(_unit_highlight(getattr(game_state, "battle_attacker", None), "attacking"))
        add(_unit_highlight(getattr(game_state, "battle_defender", None), "defending"))

    return highlights


def serialize_action(action: Any) -> Optional[Dict[str, Any]]:
    if action is None:
        return None
    if hasattr(action, "to_dict"):
        return action.to_dict()
    return {"summary": str(action)}


class ReplayRecorder:
    """Collects replay frames and writes the final JSON artifact."""

    def __init__(
        self,
        *,
        seed: Optional[int] = None,
        deck_p0: Optional[str] = None,
        deck_p1: Optional[str] = None,
        text_log: Optional[str] = None,
    ) -> None:
        self.metadata = {
            "seed": seed,
            "decks": {"0": deck_p0, "1": deck_p1},
            "textLog": text_log,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
        }
        self.frames: list[Dict[str, Any]] = []

    def record(
        self,
        game_state: GameState,
        *,
        label: str,
        cause_type: str,
        summary: str,
        action: Any = None,
        result: Optional[str] = None,
        effects: Optional[list[Dict[str, Any]]] = None,
    ) -> None:
        highlights = compute_frame_highlights(game_state, action=action, summary=summary)
        move = serialize_action(action)
        state = serialize_game_state(game_state)
        state.update(
            {
                "id": len(self.frames),
                "label": label,
                "cause": {
                    "type": cause_type,
                    "summary": summary,
                    "move": move,
                    "action": move,
                    "result": result,
                    "effects": effects or [],
                    "highlights": highlights,
                },
            }
        )
        self.frames.append(state)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "metadata": self.metadata,
            "frames": self.frames,
        }

    def write_json(self, path: str) -> None:
        with open(path, "w") as replay_file:
            json.dump(self.to_dict(), replay_file, indent=2)
            replay_file.write("\n")
