"""LLM-backed discovery parser for ExBurst card text."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import re

from pydantic import BaseModel, Field, field_validator, model_validator

from simulator.ir_validator import validate_ir_effect_data
from simulator.ir_vocabulary import (
    SUPPORTED_ACTION_TYPES,
    SUPPORTED_CONDITION_TYPES,
    SUPPORTED_DURATIONS,
    SUPPORTED_SELECTOR_TYPES,
    SUPPORTED_TRIGGER_TYPES,
)


PROMPT_VERSION = "exburst-discovery-v1"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "deepseek/deepseek-chat-v3.1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

LLM_DURATION_ALIASES = {
    "IMMEDIATE": None,
    "INSTANT": None,
    "TURN": "THIS_TURN",
    "END_OF_TURN": "THIS_TURN",
    "UNTIL_END_OF_TURN": "THIS_TURN",
    "DURING_BATTLE": "THIS_BATTLE",
}

SELECTOR_ALIASES = {
    "BOTH_PLAYERS": "ALL_PLAYERS",
    "DECK": "SELF_DECK",
    "ENEMY_RESOURCE_AREA": "ENEMY_RESOURCE",
    "ENEMY_SHIELD": "ENEMY_SHIELDS",
    "ENEMY_SHIELDS": "OPPONENT_SHIELDS",
    "FRIENDLY_DECK": "SELF_DECK",
    "FRIENDLY_HAND": "SELF_HAND",
    "FRIENDLY_SHIELD": "FRIENDLY_SHIELDS",
    "FRIENDLY_SHIELDS": "SELF_SHIELDS",
    "OWN_DECK": "SELF_DECK",
    "OWN_HAND": "SELF_HAND",
    "OWN_SHIELDS": "SELF_SHIELDS",
    "SELECTED_TARGET": "SELECTED_CARD",
    "SELECTED_UNIT": "SELECTED_CARD",
}

CONDITION_ALIASES = {
    "CHECK_CARD_TRAIT": "CHECK_TRAIT",
    "CHECK_DAMAGED": "CHECK_DAMAGE",
    "CHECK_PAIRING": "CHECK_PAIR_STATUS",
    "HAS_KEYWORD": "CHECK_KEYWORD",
    "IS_PAIRED": "CHECK_PAIR_STATUS",
    "PAIR_STATUS": "CHECK_PAIR_STATUS",
    "TARGET_IS_PLAYER": "CHECK_TARGET",
}

ACTION_ALIASES = {
    "ACTIVATE_ACTION": "RESOLVE_COMMAND_EFFECT",
    "ACTIVATE_MAIN": "RESOLVE_COMMAND_EFFECT",
    "BOUNCE": "RETURN_TO_HAND",
    "RETURN_CARD_TO_HAND": "RETURN_TO_HAND",
    "RETURN_UNIT_TO_HAND": "RETURN_TO_HAND",
}

COMPARISON_ALIASES = {
    "EQ": "==",
    "EQUAL": "==",
    "GE": ">=",
    "GTE": ">=",
    "LE": "<=",
    "LTE": "<=",
    "GT": ">",
    "LT": "<",
}


TRIGGER_ALIASES = {
    "MAIN": "MAIN_PHASE",
    "ACTION": "ACTION_PHASE",
    "ACTIVATE MAIN": "ACTIVATE_MAIN",
    "ACTIVATE ACTION": "ACTIVATE_ACTION",
    "ACTIVATE-MAIN": "ACTIVATE_MAIN",
    "ACTIVATE-ACTION": "ACTIVATE_ACTION",
}


COMBINED_TRIGGER_ALIASES = {
    "MAIN_PHASE_ACTION_PHASE": ["MAIN_PHASE", "ACTION_PHASE"],
    "ACTION_PHASE_MAIN_PHASE": ["ACTION_PHASE", "MAIN_PHASE"],
    "ACTIVATE_MAIN_ACTIVATE_ACTION": ["ACTIVATE_MAIN", "ACTIVATE_ACTION"],
    "ACTIVATE_ACTION_ACTIVATE_MAIN": ["ACTIVATE_ACTION", "ACTIVATE_MAIN"],
}


def _normalize_trigger_name(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().upper()
    normalized = normalized.replace("【", "").replace("】", "")
    normalized = normalized.replace("･", "_").replace(" ", "_").replace("-", "_")
    normalized = normalized.removeprefix("TRIGGER_")
    return TRIGGER_ALIASES.get(normalized, normalized)


def _normalize_trigger_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [
            normalized
            for item in value
            for normalized in _normalize_trigger_values(item)
        ]
    if not isinstance(value, str):
        return [value]

    combined = COMBINED_TRIGGER_ALIASES.get(_normalize_trigger_name(value))
    if combined:
        return combined

    parts = re.split(r"\s*(?:,|/|\+|\band\b|\bor\b)\s*", value, flags=re.IGNORECASE)
    return [
        normalized
        for part in parts
        if (normalized := _normalize_trigger_name(part))
    ]


def _dedupe_preserve_order(values: List[Any]) -> List[Any]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


class GameEffect(BaseModel):
    raw_text: str = ""
    trigger: Optional[str] = None
    triggers: List[str] = Field(default_factory=list)
    action_type: Optional[str] = None
    target_selector: Optional[str] = None
    amount: Optional[int] = None
    duration: Optional[str] = None
    timing: Optional[str] = None
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    restrictions: List[str] = Field(default_factory=list)
    is_supported: bool = False
    unhandled_explanation: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_llm_timing_shapes(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        trigger_values = _normalize_trigger_values(normalized.get("triggers"))
        trigger_values.extend(_normalize_trigger_values(normalized.get("trigger")))
        phase_duration = _normalize_trigger_name(normalized.get("duration"))
        if phase_duration in {"MAIN_PHASE", "ACTION_PHASE"}:
            raw_text = str(normalized.get("raw_text") or "")
            normalized.pop("duration", None)
            if str(normalized.get("action_type") or "").strip().upper() in {
                "ACTIVATE_ACTION",
                "ACTIVATE_MAIN",
                "RESOLVE_COMMAND_EFFECT",
            } or re.search(r"Activate this card's\s+【(?:Action|Main)】", raw_text, flags=re.IGNORECASE):
                normalized.setdefault("timing", phase_duration)
            else:
                trigger_values.append(phase_duration)

        trigger_values = _dedupe_preserve_order(trigger_values)
        if trigger_values:
            normalized["triggers"] = trigger_values
            normalized["trigger"] = trigger_values[0]

        action_type = normalized.get("action_type")
        if isinstance(action_type, str) and _normalize_trigger_name(action_type) in SUPPORTED_TRIGGER_TYPES:
            raw_text = str(normalized.get("raw_text") or "")
            if re.search(r"\bpair that card\b", raw_text, flags=re.IGNORECASE):
                normalized["action_type"] = None
                normalized["actions"] = []
                normalized["is_supported"] = False
                normalized["unhandled_explanation"] = (
                    "Requires an action to pair a card from trash with a Unit."
                )

        return normalized

    @field_validator("trigger")
    @classmethod
    def validate_trigger(cls, value: Optional[str]) -> Optional[str]:
        value = _normalize_trigger_name(value)
        if value is not None and value not in SUPPORTED_TRIGGER_TYPES:
            raise ValueError(f"Unsupported trigger vocabulary: {value}")
        return value

    @field_validator("triggers", mode="before")
    @classmethod
    def normalize_triggers(cls, value: Any) -> Any:
        return _normalize_trigger_values(value)

    @field_validator("triggers")
    @classmethod
    def validate_triggers(cls, value: List[str]) -> List[str]:
        for trigger in value:
            if trigger not in SUPPORTED_TRIGGER_TYPES:
                raise ValueError(f"Unsupported trigger vocabulary: {trigger}")
        return value

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = _normalize_action_type(value)
        if value is not None and value not in SUPPORTED_ACTION_TYPES:
            raise ValueError(f"Unsupported action vocabulary: {value}")
        return value

    @field_validator("target_selector")
    @classmethod
    def validate_target_selector(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = _normalize_selector(value)
        if value is not None and value not in SUPPORTED_SELECTOR_TYPES:
            raise ValueError(f"Unsupported selector vocabulary: {value}")
        return value

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SUPPORTED_DURATIONS:
            raise ValueError(f"Unsupported duration vocabulary: {value}")
        return value

    @field_validator("duration", mode="before")
    @classmethod
    def normalize_duration(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_duration(value)

    @field_validator("timing", mode="before")
    @classmethod
    def normalize_timing(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_trigger_name(value)

    @field_validator("actions", mode="before")
    @classmethod
    def normalize_action_durations(cls, value: Any) -> Any:
        return _normalize_llm_action_aliases(value)

    @field_validator("conditions", mode="before")
    @classmethod
    def normalize_condition_aliases(cls, value: Any) -> Any:
        return _normalize_llm_condition_aliases(value)

    @model_validator(mode="after")
    def normalize_keyword_grants(self) -> "GameEffect":
        self.actions = [
            _normalize_keyword_grant_action(_canonicalize_action_shape(action), self.raw_text)
            for action in self.actions
        ]
        return self


class ParsedCard(BaseModel):
    name: str
    card_type: str
    cost: Optional[int] = None
    color: str = "-"
    effects: List[GameEffect] = Field(default_factory=list)

    @field_validator("card_type")
    @classmethod
    def normalize_card_type(cls, value: str) -> str:
        normalized = value.upper().replace(" ", "_")
        if normalized == "UNIT_TOKEN":
            normalized = "UNIT TOKEN"
        allowed = {"UNIT", "PILOT", "COMMAND", "BASE", "RESOURCE", "UNIT TOKEN"}
        if normalized not in allowed:
            raise ValueError(f"Unsupported card type: {value}")
        return normalized


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    model: str = DEFAULT_OPENROUTER_MODEL
    base_url: str = DEFAULT_OPENROUTER_BASE_URL
    prompt_version: str = PROMPT_VERSION
    timeout_seconds: float = 60.0
    max_retries: int = 1


def load_openrouter_config(credentials_path: str | Path | None = None) -> OpenRouterConfig:
    api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPEN_ROUTER_API_KEY")
        or _read_credentials_api_key(credentials_path)
    )
    if not api_key:
        raise RuntimeError("OpenRouter API key not found in OPENROUTER_API_KEY or .credentials")
    return OpenRouterConfig(
        api_key=api_key,
        model=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
        base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
        timeout_seconds=_read_float_env("OPENROUTER_TIMEOUT_SECONDS", 60.0),
        max_retries=_read_int_env("OPENROUTER_MAX_RETRIES", 1),
    )


def build_instructor_client(config: OpenRouterConfig | None = None) -> Any:
    config = config or load_openrouter_config()
    try:
        import instructor
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install instructor and openai to use LLM parsing") from exc

    openai_client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
    )
    return instructor.from_openai(openai_client, mode=instructor.Mode.JSON)


def screen_card(
    card_text: str,
    *,
    client: Any | None = None,
    config: OpenRouterConfig | None = None,
) -> ParsedCard:
    config = config or load_openrouter_config()
    client = client or build_instructor_client(config)
    return client.chat.completions.create(
        model=config.model,
        response_model=ParsedCard,
        max_retries=config.max_retries,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": card_text},
        ],
    )


def parse_normalized_card_offline(card: Dict[str, Any]) -> ParsedCard:
    effects = [_parse_effect_line_offline(line) for line in card.get("Effect", [])]
    return ParsedCard(
        name=str(card.get("Name") or ""),
        card_type=str(card.get("Type") or "UNIT"),
        cost=card.get("Cost"),
        color=str(card.get("Color") or "-"),
        effects=effects,
    )


def parsed_card_to_ir(
    card_id: str,
    parsed_card: ParsedCard,
    *,
    raw_effects: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw_effects = raw_effects or []
    authoritative_entries = _known_supported_ir_entries(card_id, raw_effects)
    handled_raw_text = {_normalize_effect_text(entry["metadata"]["raw_text"]) for entry in authoritative_entries}
    llm_entries = [
        _parsed_effect_to_entry(card_id, parsed_effect, index)
        for index, parsed_effect in enumerate(parsed_card.effects, start=1)
        if _normalize_effect_text(parsed_effect.raw_text) not in handled_raw_text
    ]
    entries = _renumber_entries(card_id, [*authoritative_entries, *llm_entries])

    effect_entries = [entry for entry in entries if entry["effect_type"] != "CONTINUOUS"]
    continuous_effects = [entry for entry in entries if entry["effect_type"] == "CONTINUOUS"]

    result: Dict[str, Any] = {
        "card_id": card_id,
        "effects": effect_entries,
        "continuous_effects": continuous_effects,
        "metadata": {
            "original_text": "; ".join(raw_effects),
            "parsing_version": PROMPT_VERSION,
            "card_type": parsed_card.card_type,
            "llm_model": metadata.get("llm_model") if metadata else None,
            "parser_source": metadata.get("parser_source", "offline") if metadata else "offline",
        },
    }
    report = validate_ir_effect_data(result)
    result["metadata"]["support_status"] = report.support_status
    result["metadata"]["validation_issues"] = [
        {
            "path": issue.path,
            "kind": issue.kind,
            "value": issue.value,
            "message": issue.message,
        }
        for issue in report.issues
    ]
    return result


def _parsed_effect_to_entry(card_id: str, parsed_effect: GameEffect, index: int) -> Dict[str, Any]:
    if _is_pilot_metadata_text(parsed_effect.raw_text):
        return _pilot_metadata_entry(card_id, parsed_effect.raw_text, index)

    triggers = parsed_effect.triggers or ([parsed_effect.trigger] if parsed_effect.trigger else [])
    entry = {
        "effect_id": f"{card_id}-E{index}",
        "effect_type": _effect_type_for(parsed_effect),
        "triggers": triggers,
        "conditions": parsed_effect.conditions,
        "actions": _ir_actions_for(parsed_effect),
        "is_supported": parsed_effect.is_supported,
        "unhandled_explanation": parsed_effect.unhandled_explanation,
        "metadata": {"raw_text": parsed_effect.raw_text, "source": "llm"},
    }
    if parsed_effect.restrictions:
        entry["restrictions"] = parsed_effect.restrictions
    return entry


def _known_supported_ir_entries(card_id: str, raw_effects: List[str]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for line in raw_effects:
        if _is_pilot_metadata_text(line):
            entries.append(_pilot_metadata_entry(card_id, line, 0))
            continue
        continuous = _parse_known_continuous_keyword(card_id, line)
        if continuous:
            entries.append(continuous)
            continue
        triggered = _parse_known_triggered_draw(card_id, line)
        if triggered:
            entries.append(triggered)
    return entries


def _parse_known_continuous_keyword(card_id: str, text: str) -> Optional[Dict[str, Any]]:
    gated = _parse_gated_keyword_modifier(text)
    if gated:
        conditions, modifier = gated
        return {
            "effect_id": f"{card_id}-E0",
            "effect_type": "CONTINUOUS",
            "description": text,
            "conditions": conditions,
            "modifiers": [modifier],
            "is_supported": True,
            "unhandled_explanation": "",
            "metadata": {"raw_text": text, "source": "known_pattern"},
        }

    standalone = _parse_standalone_keyword_modifier(text)
    if standalone:
        return {
            "effect_id": f"{card_id}-E0",
            "effect_type": "CONTINUOUS",
            "description": text,
            "modifiers": [standalone],
            "is_supported": True,
            "unhandled_explanation": "",
            "metadata": {"raw_text": text, "source": "known_pattern"},
        }

    match = re.search(
        r"^All your \(([^)]+)\) Units gain <([A-Za-z-]+)(?:\s+(\d+))?>\.",
        text,
    )
    if not match:
        return None
    trait = match.group(1).strip()
    keyword = match.group(2).strip().upper().replace("-", "_")
    value = int(match.group(3)) if match.group(3) else None
    return {
        "effect_id": f"{card_id}-E0",
        "effect_type": "CONTINUOUS",
        "description": text,
        "modifiers": [
            {
                "type": "GRANT_KEYWORD",
                "target": {
                    "selector": "FRIENDLY_UNIT",
                    "filters": {"traits": [trait]},
                },
                "keyword": keyword,
                "value": value,
            }
        ],
        "is_supported": True,
        "unhandled_explanation": "",
        "metadata": {"raw_text": text, "source": "known_pattern"},
    }


def _parse_known_triggered_draw(card_id: str, text: str) -> Optional[Dict[str, Any]]:
    match = re.search(
        r"【When Paired】If you have (\d+) or more other Units in play, draw (\d+)\.",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return {
        "effect_id": f"{card_id}-E0",
        "effect_type": "TRIGGERED",
        "triggers": ["ON_PAIRED"],
        "conditions": [
            {
                "type": "COUNT_CARDS",
                "zone": "BATTLE_AREA",
                "owner": "SELF",
                "card_type": "UNIT",
                "exclude_self": True,
                "operator": ">=",
                "value": int(match.group(1)),
            }
        ],
        "actions": [{"type": "DRAW", "target": "SELF", "amount": int(match.group(2))}],
        "is_supported": True,
        "unhandled_explanation": "",
        "metadata": {"raw_text": text, "source": "known_pattern"},
    }


def _renumber_entries(card_id: str, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {**entry, "effect_id": f"{card_id}-E{index}"}
        for index, entry in enumerate(entries, start=1)
    ]


def _normalize_effect_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_duration(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().upper()
    return LLM_DURATION_ALIASES.get(normalized, normalized)


def _normalize_action_type(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().upper()
    return ACTION_ALIASES.get(normalized, normalized)


def _normalize_llm_action_aliases(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize_llm_action_aliases(item) for item in value]
    if isinstance(value, dict):
        normalized = {
            key: (
                _normalize_duration(item)
                if key == "duration"
                else _normalize_target_spec(item)
                if key == "target" and isinstance(item, dict)
                else _normalize_filters(item)
                if key == "filters"
                else _normalize_llm_action_aliases(item)
            )
            for key, item in value.items()
        }
        if "type" not in normalized and "action_type" in normalized:
            normalized["type"] = normalized.pop("action_type")
        if not normalized.get("type"):
            inferred_action_type = _infer_action_type_from_fields(normalized)
            if inferred_action_type:
                normalized["type"] = inferred_action_type
        if normalized.get("type"):
            original_type = str(normalized["type"]).strip().upper()
            normalized["type"] = _normalize_action_type(original_type)
            if normalized["type"] == "RESOLVE_COMMAND_EFFECT":
                if "timing" not in normalized:
                    normalized["timing"] = "ACTION_PHASE" if original_type.endswith("ACTION") else "MAIN_PHASE"
            elif normalized["type"] == "MODIFY_COST":
                normalized.setdefault("scope", "PLAY")
        if "target" not in normalized and "target_selector" in normalized:
            normalized["target"] = {"selector": _normalize_selector(normalized.pop("target_selector"))}
        if isinstance(normalized.get("target"), dict):
            normalized["target"] = _normalize_target_spec(normalized["target"])
        if "selector" in normalized:
            normalized["selector"] = _normalize_selector(normalized["selector"])
        if "filters" in normalized:
            normalized["filters"] = _normalize_filters(normalized["filters"])
        return _canonicalize_action_shape(normalized)
    return value


def _normalize_llm_condition_aliases(value: Any) -> Any:
    if isinstance(value, list):
        return [
            normalized
            for item in value
            if (normalized := _normalize_llm_condition_aliases(item)) is not None
        ]
    if not isinstance(value, dict):
        return value

    normalized = {
        key: _normalize_target_spec(item) if key == "target" and isinstance(item, dict) else item
        for key, item in value.items()
    }
    if not normalized.get("type") and normalized.get("condition_type"):
        normalized["type"] = normalized.pop("condition_type")

    condition_type = str(normalized.get("type") or "").strip().upper()
    if not condition_type:
        condition_type = _infer_condition_type_from_fields(normalized)
    if not condition_type and not any(value not in (None, "", [], {}) for value in normalized.values()):
        return None
    normalized["type"] = CONDITION_ALIASES.get(condition_type, condition_type)

    if "selector" in normalized and "target" not in normalized:
        normalized["target"] = {"selector": _normalize_selector(normalized.pop("selector"))}
    if "target_selector" in normalized and "target" not in normalized:
        normalized["target"] = {"selector": _normalize_selector(normalized.pop("target_selector"))}
    elif "selector" in normalized:
        normalized["selector"] = _normalize_selector(normalized["selector"])

    if "trait" in normalized and "traits" not in normalized:
        normalized["traits"] = [normalized.pop("trait")]
    if "required_traits" in normalized and "traits" not in normalized:
        normalized["traits"] = normalized.pop("required_traits")
    if "keyword" in normalized:
        normalized["keyword"] = _normalize_keyword_name(normalized["keyword"])
    if "color" in normalized:
        normalized["color"] = str(normalized["color"]).title()
    if normalized.get("type") == "CHECK_PAIR_STATUS":
        normalized.setdefault("target", {"selector": "SELF"})
        state = str(normalized.get("state") or normalized.get("status") or "PAIRED").upper()
        normalized["state"] = "LINKED" if state == "LINKED" else "PAIRED"
    if normalized.get("type") == "CHECK_DAMAGE":
        normalized.setdefault("target", {"selector": "SELF"})
        normalized.setdefault("operator", ">")
        normalized.setdefault("value", 0)

    if "comparison" in normalized and "operator" not in normalized:
        normalized["operator"] = _normalize_comparison(normalized.pop("comparison"))
    if "operator" in normalized:
        normalized["operator"] = _normalize_comparison(normalized["operator"])

    zone = str(normalized.get("zone") or "")
    if zone.startswith("SELF_"):
        normalized.setdefault("owner", "SELF")
        normalized["zone"] = zone.removeprefix("SELF_")
    elif zone.startswith("OPPONENT_"):
        normalized.setdefault("owner", "OPPONENT")
        normalized["zone"] = zone.removeprefix("OPPONENT_")

    if normalized.get("type") == "CHECK_TURN" and "turn_owner" not in normalized:
        turn_value = str(normalized.get("value") or normalized.get("owner") or "").upper()
        if turn_value in {"YOUR", "SELF", "YOU"}:
            normalized["turn_owner"] = "SELF"
        elif turn_value in {"OPPONENT", "OPPONENTS", "ENEMY"}:
            normalized["turn_owner"] = "OPPONENT"

    return normalized


def _normalize_keyword_grant_action(action: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    normalized = _canonicalize_action_shape(action)
    keyword = _extract_keyword_grant(raw_text)
    action_type = str(normalized.get("type") or "")
    stat_type = str(normalized.get("stat_type") or "").upper()
    stat = str(normalized.get("stat") or stat_type).upper()

    if not action_type and keyword:
        normalized["type"] = "GRANT_KEYWORD"
        action_type = "GRANT_KEYWORD"
    elif not action_type and re.search(r"\b(AP|HP)\s*[+-]\s*\d+", raw_text, flags=re.IGNORECASE):
        normalized["type"] = "MODIFY_STAT"
        action_type = "MODIFY_STAT"
    elif not action_type and re.search(r"\breturn\b.+\bhand\b", raw_text, flags=re.IGNORECASE):
        normalized["type"] = "RETURN_TO_HAND"
        action_type = "RETURN_TO_HAND"

    if action_type == "MODIFY_STAT" and (
        stat in {"COST", "LEVEL", "LV"} or re.search(r"\b(cost|lv\.?|level)\s*[+-]", raw_text, flags=re.IGNORECASE)
    ):
        normalized["type"] = "MODIFY_COST"
        normalized["stat"] = "LEVEL" if stat in {"LEVEL", "LV"} else "COST"

    if action_type == "MODIFY_STAT" and stat not in {"AP", "HP"} and keyword:
        normalized["type"] = "GRANT_KEYWORD"
        normalized.pop("stat", None)
        normalized.pop("modification", None)
        normalized.pop("stat_type", None)

    if normalized.get("type") == "GRANT_KEYWORD":
        if not normalized.get("keyword"):
            normalized["keyword"] = stat_type or (keyword[0] if keyword else None)
        if normalized.get("keyword"):
            normalized["keyword"] = _normalize_keyword_name(normalized["keyword"])
        if "value" not in normalized:
            normalized["value"] = normalized.get("amount")
        if normalized.get("value") is None and keyword:
            normalized["value"] = keyword[1]
        if normalized.get("keyword") in {"BLOCKER", "FIRST_STRIKE", "HIGH_MANEUVER", "SUPPRESSION"}:
            normalized.pop("value", None)
        normalized.pop("amount", None)
        normalized.pop("stat_type", None)
    elif normalized.get("type") == "MODIFY_STAT":
        printed_stat_modifier = _printed_stat_modifier(raw_text, normalized.get("stat"))
        if printed_stat_modifier:
            normalized["stat"], normalized["modification"] = printed_stat_modifier
        if not normalized.get("stat") and stat_type in {"AP", "HP"}:
            normalized["stat"] = stat_type
            normalized.pop("stat_type", None)
        if not normalized.get("stat"):
            inferred_stat = _infer_stat_from_text(raw_text)
            if inferred_stat:
                normalized["stat"] = inferred_stat
        if "modification" not in normalized and isinstance(normalized.get("amount"), int):
            amount = normalized.pop("amount")
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        if "modification" not in normalized and isinstance(normalized.get("value"), int):
            amount = normalized.pop("value")
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        if isinstance(normalized.get("modification"), int):
            amount = normalized["modification"]
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        if "modification" in normalized and "modification_type" in normalized:
            mod_type = str(normalized.pop("modification_type")).upper()
            if mod_type in {"REDUCE", "SUBTRACT"} and str(normalized["modification"]).lstrip("+-").isdigit():
                normalized["modification"] = f"-{str(normalized['modification']).lstrip('+-')}"
        if normalized.get("stat"):
            normalized["stat"] = str(normalized["stat"]).upper()
    elif normalized.get("type") == "MODIFY_COST":
        if "modification" not in normalized and isinstance(normalized.get("amount"), int):
            amount = normalized.pop("amount")
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        if isinstance(normalized.get("modification"), int):
            amount = normalized["modification"]
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        if "modification" in normalized and "modification_type" in normalized:
            mod_type = str(normalized.pop("modification_type")).upper()
            if mod_type in {"REDUCE", "SUBTRACT"} and str(normalized["modification"]).lstrip("+-").isdigit():
                normalized["modification"] = f"-{str(normalized['modification']).lstrip('+-')}"
        normalized.setdefault("scope", "PLAY")
    elif normalized.get("type") == "RESOLVE_COMMAND_EFFECT":
        if re.search(r"Activate this card's\s+【Action】", raw_text, flags=re.IGNORECASE):
            normalized["timing"] = "ACTION_PHASE"
        elif re.search(r"Activate this card's\s+【Main】", raw_text, flags=re.IGNORECASE):
            normalized["timing"] = "MAIN_PHASE"
        elif not normalized.get("timing"):
            normalized["timing"] = "ACTION_PHASE" if "【Action】" in raw_text else "MAIN_PHASE"

    return normalized


def _canonicalize_action_shape(action: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy LLM action fields into the runtime target/action shape."""
    normalized = dict(action)
    if "type" not in normalized and "action_type" in normalized:
        normalized["type"] = normalized.pop("action_type")
    if normalized.get("type"):
        normalized["type"] = _normalize_action_type(normalized["type"])

    target = normalized.get("target")
    if isinstance(target, str):
        target = {"selector": _normalize_selector(target)}
    elif isinstance(target, dict):
        target = _normalize_target_spec(target)
    elif "target_selector" in normalized:
        target = {"selector": _normalize_selector(normalized.pop("target_selector"))}
    elif "selector" in normalized:
        target = {"selector": _normalize_selector(normalized.pop("selector"))}

    if isinstance(target, dict):
        if "target_selector" in normalized and "selector" not in target:
            target["selector"] = _normalize_selector(normalized.pop("target_selector"))
        if "selector" in normalized and "selector" not in target:
            target["selector"] = _normalize_selector(normalized.pop("selector"))
        if "filters" in normalized:
            merged_filters = _merge_filter_specs(target.get("filters", {}), normalized.pop("filters"))
            if merged_filters:
                target["filters"] = merged_filters
        normalized["target"] = _normalize_target_spec(target)

    if normalized.get("type") == "MODIFY_STAT":
        stat = normalized.get("stat") or normalized.get("stat_type")
        if stat:
            normalized["stat"] = str(stat).upper()
            normalized.pop("stat_type", None)
        if isinstance(normalized.get("modification"), int):
            amount = normalized["modification"]
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
    elif normalized.get("type") == "MODIFY_COST":
        if isinstance(normalized.get("modification"), int):
            amount = normalized["modification"]
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        normalized.setdefault("scope", "PLAY")

    return normalized


def _merge_filter_specs(*filter_specs: Any) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for filters in filter_specs:
        normalized = _filters_to_dict(filters)
        for key, value in normalized.items():
            merged[key] = value
    return merged


def _filters_to_dict(filters: Any) -> Dict[str, Any]:
    if not filters:
        return {}
    if isinstance(filters, list):
        merged: Dict[str, Any] = {}
        for item in filters:
            merged.update(_filters_to_dict(item))
        return merged
    if not isinstance(filters, dict):
        return {}

    normalized = _normalize_filters(filters)
    stat = str(normalized.get("stat") or normalized.get("stat_type") or "").upper()
    if stat in {"LEVEL", "LV", "AP", "HP"} and "operator" in normalized and "value" in normalized:
        key = "level" if stat in {"LEVEL", "LV"} else stat.lower()
        return {key: {"operator": normalized["operator"], "value": normalized["value"]}}
    return normalized


def _printed_stat_modifier(raw_text: str, requested_stat: Any = None) -> Optional[tuple[str, str]]:
    matches = [
        (match.group(1).upper(), f"{match.group(2)}{match.group(3)}")
        for match in re.finditer(r"\b(AP|HP)\s*([+-])\s*(\d+)", raw_text, flags=re.IGNORECASE)
    ]
    if not matches:
        return None
    stat = str(requested_stat or "").upper()
    if stat:
        for match_stat, modification in matches:
            if match_stat == stat:
                return match_stat, modification
    return matches[0] if len(matches) == 1 else None


def _extract_keyword_grant(text: str) -> Optional[tuple[str, Optional[int]]]:
    match = re.search(r"(?:gain|gains)\s*[【<]([A-Za-z -]+)(?:\s+(\d+))?[】>]", text, re.IGNORECASE)
    if not match:
        return None
    return (
        _normalize_keyword_name(match.group(1)),
        int(match.group(2)) if match.group(2) else None,
    )


def _parse_standalone_keyword_modifier(text: str) -> Optional[Dict[str, Any]]:
    stripped = text.strip()
    match = re.match(r"^[<\[]([A-Za-z -]+)(?:\s+(\d+))?[>\]]", stripped)
    if not match:
        return None
    keyword = _normalize_keyword_name(match.group(1))
    value = int(match.group(2)) if match.group(2) else None
    return {
        "type": "GRANT_KEYWORD",
        "target": {"selector": "SELF"},
        "keyword": keyword,
        "value": value,
    }


def _parse_gated_keyword_modifier(text: str) -> Optional[tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    if "【During Pair】" not in text and "【During Link】" not in text:
        return None
    keyword = _extract_keyword_grant(text)
    if not keyword:
        return None
    state = "LINKED" if "【During Link】" in text else "PAIRED"
    return (
        [{"type": "CHECK_CARD_STATE", "target": {"selector": "SELF"}, "state": state}],
        {
            "type": "GRANT_KEYWORD",
            "target": {"selector": "SELF"},
            "keyword": keyword[0],
            "value": keyword[1],
        },
    )


def _is_pilot_metadata_text(text: str) -> bool:
    normalized = text.strip()
    if normalized.startswith("【Pilot】"):
        return True
    return bool(re.search(r"\bAP[+-]\d+\b|\bHP[+-]\d+\b", normalized)) and "Pilot" in normalized


def _pilot_metadata_entry(card_id: str, text: str, index: int) -> Dict[str, Any]:
    ap_match = re.search(r"\bAP([+-]\d+)", text, flags=re.IGNORECASE)
    hp_match = re.search(r"\bHP([+-]\d+)", text, flags=re.IGNORECASE)
    traits = re.findall(r"\(([^)]+)\)", text)
    return {
        "effect_id": f"{card_id}-E{index}",
        "effect_type": "PILOT_ABILITY",
        "triggers": [],
        "conditions": [],
        "actions": [],
        "pilot_stats": {
            "ap": int(ap_match.group(1)) if ap_match else 0,
            "hp": int(hp_match.group(1)) if hp_match else 0,
            "traits": traits,
        },
        "is_supported": True,
        "unhandled_explanation": "",
        "metadata": {"raw_text": text, "source": "pilot_metadata"},
    }


def _infer_action_type_from_fields(action: Dict[str, Any]) -> Optional[str]:
    if "look_at" in action or "look_count" in action:
        return "LOOK_AT_DECK"
    if action.get("return_to") in {"HAND", "OWNER_HAND", "OWNERS_HAND"} or action.get("destination") in {"HAND", "OWNER_HAND"}:
        return "RETURN_TO_HAND"
    if "damage_reduction" in action or "reduce_damage_by" in action:
        return "REDUCE_DAMAGE"
    if action.get("return_to") in {"TOP", "BOTTOM"} or "return_remaining_to" in action:
        return "RETURN_LOOKED_TO_BOTTOM"
    if action.get("select_from") == "LOOKED_AT" or "max_select" in action:
        return "SELECT_LOOKED_AT_CARD"
    return None


def _infer_condition_type_from_fields(condition: Dict[str, Any]) -> str:
    if condition.get("condition_type"):
        return str(condition["condition_type"])
    if "attacking_player" in condition or "target_type" in condition or "attack_target" in condition:
        return "CHECK_TARGET"
    if "paired" in condition or "pair_status" in condition:
        return "CHECK_PAIR_STATUS"
    if "trait" in condition or "traits" in condition or "required_traits" in condition:
        return "CHECK_TRAIT"
    if "color" in condition:
        return "CHECK_COLOR"
    if "keyword" in condition or "has_keyword" in condition:
        return "CHECK_KEYWORD"
    if "damaged" in condition or "damage" in condition:
        return "CHECK_DAMAGE"
    return str(condition.get("type") or "")


def _normalize_target_spec(target: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(target)
    if "selector" in normalized:
        normalized["selector"] = _normalize_selector(normalized["selector"])
    if "filters" in normalized and isinstance(normalized["filters"], dict):
        normalized["filters"] = _normalize_filters(normalized["filters"])
    return normalized


def _normalize_selector(selector: Any) -> Any:
    if not isinstance(selector, str):
        return selector
    normalized = selector.strip().upper()
    return SELECTOR_ALIASES.get(normalized, normalized)


def _normalize_filters(filters: Any) -> Any:
    if isinstance(filters, list):
        return [_normalize_filters(item) for item in filters]
    if not isinstance(filters, dict):
        return filters
    normalized = dict(filters)
    if "type" in normalized and "card_type" not in normalized:
        normalized["card_type"] = normalized.pop("type")
    if "trait" in normalized and "traits" not in normalized:
        normalized["traits"] = [normalized.pop("trait")]
    if normalized.pop("is_active", False):
        normalized["state"] = "ACTIVE"
    if "state" in normalized and isinstance(normalized["state"], str):
        normalized["state"] = normalized["state"].upper()
    if "has_keyword" in normalized:
        normalized["has_keyword"] = _normalize_keyword_name(normalized["has_keyword"]).lower()
    if "keyword" in normalized and "has_keyword" not in normalized:
        normalized["has_keyword"] = _normalize_keyword_name(normalized.pop("keyword")).lower()
    else:
        normalized.pop("keyword", None)
    if normalized.get("card_type") == "CHECK_TRAIT" and "value" in normalized:
        normalized["traits"] = [normalized.pop("value")]
        normalized.pop("card_type", None)
    if "card_state" in normalized and "state" not in normalized:
        normalized["state"] = str(normalized.pop("card_state")).upper()
    else:
        normalized.pop("card_state", None)
    if "level_operator" in normalized and "level" in normalized and not isinstance(normalized["level"], dict):
        normalized["level"] = {"operator": normalized.pop("level_operator"), "value": normalized["level"]}
    normalized.pop("level_operator", None)
    for unsupported_key in (
        "amount",
        "can_target_player",
        "condition",
        "conditions",
        "count",
        "limit",
        "most_units_owner",
        "owner",
        "paired_with_pilot_trait",
        "quantity",
        "sort_by",
        "sort_order",
        "stat_filters",
        "target",
        "value",
    ):
        normalized.pop(unsupported_key, None)
    stat = str(normalized.get("stat") or normalized.get("stat_type") or "").upper()
    if stat in {"LEVEL", "LV", "AP", "HP"} and "operator" in normalized and "value" in normalized:
        key = "level" if stat in {"LEVEL", "LV"} else stat.lower()
        return {key: {"operator": normalized["operator"], "value": normalized["value"]}}
    for key in ("level", "ap", "hp"):
        value_key = f"{key}_value"
        if value_key in normalized and isinstance(normalized.get(key), str) and normalized[key] in {"<=", ">=", "==", "!=", "<", ">"}:
            normalized[key] = {"operator": normalized.pop(key), "value": normalized.pop(value_key)}
        elif value_key in normalized and "operator" in normalized:
            normalized[key] = {"operator": normalized.pop("operator"), "value": normalized.pop(value_key)}
        elif key in normalized and "operator" in normalized and not isinstance(normalized[key], dict):
            normalized[key] = {"operator": normalized.pop("operator"), "value": normalized[key]}
    return normalized


def _normalize_keyword_name(keyword: Any) -> str:
    return str(keyword).strip().upper().replace("-", "_").replace(" ", "_")


def _normalize_comparison(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().upper()
    return COMPARISON_ALIASES.get(normalized, value)


def _infer_stat_from_text(text: str) -> Optional[str]:
    match = re.search(r"\b(AP|HP)\s*[+-]\s*\d+", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"gets\s+(AP|HP)", text, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def _parse_effect_line_offline(text: str) -> GameEffect:
    triggers = _extract_triggers(text)
    trigger = triggers[0] if triggers else None
    action = _extract_simple_action(text)
    conditions = _extract_supported_conditions(text)
    unsupported = _unsupported_reason(text, trigger, action, conditions)
    return GameEffect(
        raw_text=text,
        trigger=trigger,
        triggers=triggers,
        action_type=action.get("type") if action else None,
        target_selector=_target_selector(action.get("target")) if action else None,
        amount=action.get("amount") if action else None,
        duration=action.get("duration") if action else None,
        conditions=conditions,
        actions=[action] if action else [],
        restrictions=["ONCE_PER_TURN"] if "Once per Turn" in text else [],
        is_supported=unsupported is None,
        unhandled_explanation=unsupported or "",
    )


def _extract_trigger(text: str) -> Optional[str]:
    triggers = _extract_triggers(text)
    return triggers[0] if triggers else None


def _extract_triggers(text: str) -> List[str]:
    trigger_map = {
        "【Deploy】": "ON_DEPLOY",
        "【Attack】": "ON_ATTACK",
        "【Destroyed】": "ON_DESTROYED",
        "【Burst】": "BURST",
        "【Main】": "MAIN_PHASE",
        "【Action】": "ACTION_PHASE",
        "【When Paired】": "ON_PAIRED",
        "【When Linked】": "ON_LINKED",
        "【Activate･Main】": "ACTIVATE_MAIN",
        "【Activate･Action】": "ACTIVATE_ACTION",
    }
    if "【Main】/【Action】" in text or "【Action】/【Main】" in text:
        return ["MAIN_PHASE", "ACTION_PHASE"]
    return [trigger for marker, trigger in trigger_map.items() if marker in text]


def _extract_simple_action(text: str) -> Optional[Dict[str, Any]]:
    draw_match = re.search(r"\b[Dd]raw (\d+)", text)
    if draw_match and _only_simple_action(text, ("draw",)):
        return {"type": "DRAW", "target": "SELF", "amount": int(draw_match.group(1))}

    damage_match = re.search(r"\b[Dd]eal (\d+) damage", text)
    if damage_match and "Choose 1 enemy Unit" in text:
        target = {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"}
        if "rested enemy Unit" in text:
            target["filters"] = {"state": "RESTED"}
        return {
            "type": "DAMAGE_UNIT",
            "target": target,
            "amount": int(damage_match.group(1)),
            "damage_type": "EFFECT",
        }

    if re.search(r"\b[Rr]est (it|them)", text) and "Choose 1 enemy Unit" in text:
        return {
            "type": "REST_UNIT",
            "target": {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"},
        }

    if re.search(r"\b[Dd]estroy (it|them)", text) and "Choose 1 enemy Unit" in text:
        return {
            "type": "DESTROY_CARD",
            "target": {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"},
        }

    if re.search(r"\b[Rr]eturn (it|them|.+) to (?:its |their )?owner'?s hand", text) and "enemy Unit" in text:
        return {
            "type": "RETURN_TO_HAND",
            "target": {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"},
        }

    return None


def _extract_supported_conditions(text: str) -> List[Dict[str, Any]]:
    match = re.search(r"If you have (\d+) or more other Units in play", text, re.IGNORECASE)
    if match:
        return [
            {
                "type": "COUNT_CARDS",
                "zone": "BATTLE_AREA",
                "owner": "SELF",
                "card_type": "UNIT",
                "exclude_self": True,
                "operator": ">=",
                "value": int(match.group(1)),
            }
        ]
    return []


def _unsupported_reason(
    text: str,
    trigger: Optional[str],
    action: Optional[Dict[str, Any]],
    conditions: List[Dict[str, Any]],
) -> Optional[str]:
    if not trigger:
        return "No supported trigger/timing was identified."
    if "choose" in text.lower() and not action:
        return "Target choices require the pending effect decision layer."
    if "may" in text.lower():
        return "Optional decisions require the pending decision layer."
    if any(word in text.lower() for word in ("token", "instead", "search", "reveal", "look at", "shuffle")):
        return "Effect uses mechanics that are not in the current supported runtime vocabulary."
    if "If " in text and not conditions:
        return "Condition could not be represented with supported runtime conditions."
    if not action:
        return "No supported action could represent the full effect."
    return None


def _ir_actions_for(effect: GameEffect) -> List[Dict[str, Any]]:
    if effect.actions:
        return effect.actions
    if not effect.action_type:
        return []
    action: Dict[str, Any] = {"type": effect.action_type}
    if effect.amount is not None:
        action["amount"] = effect.amount
    if effect.target_selector:
        action["target"] = {"selector": effect.target_selector}
    if effect.duration:
        action["duration"] = effect.duration
    if effect.action_type == "RESOLVE_COMMAND_EFFECT":
        action["timing"] = effect.timing or ("ACTION_PHASE" if "【Action】" in effect.raw_text else "MAIN_PHASE")
    return [_normalize_keyword_grant_action(action, effect.raw_text)]


def _effect_type_for(effect: GameEffect) -> str:
    triggers = set(effect.triggers or ([effect.trigger] if effect.trigger else []))
    if triggers and triggers <= {"ACTIVATE_MAIN", "ACTIVATE_ACTION"}:
        return "ACTIVATED"
    if not effect.trigger:
        return "CONTINUOUS"
    return "TRIGGERED"


def _target_selector(target: Any) -> Optional[str]:
    if isinstance(target, dict):
        return target.get("selector")
    if isinstance(target, str):
        return target
    return None


def _only_simple_action(text: str, allowed_words: tuple[str, ...]) -> bool:
    action_words = ("draw", "deal", "rest", "destroy", "deploy", "discard", "return", "search", "reveal", "look")
    lower = text.lower()
    return all(word in allowed_words or word not in lower for word in action_words)


def _read_credentials_api_key(credentials_path: str | Path | None) -> str:
    path = Path(credentials_path) if credentials_path else PROJECT_ROOT / ".credentials"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            if key.strip() in {"OPENROUTER_API_KEY", "OPEN_ROUTER_API_KEY", "OPENAI_API_KEY", "API_KEY"}:
                return value.strip().strip("\"'")
        else:
            return stripped.strip("\"'")
    return ""


def _read_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _system_prompt() -> str:
    return f"""You are an expert Game Logic Compiler for the Bandai Gundam Card Game (GCG).
Your job is to translate ExBurst card text into conservative simulator IR candidates for a strict Python game engine.
Return only data matching the ParsedCard response model. Do not explain outside the structured fields.

Available runtime vocabulary:
- Triggers: {sorted(SUPPORTED_TRIGGER_TYPES)}
- Actions: {sorted(SUPPORTED_ACTION_TYPES)}
- Conditions: {sorted(SUPPORTED_CONDITION_TYPES)}
- Selectors: {sorted(SUPPORTED_SELECTOR_TYPES)}
- Durations: {sorted(SUPPORTED_DURATIONS)}

Critical rule for is_supported:
- Set is_supported=true when the complete effect can be represented with the available trigger/action/condition/selector vocabulary, even if it has conditions, choices, optional text, targeting, or multiple sequential actions.
- Do not mark an effect unsupported just because it says "If", "while", "choose", "you may", "up to", "look at", "reveal", "during link", "during pair", or has timing restrictions. Encode those with conditions, target selectors, optional actions, and ordered actions whenever the listed vocabulary can express the effect.
- Set is_supported=false only when the effect requires a mechanic that the listed vocabulary cannot represent without losing behavior. In unhandled_explanation, name the missing engine primitive precisely, such as "requires cost replacement hook", "requires return target to hand action", or "requires name alias modifier".

Output shape guidance:
- Preserve each printed effect line in raw_text.
- Use trigger for single timing, action_type/target_selector/amount/duration only for simple one-action effects, and actions for full action objects.
- For effects usable in more than one timing, use the triggers list, for example 【Main】/【Action】 -> ["MAIN_PHASE", "ACTION_PHASE"]. Do not combine trigger names into one comma-separated or underscored string.
- Use conditions for gating requirements. Never emit blank condition objects; if a condition has no meaningful type, omit it.
- Use actions in the exact order the card performs them. GCG effects resolve in printed order.
- Use restrictions for timing or usage restrictions such as ONCE_PER_TURN when they are not naturally represented as triggers or conditions.
- If only part of an effect is representable, keep is_supported=false and explain the missing part; do not claim support for partial behavior.

Timing and trigger mapping:
- 【Main】 Command timing -> MAIN_PHASE.
- 【Action】 Command timing -> ACTION_PHASE.
- 【Main】/【Action】 Command timing -> triggers ["MAIN_PHASE", "ACTION_PHASE"].
- 【Activate･Main】 -> ACTIVATE_MAIN. 【Activate･Action】 -> ACTIVATE_ACTION.
- 【Deploy】 -> ON_DEPLOY. 【Attack】 -> ON_ATTACK. 【Destroyed】 -> ON_DESTROYED. 【Burst】 -> BURST.
- 【Burst】Activate this card's 【Action】 -> trigger BURST and action RESOLVE_COMMAND_EFFECT with timing ACTION_PHASE; use MAIN_PHASE only when the referenced printed timing is 【Main】.
- 【When Paired】 -> ON_PAIRED. 【When Linked】 -> ON_LINKED.
- Static text such as "While", "During your turn", "This Unit gains", "All your Units gain", standalone <Keyword>, or [Suppression] should be represented as continuous-style effects with actions/modifiers when possible, not as unsupported text.
- 【Pilot】 lines are pilot metadata/stat bonuses. Preserve them as PILOT_ABILITY metadata when possible; do not emit them as executable pairing actions unless the text actually pairs a Pilot during resolution.

Condition mapping:
- Trait requirements like "friendly (Zeon) Unit", "this Unit is (Earth Federation)", or "Pilot has trait X" -> CHECK_TRAIT or CHECK_PAIRED_PILOT_TRAIT.
- Color requirements -> CHECK_COLOR or paired color triggers when available.
- Keyword requirements -> CHECK_KEYWORD.
- Active/rested/paired/linked/destroyed/attacking state -> CHECK_CARD_STATE or CHECK_LINK_STATUS.
- Damaged cards -> CHECK_DAMAGE with target, operator, and value 0; do not encode damaged as CHECK_CARD_STATE.
- "You have N or more cards/Units/resources/shields/trash" -> COUNT_CARDS with zone, owner, operator, value, and filters.
- Level/AP/HP/cost comparisons -> CHECK_STAT or CHECK_PLAYER_LEVEL when referring to player level.
- Turn conditions like "during your turn" or "during your opponent's turn" -> CHECK_TURN.
- Use operators exactly as ==, !=, >=, <=, >, <.

Target and selector mapping:
- "this Unit/card" -> SELF.
- Friendly Units/Bases/Resources -> FRIENDLY_UNIT, FRIENDLY_BASE, FRIENDLY_RESOURCE.
- Enemy Units/Base/player -> ENEMY_UNIT, ENEMY_BASE, ENEMY_PLAYER.
- Other friendly Unit -> OTHER_FRIENDLY_UNIT.
- Paired Pilot -> PAIRED_PILOT.
- Hand/trash/shields/deck zones -> SELF_HAND, OPPONENT_HAND, SELF_TRASH, OPPONENT_TRASH, SELF_SHIELDS, OPPONENT_SHIELDS, SELF_DECK when applicable.
- Cards looked at from deck -> LOOKED_AT_CARD; selected looked-at cards -> SELECTED_CARD.
- Use filters for traits, color, card_type, level, AP, HP, state, is_token, has_keyword, name_contains, and text_contains.

Action mapping:
- Draw -> DRAW.
- Discard from hand -> DISCARD.
- Deal effect damage to Unit -> DAMAGE_UNIT with damage_type EFFECT when useful.
- Rest a Unit -> REST_UNIT. Set active -> SET_ACTIVE.
- Destroy -> DESTROY_CARD. Remove/exile -> EXILE_CARDS.
- Recover HP -> RECOVER_HP.
- Modify AP/HP -> MODIFY_STAT with stat AP or HP and modification such as +2 or -3. Do not use modifier/amount-only shapes when stat+modification can be inferred.
- Grant <Repair X>, <Breach X>, <Support X>, <Blocker>, <First Strike>, <High-Maneuver>, or <Suppression> -> GRANT_KEYWORD with uppercase keyword and value for stackable numeric keywords.
- Deploy tokens -> DEPLOY_TOKEN if the token can be described by existing fields.
- Deploy from trash/deck/other zone -> DEPLOY_FROM_ZONE when source and target filters are expressible.
- Return chosen field cards to their owner's hand -> RETURN_TO_HAND. Add selected/zone cards to hand -> ADD_TO_HAND when source/target are expressible.
- Shield movement -> SHIELD_TO_HAND or ADD_TO_SHIELDS when expressible.
- Look at top N deck cards -> LOOK_AT_DECK. Select/reveal one among looked cards -> SELECT_LOOKED_AT_CARD. Return remaining looked cards to top/bottom -> RETURN_LOOKED_TO_TOP or RETURN_LOOKED_TO_BOTTOM.
- Optional "you may" effects -> OPTIONAL_ACTION with optional_actions and next_if_success when represented by existing actions.
- "If you do" means follow-up actions run only if the prior action succeeds. "Then" means continue even if the prior action fails.

Important GCG rules to preserve:
- Card text overrides general rules, but do not invent runtime vocabulary.
- Impossible actions are skipped; partial impossible actions do as much as possible.
- Tokens have Lv 0, cost 0, no color, and are removed when leaving field-like zones.
- Pilot AP/HP are added to paired Units while paired; Pilot traits are not added to the Unit.
- Link Units can attack the turn they are deployed.
- Standalone keywords are real mechanics, not reminder text. Numeric Repair/Breach/Support stack; Blocker/First Strike/High-Maneuver/Suppression do not stack.
- Burst effects have highest resolution priority, but encode them with BURST trigger rather than inventing priority fields.

Unsupported examples:
- Cost reductions or level/cost modifications -> MODIFY_COST when they can be represented as an effective play-cost hook. Unsupported only for replacement payment behavior that cannot be expressed.
- Damage reduction by a fixed amount -> REDUCE_DAMAGE. Prevention/destruction immunity -> GRANT_PROTECTION.
- Name aliasing or treating a card's name as another name if no modifier/action exists.
- Swapping zones, copying effects, changing ownership, viewing opponent hidden zones, or arbitrary search/shuffle behavior beyond the listed deck-look primitives.
"""
