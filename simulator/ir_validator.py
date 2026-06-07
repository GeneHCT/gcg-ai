"""Strict audit utilities for simulator IR files."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json

from simulator.ir_vocabulary import (
    SUPPORTED_ACTION_TYPES,
    SUPPORTED_CONDITION_TYPES,
    SUPPORTED_DURATIONS,
    SUPPORTED_EFFECT_TYPES,
    SUPPORTED_FILTER_KEYS,
    SUPPORTED_MODIFIER_TYPES,
    SUPPORTED_SELECTOR_TYPES,
    SUPPORTED_TRIGGER_TYPES,
)


@dataclass(frozen=True)
class IRValidationIssue:
    card_id: str
    path: str
    kind: str
    value: str
    message: str


@dataclass
class IRValidationReport:
    card_id: str
    issues: List[IRValidationIssue] = field(default_factory=list)

    @property
    def is_supported(self) -> bool:
        return not self.issues

    @property
    def support_status(self) -> str:
        if self.is_supported:
            return "supported"
        issue_kinds = {issue.kind for issue in self.issues}
        if "unsupported_llm_effect" in issue_kinds:
            return "unsupported"
        return "partial"


def validate_ir_effect_data(effect_data: Dict[str, Any]) -> IRValidationReport:
    card_id = str(effect_data.get("card_id") or "<unknown>")
    report = IRValidationReport(card_id=card_id)

    for index, effect in enumerate(effect_data.get("effects", [])):
        _validate_effect(card_id, f"effects[{index}]", effect, report)

    for index, effect in enumerate(effect_data.get("continuous_effects", [])):
        _validate_effect(card_id, f"continuous_effects[{index}]", effect, report)

    for index, keyword in enumerate(effect_data.get("keywords", [])):
        if not isinstance(keyword, dict) or not keyword.get("keyword"):
            _add_issue(report, f"keywords[{index}]", "malformed_keyword", keyword, "Keyword entry must include a keyword name")

    return report


def validate_ir_file(path: str | Path) -> IRValidationReport:
    effect_data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_ir_effect_data(effect_data)


def audit_ir_directory(path: str | Path) -> Dict[str, Any]:
    reports = [
        validate_ir_file(effect_path)
        for effect_path in sorted(Path(path).iterdir())
        if effect_path.is_file() and not effect_path.name.startswith(".")
    ]
    return {
        "total_cards": len(reports),
        "supported": sum(report.support_status == "supported" for report in reports),
        "partial": sum(report.support_status == "partial" for report in reports),
        "unsupported": sum(report.support_status == "unsupported" for report in reports),
        "issues": [
            {
                "card_id": issue.card_id,
                "path": issue.path,
                "kind": issue.kind,
                "value": issue.value,
                "message": issue.message,
            }
            for report in reports
            for issue in report.issues
        ],
    }


def _validate_effect(card_id: str, path: str, effect: Dict[str, Any], report: IRValidationReport) -> None:
    effect_type = str(effect.get("effect_type") or "")
    if effect_type not in SUPPORTED_EFFECT_TYPES:
        _add_issue(report, f"{path}.effect_type", "unknown_effect_type", effect_type, "Effect type is not recognized")

    for index, trigger in enumerate(effect.get("triggers", [])):
        if trigger not in SUPPORTED_TRIGGER_TYPES:
            _add_issue(report, f"{path}.triggers[{index}]", "unknown_trigger", trigger, "Trigger is not in runtime vocabulary")

    if effect.get("is_supported") is False:
        explanation = str(effect.get("unhandled_explanation") or "LLM parser marked this effect unsupported")
        _add_issue(report, path, "unsupported_llm_effect", effect.get("effect_id", ""), explanation)

    for index, condition in enumerate(effect.get("conditions", [])):
        _validate_condition(card_id, f"{path}.conditions[{index}]", condition, report)

    for index, action in enumerate(effect.get("actions", [])):
        _validate_action(card_id, f"{path}.actions[{index}]", action, report)

    modifiers = effect.get("modifiers", effect.get("modifications", []))
    for index, modifier in enumerate(modifiers):
        _validate_modifier(card_id, f"{path}.modifiers[{index}]", modifier, report)


def _validate_condition(card_id: str, path: str, condition: Dict[str, Any], report: IRValidationReport) -> None:
    condition_type = str(condition.get("type") or "")
    if condition_type not in SUPPORTED_CONDITION_TYPES:
        _add_issue(report, f"{path}.type", "unknown_condition", condition_type, "Condition is not executed by the runtime")

    target = condition.get("target")
    if isinstance(target, dict):
        _validate_target(card_id, f"{path}.target", target, report)


def _validate_action(card_id: str, path: str, action: Dict[str, Any], report: IRValidationReport) -> None:
    action_type = str(action.get("type") or "")
    if action_type not in SUPPORTED_ACTION_TYPES:
        _add_issue(report, f"{path}.type", "unknown_action", action_type, "Action is not executed by the runtime")
    elif action_type == "GRANT_KEYWORD" and not action.get("keyword"):
        _add_issue(report, f"{path}.keyword", "missing_keyword", action.get("keyword"), "Keyword grant must name the granted keyword")
    elif action_type == "MODIFY_STAT" and (not action.get("stat") or not action.get("modification")):
        _add_issue(
            report,
            path,
            "malformed_stat_modifier",
            action,
            "Stat modifier must include stat and modification fields",
        )
    elif action_type == "MODIFY_COST" and not action.get("modification"):
        _add_issue(
            report,
            path,
            "malformed_cost_modifier",
            action,
            "Cost modifier must include a modification field",
        )
    elif action_type == "REDUCE_DAMAGE" and action.get("amount") is None:
        _add_issue(
            report,
            path,
            "malformed_damage_reduction",
            action,
            "Damage reduction must include an amount",
        )

    target = action.get("target")
    if isinstance(target, dict):
        _validate_target(card_id, f"{path}.target", target, report)

    duration = action.get("duration")
    if duration is not None and duration not in SUPPORTED_DURATIONS:
        _add_issue(report, f"{path}.duration", "unknown_duration", duration, "Duration is not in runtime vocabulary")

    for key in ("conditional_actions", "optional_actions", "next_if_success", "else_actions"):
        for index, nested in enumerate(_as_list(action.get(key))):
            if isinstance(nested, dict):
                _validate_action(card_id, f"{path}.{key}[{index}]", nested, report)

    conditional_next = action.get("conditional_next", {})
    if isinstance(conditional_next, dict):
        for index, nested in enumerate(_as_list(conditional_next.get("actions"))):
            if isinstance(nested, dict):
                _validate_action(card_id, f"{path}.conditional_next.actions[{index}]", nested, report)

        for index, condition in enumerate(_as_list(conditional_next.get("conditions"))):
            if isinstance(condition, dict):
                _validate_condition(card_id, f"{path}.conditional_next.conditions[{index}]", condition, report)


def _validate_modifier(card_id: str, path: str, modifier: Dict[str, Any], report: IRValidationReport) -> None:
    modifier_type = str(modifier.get("type") or "")
    if modifier_type not in SUPPORTED_MODIFIER_TYPES:
        _add_issue(report, f"{path}.type", "unknown_modifier", modifier_type, "Modifier is not recomputed by the runtime")

    target = modifier.get("target")
    if isinstance(target, dict):
        _validate_target(card_id, f"{path}.target", target, report)

    duration = modifier.get("duration")
    if duration is not None and duration not in SUPPORTED_DURATIONS:
        _add_issue(report, f"{path}.duration", "unknown_duration", duration, "Duration is not in runtime vocabulary")


def _validate_target(card_id: str, path: str, target: Dict[str, Any], report: IRValidationReport) -> None:
    selector = target.get("selector")
    if selector is not None and selector not in SUPPORTED_SELECTOR_TYPES:
        _add_issue(report, f"{path}.selector", "unknown_selector", selector, "Selector is not resolved by the runtime")

    filters = target.get("filters", {})
    if isinstance(filters, dict):
        for key in filters:
            if key not in SUPPORTED_FILTER_KEYS:
                _add_issue(report, f"{path}.filters.{key}", "unknown_filter", key, "Filter is not applied by the runtime")


def _add_issue(report: IRValidationReport, path: str, kind: str, value: Any, message: str) -> None:
    report.issues.append(
        IRValidationIssue(
            card_id=report.card_id,
            path=path,
            kind=kind,
            value=str(value),
            message=message,
        )
    )


def _as_list(value: Optional[Any]) -> Iterable[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
