"""Semantic audit utilities for ExBurst card-effect IR."""
from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from simulator.exburst_essential_cards import (
    apply_essential_cosmetic_normalization,
    is_essential_cosmetic_card_id,
)
from simulator.ir_validator import audit_ir_directory


TARGET_ACTION_TYPES = {
    "ADD_TO_HAND",
    "DAMAGE_UNIT",
    "DEPLOY_FROM_ZONE",
    "DESTROY_CARD",
    "EXILE_CARDS",
    "GRANT_ATTACK_TARGETING",
    "GRANT_KEYWORD",
    "GRANT_PROTECTION",
    "MODIFY_STAT",
    "OPTIONAL_ACTION",
    "PAIR_PILOT",
    "PREVENT_SET_ACTIVE",
    "RECOVER_HP",
    "REDUCE_DAMAGE",
    "REST_UNIT",
    "RETURN_TO_HAND",
    "SELECT_TARGET",
    "SET_ACTIVE",
}

CHAIN_KEYS = ("conditional_actions", "optional_actions", "next_if_success", "else_actions")
BRANCH_ACTION_KEYS = ("actions", "true_actions", "false_actions", "success_actions", "on_true", "on_false")
STACKING_KEYWORDS = {"BREACH", "REPAIR", "SUPPORT"}
NON_STACKING_KEYWORDS = {"BLOCKER", "FIRST_STRIKE", "HIGH_MANEUVER", "SUPPRESSION"}
CARD_STATES = {"ACTIVE", "RESTED", "PAIRED", "LINKED", "DESTROYED", "ATTACKING"}


@dataclass(frozen=True)
class SemanticAuditIssue:
    card_id: str
    path: str
    kind: str
    severity: str
    message: str
    raw_text: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class LLMTestSpecIssue:
    path: str
    message: str


def audit_exburst_semantics(
    output_dir: str | Path = "card_effects_exburst",
    *,
    normalized_cards_path: str | Path | None = "exburst_cards_normalized.json",
    card_database_dir: str | Path | None = "card_database",
) -> Dict[str, Any]:
    """Audit ExBurst IR for semantic mismatches that vocabulary validation misses."""
    output_path = Path(output_dir)
    strict_audit = audit_ir_directory(output_path)
    authority = _load_authority_texts(normalized_cards_path, card_database_dir)
    cards = [_load_effect_file(path) for path in sorted(output_path.iterdir()) if path.is_file()]
    essential_ids = {
        str(card.get("card_id") or "")
        for card in cards
        if is_essential_cosmetic_card_id(str(card.get("card_id") or ""))
    }
    auditable_cards = [
        card
        for card in cards
        if str(card.get("card_id") or "") not in essential_ids
    ]
    issues = [
        issue
        for card in auditable_cards
        for issue in audit_card_semantics(card, authority.get(str(card.get("card_id") or "")))
    ]
    strict_issues = [
        issue
        for issue in strict_audit["issues"]
        if str(issue.get("card_id") or "") not in essential_ids
    ]
    grouped = _group_issues([*strict_issues, *[asdict(issue) for issue in issues]])
    statuses = Counter(card.get("metadata", {}).get("support_status", "unknown") for card in cards)
    return {
        "total_cards": len(cards),
        "essential_cosmetic_card_count": len(essential_ids),
        "strict_validation": {
            "supported": strict_audit["supported"],
            "partial": strict_audit["partial"],
            "unsupported": strict_audit["unsupported"],
            "issue_count": len(strict_issues),
        },
        "metadata_status": {
            "supported": statuses["supported"],
            "partial": statuses["partial"],
            "unsupported": statuses["unsupported"],
            "unknown": statuses["unknown"],
        },
        "semantic_issue_count": len(issues),
        "affected_cards": sorted({issue.card_id for issue in issues}),
        "issues": [asdict(issue) for issue in issues],
        "groups": grouped,
    }


def audit_card_semantics(card: Dict[str, Any], authority_text: Optional[List[str]] = None) -> List[SemanticAuditIssue]:
    card_id = str(card.get("card_id") or "")
    issues: List[SemanticAuditIssue] = []
    original_text = _normalize_text(card.get("metadata", {}).get("original_text", ""))
    if authority_text and original_text:
        authority_joined = _normalize_text("; ".join(authority_text))
        if authority_joined and _strip_markup(original_text) != _strip_markup(authority_joined):
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path="metadata.original_text",
                    kind="authority_text_mismatch",
                    severity="review",
                    message="Checked-in IR original_text differs from the normalized card database text.",
                    raw_text=original_text,
                    recommendation="Review this card before trusting semantic findings generated from metadata text.",
                )
            )

    for bucket in ("effects", "continuous_effects"):
        for index, effect in enumerate(card.get(bucket, [])):
            path = f"{bucket}[{index}]"
            raw_text = _effect_raw_text(effect)
            issues.extend(_audit_effect(card_id, path, effect, raw_text))
    return issues


def normalize_effect_data(effect_data: Dict[str, Any]) -> tuple[Dict[str, Any], List[SemanticAuditIssue]]:
    """Return a copy with conservative, schema-preserving ExBurst IR normalizations."""
    normalized = copy.deepcopy(effect_data)
    card_id = str(normalized.get("card_id") or "")
    changes: List[SemanticAuditIssue] = []

    for bucket in ("effects", "continuous_effects"):
        for effect_index, effect in enumerate(normalized.get(bucket, [])):
            path = f"{bucket}[{effect_index}]"
            conditions = effect.get("conditions", [])
            raw_text = _effect_raw_text(effect)
            for cond_index, condition in enumerate(_walk_conditions(conditions)):
                original_condition = copy.deepcopy(condition)
                canonical_condition = _canonicalize_condition_shape(condition, raw_text)
                if canonical_condition != condition:
                    condition.clear()
                    condition.update(canonical_condition)
                    changes.append(
                        SemanticAuditIssue(
                            card_id=card_id,
                            path=f"{path}.conditions[{cond_index}]",
                            kind="normalized_condition_shape",
                            severity="fixed",
                            message="Normalized legacy condition fields into canonical runtime IR shape.",
                            raw_text=raw_text,
                        )
                    )
                    if (
                        original_condition.get("type") == "CHECK_CARD_STATE"
                        and original_condition.get("value") in {"ACTIVE", "RESTED", "PAIRED", "LINKED", "DESTROYED", "ATTACKING"}
                        and canonical_condition.get("state") == original_condition.get("value")
                    ):
                        changes.append(
                            SemanticAuditIssue(
                                card_id=card_id,
                                path=f"{path}.conditions[{cond_index}]",
                                kind="normalized_legacy_card_state",
                                severity="fixed",
                                message="Normalized legacy CHECK_CARD_STATE value field into state.",
                                raw_text=raw_text,
                            )
                        )
                legacy_state = condition.get("value")
                if (
                    condition.get("type") == "CHECK_CARD_STATE"
                    and condition.get("state") is None
                    and legacy_state in CARD_STATES
                ):
                    condition["state"] = condition.pop("value")
                    changes.append(
                        SemanticAuditIssue(
                            card_id=card_id,
                            path=f"{path}.conditions[{cond_index}]",
                            kind="normalized_legacy_card_state",
                            severity="fixed",
                            message="Converted legacy CHECK_CARD_STATE value field to state.",
                            raw_text=raw_text,
                        )
                    )

            for change_path, message in _normalize_invalid_state_conditions(effect, raw_text):
                changes.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{path}.{change_path}",
                        kind="normalized_invalid_card_state",
                        severity="fixed",
                        message=message,
                        raw_text=raw_text,
                    )
                )

            for change_path, message in _normalize_event_conditions(effect):
                changes.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{path}.{change_path}",
                        kind="normalized_event_condition",
                        severity="fixed",
                        message=message,
                        raw_text=raw_text,
                    )
                )

            trigger_change = _normalize_effect_triggers(effect, raw_text)
            if trigger_change:
                changes.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{path}.triggers",
                        kind="normalized_timing_triggers",
                        severity="fixed",
                        message=trigger_change,
                        raw_text=raw_text,
                    )
                )

            state_by_selector = _state_conditions_by_selector(conditions)
            expected = _expected_target_from_text(raw_text)
            for action_path, action in _walk_actions(effect.get("actions", []), f"{path}.actions"):
                canonical = _canonicalize_action_shape(action, raw_text)
                if canonical != action:
                    action.clear()
                    action.update(canonical)
                    changes.append(
                        SemanticAuditIssue(
                            card_id=card_id,
                            path=action_path,
                            kind="normalized_action_shape",
                            severity="fixed",
                            message="Normalized legacy action fields into canonical runtime IR shape.",
                            raw_text=raw_text,
                        )
                    )
                for nested_index, nested_condition in enumerate(action.get("conditions", []) if isinstance(action.get("conditions"), list) else []):
                    if not isinstance(nested_condition, dict):
                        continue
                    canonical_condition = _canonicalize_condition_shape(nested_condition, raw_text)
                    if canonical_condition != nested_condition:
                        nested_condition.clear()
                        nested_condition.update(canonical_condition)
                        changes.append(
                            SemanticAuditIssue(
                                card_id=card_id,
                                path=f"{action_path}.conditions[{nested_index}]",
                                kind="normalized_condition_shape",
                                severity="fixed",
                                message="Normalized legacy action-local condition fields into canonical runtime IR shape.",
                                raw_text=raw_text,
                            )
                        )
                target = action.get("target")
                if not isinstance(target, dict):
                    continue
                selector = target.get("selector")
                if selector in state_by_selector and target.get("filters", {}).get("state") is None:
                    target.setdefault("filters", {})["state"] = state_by_selector[selector]
                    changes.append(
                        SemanticAuditIssue(
                            card_id=card_id,
                            path=f"{action_path}.target.filters.state",
                            kind="normalized_missing_state_filter",
                            severity="fixed",
                            message="Copied matching CHECK_CARD_STATE selector state onto the action target filter.",
                            raw_text=raw_text,
                        )
                    )
                if expected and expected.get("selector") == selector:
                    for filter_key, filter_value in expected.get("filters", {}).items():
                        if target.get("filters", {}).get(filter_key) is not None:
                            continue
                        target.setdefault("filters", {})[filter_key] = filter_value
                        changes.append(
                            SemanticAuditIssue(
                                card_id=card_id,
                                path=f"{action_path}.target.filters.{filter_key}",
                                kind=f"normalized_text_{filter_key}_filter",
                                severity="fixed",
                                message="Added filter required by the printed qualified target text.",
                                raw_text=raw_text,
                            )
                        )
                    if expected.get("variable_count") and target.get("variable_count") != expected["variable_count"]:
                        target["variable_count"] = expected["variable_count"]
                        changes.append(
                            SemanticAuditIssue(
                                card_id=card_id,
                                path=f"{action_path}.target.variable_count",
                                kind="normalized_text_variable_count",
                                severity="fixed",
                                message="Added variable_count required by the printed target range.",
                                raw_text=raw_text,
                            )
                        )

            modifiers = effect.get("modifiers", effect.get("modifications", []))
            for modifier_index, modifier in enumerate(modifiers or []):
                if not isinstance(modifier, dict):
                    continue
                canonical = _canonicalize_action_shape(modifier, raw_text)
                if canonical != modifier:
                    modifier.clear()
                    modifier.update(canonical)
                    changes.append(
                        SemanticAuditIssue(
                            card_id=card_id,
                            path=f"{path}.modifiers[{modifier_index}]",
                            kind="normalized_modifier_shape",
                            severity="fixed",
                            message="Normalized legacy modifier fields into canonical runtime IR shape.",
                            raw_text=raw_text,
                        )
                    )

            removed = _remove_moved_target_qualification_conditions(effect, expected)
            for condition_path, state in removed:
                changes.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{path}.{condition_path}",
                        kind="removed_target_qualification_condition",
                        severity="fixed",
                        message="Removed broad CHECK_CARD_STATE after moving the printed target qualification to action filters.",
                        raw_text=raw_text,
                        recommendation=f"Target state {state} is now enforced by action.target.filters.state.",
                    )
                )

            for change_path in _normalize_existing_select_targets(effect, raw_text):
                changes.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{path}.{change_path}",
                        kind="normalized_selected_target_workflow",
                        severity="fixed",
                        message="Aligned existing SELECT_TARGET with the printed choice target.",
                        raw_text=raw_text,
                    )
                )

            for change_path in _normalize_selected_target_workflow(effect, expected, raw_text):
                changes.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{path}.{change_path}",
                        kind="normalized_selected_target_workflow",
                        severity="fixed",
                        message="Inserted SELECT_TARGET and rewired pronoun follow-up actions to SELECTED_CARD.",
                        raw_text=raw_text,
                    )
                )

            for change_path, message in _normalize_clause_semantics(effect, raw_text):
                changes.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{path}.{change_path}",
                        kind="normalized_clause_semantics",
                        severity="fixed",
                        message=message,
                        raw_text=raw_text,
                    )
                )

    return normalized, changes


def apply_normalizations(output_dir: str | Path = "card_effects_exburst") -> Dict[str, Any]:
    """Apply conservative normalizations in-place and return a summary."""
    essential_summary = apply_essential_cosmetic_normalization(output_dir)
    changed_cards = []
    changes: List[SemanticAuditIssue] = []
    for path in sorted(Path(output_dir).iterdir()):
        if not path.is_file():
            continue
        original = _load_effect_file(path)
        normalized, card_changes = normalize_effect_data(original)
        if not card_changes:
            continue
        path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed_cards.append(str(normalized.get("card_id") or path.name))
        changes.extend(card_changes)
    return {
        "essential_cosmetic": essential_summary,
        "changed_card_count": len(changed_cards),
        "changed_cards": changed_cards,
        "change_count": len(changes),
        "changes": [asdict(change) for change in changes],
    }


def build_llm_test_generation_prompt(card: Dict[str, Any], effect_data: Dict[str, Any]) -> str:
    """Build a constrained prompt for generating card-specific behavioral test specs."""
    return (
        "Create deterministic simulator test specs for this Gundam Card Game card.\n"
        "Return JSON only with a top-level test_cases array. Each case must include: "
        "name, cited_text, initial_state, action, expected_legal_targets, expected_state_delta, "
        "rules_references, and unsupported_mechanics.\n"
        "Do not write code and do not invent hidden information. If a mechanic cannot be represented "
        "deterministically, list it in unsupported_mechanics.\n\n"
        f"Card:\n{json.dumps(card, ensure_ascii=False, indent=2)}\n\n"
        f"Current IR:\n{json.dumps(effect_data, ensure_ascii=False, indent=2)}"
    )


def validate_llm_test_spec(spec: Dict[str, Any]) -> List[LLMTestSpecIssue]:
    """Validate the structured LLM test-spec contract before any pytest generation."""
    issues: List[LLMTestSpecIssue] = []
    cases = spec.get("test_cases")
    if not isinstance(cases, list) or not cases:
        return [LLMTestSpecIssue("test_cases", "Spec must include a non-empty test_cases list.")]

    required = {
        "name",
        "cited_text",
        "initial_state",
        "action",
        "expected_legal_targets",
        "expected_state_delta",
        "rules_references",
        "unsupported_mechanics",
    }
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            issues.append(LLMTestSpecIssue(f"test_cases[{index}]", "Each test case must be an object."))
            continue
        for key in sorted(required - set(case)):
            issues.append(LLMTestSpecIssue(f"test_cases[{index}].{key}", "Missing required field."))
        if case.get("unsupported_mechanics"):
            issues.append(
                LLMTestSpecIssue(
                    f"test_cases[{index}].unsupported_mechanics",
                    "Case is quarantined until unsupported mechanics are implemented or manually modeled.",
                )
            )
        if not case.get("cited_text"):
            issues.append(LLMTestSpecIssue(f"test_cases[{index}].cited_text", "Case must cite the printed phrase it covers."))
    return issues


def write_markdown_report(audit: Dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(render_markdown_report(audit), encoding="utf-8")


def render_markdown_report(audit: Dict[str, Any]) -> str:
    lines = [
        "# ExBurst Semantic Audit",
        "",
        f"- Total cards: {audit['total_cards']}",
        f"- Strict validation issues: {audit['strict_validation']['issue_count']}",
        f"- Semantic issues: {audit['semantic_issue_count']}",
        f"- Affected cards: {len(audit['affected_cards'])}",
        "",
        "## Groups",
    ]
    for group in audit["groups"][:50]:
        examples = ", ".join(group["examples"])
        lines.append(
            f"- `{group['kind']}` ({group['severity']}): {group['count']} issue(s), examples: {examples}"
        )
    if audit["issues"]:
        lines.extend(["", "## Semantic Findings"])
        for issue in audit["issues"][:200]:
            lines.append(
                f"- `{issue['card_id']}` `{issue['kind']}` at `{issue['path']}`: {issue['message']}"
            )
    return "\n".join(lines) + "\n"


def _audit_effect(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    issues: List[SemanticAuditIssue] = []
    issues.extend(_audit_malformed_targets(card_id, path, effect, raw_text))
    issues.extend(_audit_invalid_card_states(card_id, path, effect, raw_text))
    issues.extend(_audit_legacy_state_conditions(card_id, path, effect, raw_text))
    issues.extend(_audit_condition_target_filters(card_id, path, effect, raw_text))
    issues.extend(_audit_text_target_expectations(card_id, path, effect, raw_text))
    issues.extend(_audit_timing(card_id, path, effect, raw_text))
    issues.extend(_audit_quantities(card_id, path, effect, raw_text))
    issues.extend(_audit_clause_connectors(card_id, path, effect, raw_text))
    issues.extend(_audit_keywords(card_id, path, effect, raw_text))
    return issues


def _audit_malformed_targets(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    issues: List[SemanticAuditIssue] = []
    for action_path, action in _walk_actions(effect.get("actions", []), f"{path}.actions"):
        target = action.get("target")
        if isinstance(target, dict) and "filters" in target and not isinstance(target.get("filters"), dict):
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{action_path}.target.filters",
                    kind="malformed_target_filters",
                    severity="warning",
                    message="Target filters must be a dictionary because TargetResolver expects key/value filters.",
                    raw_text=raw_text,
                    recommendation="Merge list-shaped filters into one target.filters object.",
                )
            )
    return issues


def _audit_invalid_card_states(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    issues: List[SemanticAuditIssue] = []
    for condition_path, condition in _walk_conditions_with_paths(effect.get("conditions", []), f"{path}.conditions"):
        if condition.get("type") != "CHECK_CARD_STATE":
            continue
        state = condition.get("state")
        if state and state not in CARD_STATES:
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{condition_path}.state",
                    kind="invalid_card_state",
                    severity="warning",
                    message=f"CHECK_CARD_STATE state {state} is not supported by ConditionEvaluator.",
                    raw_text=raw_text,
                    recommendation="Use ACTIVE, RESTED, PAIRED, or LINKED only; model destroyed/damaged/zone checks with another supported condition.",
                )
            )
    return issues


def _audit_legacy_state_conditions(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    return [
        SemanticAuditIssue(
            card_id=card_id,
            path=condition_path,
            kind="legacy_check_card_state_value",
            severity="fixable",
            message="CHECK_CARD_STATE uses legacy value instead of state.",
            raw_text=raw_text,
            recommendation="Normalize value to state so ConditionEvaluator checks the state directly.",
        )
        for condition_path, condition in _walk_conditions_with_paths(effect.get("conditions", []), f"{path}.conditions")
        if condition.get("type") == "CHECK_CARD_STATE" and condition.get("value") and condition.get("state") is None
    ]


def _audit_condition_target_filters(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    issues: List[SemanticAuditIssue] = []
    state_by_selector = _state_conditions_by_selector(effect.get("conditions", []))
    for action_path, action in _walk_actions(effect.get("actions", []), f"{path}.actions"):
        if action.get("type") not in TARGET_ACTION_TYPES:
            continue
        target = action.get("target")
        if not isinstance(target, dict):
            continue
        selector = target.get("selector")
        if selector in state_by_selector and target.get("filters", {}).get("state") != state_by_selector[selector]:
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{action_path}.target.filters.state",
                    kind="condition_target_filter_mismatch",
                    severity="fixable",
                    message=(
                        f"Effect-level CHECK_CARD_STATE constrains {selector} to {state_by_selector[selector]}, "
                        "but the action target does not carry the same filter."
                    ),
                    raw_text=raw_text,
                    recommendation="Move or copy the target qualification into action.target.filters.",
                )
            )
    return issues


def _audit_text_target_expectations(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    expected = _expected_target_from_text(raw_text)
    if not expected:
        return []
    target_actions = [
        (action_path, action)
        for action_path, action in _walk_actions(effect.get("actions", []), f"{path}.actions")
        if isinstance(action.get("target"), dict) and action.get("type") in TARGET_ACTION_TYPES
    ]
    if not target_actions:
        return [
            SemanticAuditIssue(
                card_id=card_id,
                path=f"{path}.actions",
                kind="missing_target_action_for_choice",
                severity="warning",
                message="Printed text chooses a qualified target, but no target-bearing action was found.",
                raw_text=raw_text,
                recommendation="Review whether the effect should act on the chosen target.",
            )
        ]

    expected_targets = _expected_targets_from_text(raw_text) or [expected]
    consumers = _choice_target_consumers(target_actions, len(expected_targets), raw_text)

    issues: List[SemanticAuditIssue] = []
    for expected_target, (action_path, action) in zip(expected_targets, consumers):
        target = action["target"]
        selector = target.get("selector")
        if selector != expected_target["selector"] and selector != "SELECTED_CARD":
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{action_path}.target.selector",
                    kind="selected_target_selector_mismatch",
                    severity="warning",
                    message=f"Printed target implies {expected_target['selector']}, but IR action targets {selector}.",
                    raw_text=raw_text,
                    recommendation="Use SELECTED_CARD or the same constrained selector as the printed choice.",
                )
            )
            continue

        if selector == "SELECTED_CARD":
            continue

        issues.extend(_compare_expected_filters(card_id, f"{action_path}.target", raw_text, expected_target, target, effect))
        actual_count = target.get("count", 1)
        if expected_target.get("count") is not None and actual_count != expected_target["count"]:
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{action_path}.target.count",
                    kind="target_count_mismatch",
                    severity="warning",
                    message=f"Printed text chooses {expected['count']} target(s), but IR count is {actual_count}.",
                    raw_text=raw_text,
                    recommendation="Set target.count to match the printed choice count.",
                )
            )
        if expected_target.get("variable_count") and target.get("variable_count") != expected_target["variable_count"]:
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{action_path}.target.variable_count",
                    kind="target_variable_count_mismatch",
                    severity="warning",
                    message="Printed text chooses a target range, but IR variable_count does not match.",
                    raw_text=raw_text,
                    recommendation="Represent ranges such as 1 to 2 with variable_count min/max.",
                )
            )
    return issues


def _audit_timing(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    expected = _expected_triggers(raw_text)
    if not expected:
        return []
    triggers = set(effect.get("triggers", []))
    missing = sorted(expected - triggers)
    if not missing:
        return []
    return [
        SemanticAuditIssue(
            card_id=card_id,
            path=f"{path}.triggers",
            kind="timing_trigger_mismatch",
            severity="warning",
            message=f"Printed timing expects {', '.join(missing)}, but triggers are {sorted(triggers)}.",
            raw_text=raw_text,
            recommendation="Map printed timing markers to supported runtime triggers.",
        )
    ]


def _audit_quantities(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    issues: List[SemanticAuditIssue] = []
    actions = list(_walk_actions(effect.get("actions", []), f"{path}.actions"))
    quantity_patterns = [
        (r"\b[Dd]raw (\d+)", "DRAW", "amount", "draw_amount_mismatch"),
        (r"\b[Dd]eal (\d+) damage", "DAMAGE_UNIT", "amount", "damage_amount_mismatch"),
        (r"\b[Rr]ecovers? (\d+) HP", "RECOVER_HP", "amount", "recover_amount_mismatch"),
    ]
    for pattern, action_type, field, kind in quantity_patterns:
        match = re.search(pattern, raw_text)
        if not match:
            continue
        expected = int(match.group(1))
        matching = [(action_path, action) for action_path, action in actions if action.get("type") == action_type]
        if not matching:
            issues.append(_missing_action_issue(card_id, path, kind, action_type, raw_text))
            continue
        for action_path, action in matching:
            if kind == "damage_amount_mismatch" and (" instead" in raw_text.lower() or " for each " in raw_text.lower()):
                continue
            if action.get(field) != expected:
                issues.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{action_path}.{field}",
                        kind=kind,
                        severity="warning",
                        message=f"Printed amount is {expected}, but IR value is {action.get(field)}.",
                        raw_text=raw_text,
                    )
                )

    printed_stat_modifiers = {
        (match.group(1).upper(), f"{match.group(2)}{match.group(3)}")
        for match in re.finditer(r"\b(AP|HP)\s*([+-])\s*(\d+)", raw_text, flags=re.IGNORECASE)
    }
    if printed_stat_modifiers:
        for action_path, action in [(p, a) for p, a in actions if a.get("type") == "MODIFY_STAT"]:
            actual = (str(action.get("stat") or "").upper(), str(action.get("modification")))
            if actual not in printed_stat_modifiers:
                issues.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=action_path,
                        kind="stat_modifier_mismatch",
                        severity="warning",
                        message=f"Printed stat modifiers are {sorted(printed_stat_modifiers)}, but IR has {action}.",
                        raw_text=raw_text,
                    )
                )
    return issues


def _audit_clause_connectors(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    lowered = raw_text.lower()
    actions = effect.get("actions", [])
    issues: List[SemanticAuditIssue] = []
    if "if you do" in lowered and not _has_success_gated_action(actions):
        issues.append(
            SemanticAuditIssue(
                card_id=card_id,
                path=f"{path}.actions",
                kind="if_you_do_not_success_gated",
                severity="review",
                message="Printed text uses If you do, but IR does not show an explicit success-gated follow-up.",
                raw_text=raw_text,
                recommendation="Represent the follow-up with next_if_success or an equivalent conditional branch.",
            )
        )
    if " then " in lowered and not _has_ordered_multi_action(actions):
        issues.append(
            SemanticAuditIssue(
                card_id=card_id,
                path=f"{path}.actions",
                kind="then_clause_review",
                severity="review",
                message="Printed text uses Then; verify the follow-up is represented as ordered actions even if the first part fails.",
                raw_text=raw_text,
            )
        )
    if "you may" in lowered and not _has_optional_action(actions):
        issues.append(
            SemanticAuditIssue(
                card_id=card_id,
                path=f"{path}.actions",
                kind="may_effect_not_optional",
                severity="review",
                message="Printed text is optional, but IR does not expose an optional action marker.",
                raw_text=raw_text,
            )
        )
    return issues


def _audit_keywords(card_id: str, path: str, effect: Dict[str, Any], raw_text: str) -> List[SemanticAuditIssue]:
    issues: List[SemanticAuditIssue] = []
    printed_keywords = {
        _normalize_keyword_name(match.group(1)): int(match.group(2)) if match.group(2) else None
        for match in re.finditer(r"<([A-Za-z -]+)(?:\s+(\d+))?>", raw_text)
    }
    if not printed_keywords:
        return issues

    granted = [
        (action_path, action)
        for action_path, action in _walk_actions(effect.get("actions", []), f"{path}.actions")
        if action.get("type") == "GRANT_KEYWORD"
    ]
    modifiers = [
        (f"{path}.modifiers[{index}]", modifier)
        for index, modifier in enumerate(effect.get("modifiers", effect.get("modifications", [])))
        if modifier.get("type") == "GRANT_KEYWORD"
    ]
    grants = granted + modifiers
    choice_keywords = {
        _normalize_keyword_name(match.group(1))
        for match in re.finditer(r"with\s*[【<]([A-Za-z -]+)[】>]", _choice_phrase(raw_text), re.IGNORECASE)
    }
    for keyword, value in printed_keywords.items():
        if keyword in choice_keywords:
            continue
        requires_grant = _keyword_requires_grant(raw_text, keyword)
        if keyword == "SUPPORT" and _has_executable_support_actions(effect.get("actions", []), value):
            requires_grant = False
        if requires_grant and not any(action.get("keyword") == keyword for _, action in grants):
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=path,
                    kind="keyword_missing_from_ir",
                    severity="warning",
                    message=f"Printed text references <{keyword}>, but no matching GRANT_KEYWORD IR was found.",
                    raw_text=raw_text,
                )
            )
        for grant_path, action in grants:
            if action.get("keyword") == keyword and value is not None and action.get("value") != value:
                issues.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=f"{grant_path}.value",
                        kind="keyword_value_mismatch",
                        severity="warning",
                        message=f"Printed <{keyword} {value}> value differs from IR value {action.get('value')}.",
                        raw_text=raw_text,
                    )
                )
        if requires_grant and keyword in STACKING_KEYWORDS and value is None:
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=path,
                    kind="stacking_keyword_missing_value",
                    severity="review",
                    message=f"<{keyword}> stacks by value and should normally include a numeric value.",
                    raw_text=raw_text,
                )
            )
        if keyword in NON_STACKING_KEYWORDS and value is not None:
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=path,
                    kind="non_stacking_keyword_has_value",
                    severity="review",
                    message=f"<{keyword}> does not stack by value under the comprehensive rules.",
                    raw_text=raw_text,
                )
            )
    return issues


def _expected_target_from_text(raw_text: str) -> Optional[Dict[str, Any]]:
    choice = _choice_phrase(raw_text)
    if not choice:
        return None
    selector = _selector_from_choice(choice)
    if not selector:
        return None
    expected: Dict[str, Any] = {"selector": selector, "filters": {}}
    count, variable_count = _choice_count(choice)
    if count is not None:
        expected["count"] = count
    if variable_count is not None:
        expected["variable_count"] = variable_count

    _apply_choice_qualifiers(expected, choice)
    return expected


def _expected_targets_from_text(raw_text: str) -> List[Dict[str, Any]]:
    expected = []
    for choice in _choice_phrases(raw_text):
        selector = _selector_from_choice(choice)
        if not selector:
            continue
        target: Dict[str, Any] = {"selector": selector, "filters": {}}
        count, variable_count = _choice_count(choice)
        if count is not None:
            target["count"] = count
        if variable_count is not None:
            target["variable_count"] = variable_count
        _apply_choice_qualifiers(target, choice)
        expected.append(target)
    return expected


def _choice_phrase(raw_text: str) -> str:
    phrases = _choice_phrases(raw_text)
    return phrases[0] if phrases else ""


def _choice_phrases(raw_text: str) -> List[str]:
    normalized = re.sub(r"\bLv\.", "Lv", raw_text, flags=re.IGNORECASE)
    phrases: List[str] = []
    for match in re.finditer(r"\bChoose\s+(.+?)(?:\.|,| instead\b)", normalized, flags=re.IGNORECASE):
        phrases.extend(
            phrase
            for phrase in _split_choice_phrase(match.group(1).strip())
            if "attack target" not in phrase.lower()
        )
    return phrases


def _split_choice_phrase(choice: str) -> List[str]:
    parts = re.split(
        r"\s*and\s+(?=\d+\s+(?:active\s+|rested\s+|damaged\s+)?(?:friendly|enemy|your|other)\b)",
        choice,
        flags=re.IGNORECASE,
    )
    return [part.strip() for part in parts if part.strip()]


def _selector_from_choice(choice: str) -> Optional[str]:
    lowered = choice.lower()
    if re.search(r"\bpilot paired with an? enemy unit\b", lowered):
        return "PAIRED_PILOT"
    if "from your trash" in lowered or "from your trash" in lowered:
        return "SELF_TRASH"
    if "from the trash" in lowered:
        return "SELF_TRASH"
    if "enemy" in lowered or "another player" in lowered:
        if "base/enemy shield" in lowered:
            return "ENEMY_BASE"
        if "shield" in lowered:
            return "OPPONENT_SHIELDS"
        if re.search(r"\benemy\s+units?\b", lowered):
            return "ENEMY_UNIT"
        if "base" in lowered:
            return "ENEMY_BASE"
    if "friendly" in lowered or "your " in lowered or "of your" in lowered:
        if "unit" in lowered:
            if re.search(r"\bother\b|\banother\b", lowered):
                return "OTHER_FRIENDLY_UNIT"
            return "FRIENDLY_UNIT"
        if "base" in lowered:
            return "FRIENDLY_BASE"
    return None


def _apply_choice_qualifiers(expected: Dict[str, Any], choice: str) -> None:
    lowered = choice.lower()
    if "rested" in lowered:
        expected["filters"]["state"] = "RESTED"
    if "active" in lowered:
        expected["filters"]["state"] = "ACTIVE"
    trait_filters = re.findall(r"\(([^)]+)\)", choice)
    if trait_filters:
        expected["filters"]["traits"] = [trait.strip() for trait in trait_filters if trait.strip()]
    if re.search(r"\bpurple\b", choice, re.IGNORECASE):
        expected["filters"]["color"] = "Purple"
    if re.search(r"\bUnit card\b|\bUnits?\b", choice, re.IGNORECASE) and expected["selector"] in {"SELF_TRASH"}:
        expected["filters"]["card_type"] = "UNIT"
    if re.search(r"\bBase card\b|\bBases?\b", choice, re.IGNORECASE) and expected["selector"] in {"SELF_TRASH"}:
        expected["filters"]["card_type"] = "BASE"
    stat_match = re.search(r"(?:with|that is|that are)\s+(?:Lv\.?|level)\s*\.?\s*(\d+)\s+or\s+lower", choice, re.IGNORECASE)
    if stat_match:
        expected["filters"]["level"] = {"operator": "<=", "value": int(stat_match.group(1))}
    hp_match = re.search(r"with\s+(\d+)\s+or\s+less\s+HP", choice, re.IGNORECASE)
    if hp_match:
        expected["filters"]["hp"] = {"operator": "<=", "value": int(hp_match.group(1))}
    ap_match = re.search(r"with\s+(\d+)\s+or\s+less\s+AP", choice, re.IGNORECASE)
    if ap_match:
        expected["filters"]["ap"] = {"operator": "<=", "value": int(ap_match.group(1))}
    if re.search(r"\bLink Unit", choice, re.IGNORECASE):
        expected["filters"]["is_linked"] = True
    paired_trait_match = re.search(r"paired with a \(([^)]+)\) Pilot", choice, re.IGNORECASE)
    if paired_trait_match:
        expected["filters"]["paired_pilot_traits"] = [paired_trait_match.group(1).strip()]
    if re.search(r"\bdamaged\b", choice, re.IGNORECASE):
        expected["filters"]["damaged"] = True
    keyword_match = re.search(r"with\s*[【<]([A-Za-z -]+)[】>]", choice, re.IGNORECASE)
    if keyword_match:
        expected["filters"]["has_keyword"] = _normalize_keyword_name(keyword_match.group(1)).lower()


def _choice_target_consumers(
    target_actions: List[tuple[str, Dict[str, Any]]],
    expected_count: int,
    raw_text: str,
) -> List[tuple[str, Dict[str, Any]]]:
    select_actions = [item for item in target_actions if item[1].get("type") == "SELECT_TARGET"]
    if select_actions:
        return select_actions[:expected_count]
    effect_consumers = [
        item
        for item in target_actions
        if not _looks_like_activation_cost(item[1], raw_text)
        and not _is_delayed_trigger_grant(item[1])
    ]
    return (effect_consumers or target_actions)[:expected_count]


def _looks_like_activation_cost(action: Dict[str, Any], raw_text: str) -> bool:
    target = action.get("target")
    selector = target.get("selector") if isinstance(target, dict) else target
    cost_text = re.split(r"\bChoose\b", raw_text, maxsplit=1, flags=re.IGNORECASE)[0]
    cost_text = cost_text.split("：", 1)[0].split(":", 1)[0]
    if "choose" in cost_text.lower():
        return False
    action_type = action.get("type")
    if action_type == "REST_UNIT":
        if selector == "SELF":
            return "rest this" in cost_text.lower()
        return selector in {"FRIENDLY_BASE", "SELF_BASE", "FRIENDLY_UNIT", "OTHER_FRIENDLY_UNIT"} and "rest" in cost_text.lower()
    if action_type in {"DESTROY_CARD", "DAMAGE_UNIT", "SET_ACTIVE"}:
        return selector == "SELF"
    return False


def _is_delayed_trigger_grant(action: Dict[str, Any]) -> bool:
    keyword = str(action.get("keyword") or "")
    return action.get("type") == "GRANT_KEYWORD" and (
        keyword.startswith("TRIGGER_")
        or keyword.startswith("ON_UNIT_")
        or keyword.startswith("ON_DEAL_")
    )


def _choice_count(choice: str) -> tuple[Optional[int], Optional[Dict[str, int]]]:
    range_match = re.match(r"1\s+to\s+(\d+)\b", choice)
    if range_match:
        return None, {"min": 1, "max": int(range_match.group(1))}
    count_match = re.match(r"(\d+)\b", choice)
    if count_match:
        return int(count_match.group(1)), None
    return None, None


def _keyword_requires_grant(raw_text: str, keyword: str) -> bool:
    keyword_text = keyword.replace("_", r"[- ]")
    keyword_pattern = rf"<\s*{keyword_text}(?:\s+\d+)?\s*>"
    if re.search(rf"^\s*(?:【[^】]+】\s*)?{keyword_pattern}", raw_text, flags=re.IGNORECASE):
        return True
    return bool(
        re.search(
            rf"\b(?:gain|gains|gained|grant|grants|get|gets)\s+{keyword_pattern}",
            raw_text,
            flags=re.IGNORECASE,
        )
    )


def _has_executable_support_actions(actions: Iterable[Dict[str, Any]], value: Optional[int]) -> bool:
    has_rest_self = False
    has_ap_bonus = False
    expected_modification = f"+{value}" if value is not None else None
    for _, action in _walk_actions(actions, "actions"):
        if action.get("type") == "REST_UNIT":
            target = action.get("target")
            selector = target.get("selector") if isinstance(target, dict) else target
            if selector == "SELF":
                has_rest_self = True
        if action.get("type") == "MODIFY_STAT" and str(action.get("stat", "")).upper() == "AP":
            target = action.get("target")
            selector = target.get("selector") if isinstance(target, dict) else target
            if selector in {"OTHER_FRIENDLY_UNIT", "FRIENDLY_UNIT"} and (
                expected_modification is None or action.get("modification") == expected_modification
            ):
                has_ap_bonus = True
    return has_rest_self and has_ap_bonus


def _compare_expected_filters(
    card_id: str,
    path: str,
    raw_text: str,
    expected: Dict[str, Any],
    target: Dict[str, Any],
    effect: Dict[str, Any],
) -> List[SemanticAuditIssue]:
    issues: List[SemanticAuditIssue] = []
    filters = target.get("filters", {}) if isinstance(target.get("filters"), dict) else {}
    for key, value in expected.get("filters", {}).items():
        if filters.get(key) != value:
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{path}.filters.{key}",
                    kind="target_filter_mismatch",
                    severity="fixable" if key == "state" else "warning",
                    message=f"Printed target requires filter {key}={value}, but IR has {filters.get(key)}.",
                    raw_text=raw_text,
                    recommendation="Encode printed target qualifications on action.target.filters.",
                )
            )
    required_condition = expected.get("requires_condition")
    if required_condition and not _has_condition_type(effect.get("conditions", []), required_condition):
        issues.append(
            SemanticAuditIssue(
                card_id=card_id,
                path=f"{path}.filters",
                kind="target_condition_missing",
                severity="review",
                message=f"Printed target requires {required_condition}, but the IR has no matching condition/filter.",
                raw_text=raw_text,
            )
        )
    return issues


def _expected_triggers(raw_text: str) -> set[str]:
    text = raw_text
    if re.search(r"^【Burst】\s*Activate this card's\s+【(?:Action|Main)】", text, flags=re.IGNORECASE):
        return {"BURST"}
    if "【Main】/【Action】" in text or "【Action】/【Main】" in text:
        return {"MAIN_PHASE", "ACTION_PHASE"}
    mapping = {
        "【Deploy】": "ON_DEPLOY",
        "【Attack】": "ON_ATTACK",
        "【Destroyed】": "ON_DESTROYED",
        "【When Paired】": "ON_PAIRED",
        "【When Linked】": "ON_LINKED",
        "【Burst】": "BURST",
        "【Main】": "MAIN_PHASE",
        "【Action】": "ACTION_PHASE",
        "【Activate･Main】": "ACTIVATE_MAIN",
        "【Activate･Action】": "ACTIVATE_ACTION",
    }
    return {trigger for marker, trigger in mapping.items() if marker in text}


def _normalize_effect_triggers(effect: Dict[str, Any], raw_text: str) -> str:
    expected = _expected_triggers(raw_text)
    if not expected:
        return ""
    current = [trigger for trigger in effect.get("triggers", []) if isinstance(trigger, str)]
    replaced_gating = [trigger for trigger in current if not trigger.startswith("WHILE_")]
    if len(replaced_gating) != len(current):
        current = replaced_gating
    changed = False
    for trigger in sorted(expected):
        if trigger not in current:
            current.append(trigger)
            changed = True
    if current != effect.get("triggers", []):
        effect["triggers"] = current
        changed = True
    if expected & {"ACTIVATE_MAIN", "ACTIVATE_ACTION"} and effect.get("effect_type") == "TRIGGERED":
        effect["effect_type"] = "ACTIVATED"
        changed = True
    return "Mapped printed timing markers to runtime triggers." if changed else ""


def _canonicalize_action_shape(action: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
    normalized = copy.deepcopy(action)
    if "type" not in normalized and "action_type" in normalized:
        normalized["type"] = normalized.pop("action_type")
    if isinstance(normalized.get("type"), str):
        normalized["type"] = _normalize_action_type(normalized["type"])
    if normalized.get("type") == "ON_PAIR_PILOT":
        normalized["type"] = "PAIR_PILOT"
    for legacy_key in ("pay_costs", "require_cost_payment", "cost_payment"):
        if legacy_key in normalized and "pay_cost" not in normalized:
            normalized["pay_cost"] = normalized.pop(legacy_key)
        else:
            normalized.pop(legacy_key, None)
    if "on_true" in normalized and "true_actions" not in normalized:
        normalized["true_actions"] = normalized.pop("on_true")
    if "on_false" in normalized and "false_actions" not in normalized:
        normalized["false_actions"] = normalized.pop("on_false")
    if "success_actions" in normalized and "true_actions" not in normalized:
        normalized["true_actions"] = normalized.pop("success_actions")

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

    action_type = normalized.get("type")
    if action_type == "MODIFY_STAT":
        printed = _printed_stat_modifier(raw_text, normalized.get("stat"))
        if printed:
            normalized["stat"], normalized["modification"] = printed
        elif isinstance(normalized.get("modification"), int):
            amount = normalized["modification"]
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        elif "modification" not in normalized and isinstance(normalized.get("amount"), int):
            amount = normalized.pop("amount")
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        if normalized.get("stat"):
            normalized["stat"] = str(normalized["stat"]).upper()
    elif action_type == "MODIFY_COST":
        if "modification" not in normalized and "cost" in normalized:
            normalized["modification"] = f"={normalized.pop('cost')}"
        if isinstance(normalized.get("modification"), int):
            amount = normalized["modification"]
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        elif "modification" not in normalized and isinstance(normalized.get("amount"), int):
            amount = normalized.pop("amount")
            normalized["modification"] = f"+{amount}" if amount >= 0 else str(amount)
        normalized.setdefault("scope", "PLAY")
    elif action_type == "GRANT_KEYWORD":
        if not normalized.get("keyword"):
            keyword = _standalone_or_granted_keyword(raw_text)
            if keyword:
                normalized["keyword"] = keyword
        if normalized.get("keyword"):
            normalized["keyword"] = _normalize_keyword_name(normalized["keyword"])
        if normalized.get("keyword") in NON_STACKING_KEYWORDS:
            normalized.pop("value", None)

    if action_type == "DEPLOY_FROM_ZONE":
        source_zone = str(normalized.get("source_zone") or "").upper()
        if source_zone in {"SELF_TRASH", "TRASH"}:
            normalized["source_zone"] = "TRASH"
        elif source_zone in {"SELF_DECK", "DECK"}:
            normalized["source_zone"] = "DECK"
        elif source_zone in {"BANISH", "REMOVAL", "REMOVAL_AREA"}:
            normalized["source_zone"] = "BANISH"
        if isinstance(normalized.get("target"), dict) and "card_type" not in normalized["target"]:
            filters = normalized["target"].get("filters", {})
            if isinstance(filters, dict) and filters.get("card_type"):
                normalized["target"]["card_type"] = filters["card_type"]

    if action_type == "MODIFY_STAT" and "modification" not in normalized and isinstance(normalized.get("modifier"), dict):
        operation = str(normalized["modifier"].get("operation") or "ADD").upper()
        normalized["modification"] = "-COUNT_RESULT" if operation in {"SUBTRACT", "MINUS"} else "+COUNT_RESULT"

    return normalized


def _canonicalize_condition_shape(condition: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
    normalized = copy.deepcopy(condition)
    if not normalized.get("type") and normalized.get("condition_type"):
        normalized["type"] = str(normalized.pop("condition_type")).strip().upper()
    elif not normalized.get("type") and normalized.get("condition"):
        normalized["type"] = str(normalized.pop("condition")).strip().upper()
    elif normalized.get("condition_type"):
        normalized.pop("condition_type", None)
    if "target_selector" in normalized and "target" not in normalized:
        normalized["target"] = {"selector": _normalize_selector(normalized.pop("target_selector"))}
    elif "selector" in normalized and "target" not in normalized:
        normalized["target"] = {"selector": _normalize_selector(normalized.pop("selector"))}
    elif isinstance(normalized.get("target"), dict):
        normalized["target"] = _normalize_target_spec(normalized["target"])
    elif isinstance(normalized.get("target"), str):
        normalized["target"] = {"selector": _normalize_selector(normalized["target"])}
    if "op" in normalized and "operator" not in normalized:
        normalized["operator"] = normalized.pop("op")
    else:
        normalized.pop("op", None)
    if normalized.get("type") in {"CHECK_TRAIT", "CHECK_COLOR"} and "value" in normalized:
        if normalized["type"] == "CHECK_TRAIT" and "traits" not in normalized:
            trait_value = normalized.pop("value")
            normalized["traits"] = trait_value if isinstance(trait_value, list) else [trait_value]
        elif normalized["type"] == "CHECK_COLOR" and "color" not in normalized:
            normalized["color"] = normalized.pop("value")
    if "trait" in normalized and "traits" not in normalized:
        normalized["traits"] = [normalized.pop("trait")]
    if "filters" in normalized and isinstance(normalized.get("target"), dict):
        filters = _merge_filter_specs(normalized["target"].get("filters", {}), normalized.pop("filters"))
        if filters:
            normalized["target"]["filters"] = filters
    if "card_filters" in normalized and isinstance(normalized.get("target"), dict):
        filters = _merge_filter_specs(normalized["target"].get("filters", {}), normalized.pop("card_filters"))
        if filters:
            normalized["target"]["filters"] = filters
    if normalized.get("type") == "CHECK_TURN" and "turn_owner" not in normalized:
        turn_value = str(normalized.get("value") or normalized.get("owner") or "").upper()
        if turn_value in {"YOUR_TURN", "YOUR", "SELF", "YOU"}:
            normalized["turn_owner"] = "SELF"
        elif turn_value in {"OPPONENT_TURN", "OPPONENT", "ENEMY"}:
            normalized["turn_owner"] = "OPPONENT"
    state = normalized.get("state") or normalized.get("value")
    if normalized.get("type") == "CHECK_CARD_STATE" and isinstance(state, str):
        normalized["state"] = state.upper()
        normalized.pop("value", None)
    return normalized


def _normalize_invalid_state_conditions(effect: Dict[str, Any], raw_text: str) -> List[tuple[str, str]]:
    conditions = effect.get("conditions", [])
    if not isinstance(conditions, list):
        return []

    kept: List[Dict[str, Any]] = []
    changes: List[tuple[str, str]] = []
    for index, condition in enumerate(conditions):
        if not isinstance(condition, dict) or condition.get("type") != "CHECK_CARD_STATE":
            kept.append(condition)
            continue
        state = condition.get("state") or condition.get("value")
        state_text = str(state).upper()
        target = condition.get("target")

        if state_text in {"ACTIVE", "RESTED", "PAIRED", "LINKED", "DESTROYED", "ATTACKING"}:
            condition["state"] = state_text
            condition.pop("value", None)
            kept.append(condition)
            if state != state_text:
                changes.append((f"conditions[{index}]", f"Canonicalized card state {state} to {state_text}."))
            continue

        if state_text == "DAMAGED":
            kept.append(
                {
                    "type": "CHECK_DAMAGE",
                    "target": target or {"selector": "SELF"},
                    "operator": ">",
                    "value": 0,
                }
            )
            changes.append((f"conditions[{index}]", "Converted DAMAGED state to CHECK_DAMAGE."))
            continue

        if state_text in {"IN_PLAY", "PLAY"}:
            kept.append(
                {
                    "type": "CHECK_TARGET",
                    "target": target or {"selector": "SELF"},
                    "exists": True,
                }
            )
            changes.append((f"conditions[{index}]", f"Converted {state_text} state to target existence check."))
            continue

        if state_text in {"TOKEN", "IS_TOKEN"}:
            kept.append(
                {
                    "type": "CHECK_TARGET",
                    "target": target or {"selector": "SELF"},
                    "filters": {"is_token": True},
                }
            )
            changes.append((f"conditions[{index}]", "Converted token state to target filter check."))
            continue

        if state_text in {"BATTLING", "BATTLING_UNIT"}:
            kept.append(
                {
                    "type": "CHECK_TARGET",
                    "target_type": "UNIT",
                    "event": "BATTLE_TARGET",
                }
            )
            changes.append((f"conditions[{index}]", "Converted battling state to battle target event check."))
            continue

        if state_text == "BLOCKING":
            kept.append(
                {
                    "type": "CHECK_TARGET",
                    "target_type": "UNIT",
                    "event": "BLOCKING_UNIT",
                    "target": target or {"selector": "ENEMY_UNIT"},
                }
            )
            changes.append((f"conditions[{index}]", "Converted blocking state to blocking target event check."))
            continue

        if state_text == "RECEIVING_EFFECT_DAMAGE":
            triggers = effect.setdefault("triggers", [])
            if "ON_RECEIVE_EFFECT_DAMAGE" not in triggers:
                triggers[:] = ["ON_RECEIVE_EFFECT_DAMAGE", *[trigger for trigger in triggers if trigger != "ON_RECEIVE_EFFECT_DAMAGE"]]
            kept.append(
                {
                    "type": "CHECK_TARGET",
                    "target": target or {"selector": "SELF"},
                    "event": "RECEIVING_EFFECT_DAMAGE",
                }
            )
            changes.append((f"conditions[{index}]", "Converted receiving-effect-damage state to ON_RECEIVE_EFFECT_DAMAGE event check."))
            continue

        if state_text == "FROM_TRASH":
            kept.append(
                {
                    "type": "CHECK_TARGET",
                    "source_zone": "TRASH",
                    "event": "DEPLOY_SOURCE",
                }
            )
            changes.append((f"conditions[{index}]", "Converted from-trash state to deploy source-zone check."))
            continue

        if state_text in {"ACTIVATED", "USED_EX_RESOURCE"}:
            kept.append(
                {
                    "type": "CHECK_TARGET",
                    "event": state_text,
                    "target": target or {"selector": "SELF"},
                }
            )
            changes.append((f"conditions[{index}]", f"Converted {state_text} state to trigger-data check."))
            continue

        if state_text in {"CANNOT_BE_ACTIVE", "CANNOT_BE_PAIRED"}:
            changes.append((f"conditions[{index}]", f"Removed prohibition state {state_text}; represented by effect metadata, not a condition."))
            continue

        if state_text == "DESTROYED_BY_BATTLE_DAMAGE":
            triggers = effect.setdefault("triggers", [])
            if "ON_UNIT_DESTROYED_BY_DAMAGE" not in triggers:
                triggers[:] = ["ON_UNIT_DESTROYED_BY_DAMAGE", *[trigger for trigger in triggers if trigger != "ON_UNIT_DESTROYED_BY_DAMAGE"]]
            changes.append((f"conditions[{index}]", "Moved destroyed-by-battle-damage state into ON_UNIT_DESTROYED_BY_DAMAGE trigger."))
            continue

        if state_text in {"TRUE", "ENEMY", "SHIELD", "TRASH"}:
            changes.append((f"conditions[{index}]", f"Removed non-state CHECK_CARD_STATE value {state}."))
            continue

        kept.append(condition)

    if len(kept) != len(conditions) or changes:
        effect["conditions"] = kept

    if "【During Link】" in raw_text and not _has_condition_type(effect.get("conditions", []), "CHECK_LINK_STATUS"):
        effect.setdefault("conditions", []).append({"type": "CHECK_LINK_STATUS", "target": {"selector": "SELF"}, "is_linked": True})
        changes.append(("conditions", "Added CHECK_LINK_STATUS for During Link gated text."))
    elif "【During Pair】" in raw_text and not _has_condition_type(effect.get("conditions", []), "CHECK_PAIR_STATUS"):
        effect.setdefault("conditions", []).append({"type": "CHECK_PAIR_STATUS", "target": {"selector": "SELF"}, "state": "PAIRED"})
        changes.append(("conditions", "Added CHECK_PAIR_STATUS for During Pair gated text."))
    return changes


def _normalize_event_conditions(effect: Dict[str, Any]) -> List[tuple[str, str]]:
    conditions = effect.get("conditions", [])
    if not isinstance(conditions, list):
        return []
    event_condition_triggers = {"ON_UNIT_DESTROYED_BY_DAMAGE"}
    kept = []
    changes = []
    triggers = effect.setdefault("triggers", [])
    for index, condition in enumerate(conditions):
        condition_type = condition.get("type") if isinstance(condition, dict) else None
        if condition_type in event_condition_triggers:
            if condition_type not in triggers:
                triggers.append(condition_type)
            changes.append((f"conditions[{index}]", f"Moved event condition {condition_type} into triggers."))
            continue
        kept.append(condition)
    if changes:
        effect["conditions"] = kept
    return changes


def _normalize_action_type(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().upper()
    return {
        "SELECTED_CARD": "SELECT_TARGET",
        "SELECTED_TARGET": "SELECT_TARGET",
    }.get(normalized, normalized)


def _normalize_target_spec(target: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(target)
    if "selector" in normalized:
        normalized["selector"] = _normalize_selector(normalized["selector"])
    if "filters" in normalized:
        filters = _merge_filter_specs(normalized["filters"])
        if filters:
            normalized["filters"] = filters
        else:
            normalized.pop("filters", None)
    return normalized


def _normalize_selector(selector: Any) -> Any:
    if not isinstance(selector, str):
        return selector
    aliases = {
        "BOTH_PLAYERS": "ALL_PLAYERS",
        "DECK": "SELF_DECK",
        "ENEMY_SHIELD": "OPPONENT_SHIELDS",
        "ENEMY_SHIELDS": "OPPONENT_SHIELDS",
        "FRIENDLY_HAND": "SELF_HAND",
        "FRIENDLY_SHIELD": "SELF_SHIELDS",
        "FRIENDLY_SHIELDS": "SELF_SHIELDS",
        "OWN_DECK": "SELF_DECK",
        "OWN_HAND": "SELF_HAND",
        "OWN_SHIELDS": "SELF_SHIELDS",
        "SELECTED_TARGET": "SELECTED_CARD",
        "SELECTED_UNIT": "SELECTED_CARD",
    }
    normalized = selector.strip().upper()
    return aliases.get(normalized, normalized)


def _merge_filter_specs(*filter_specs: Any) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for filters in filter_specs:
        merged.update(_filters_to_dict(filters))
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
    normalized = dict(filters)
    if "op" in normalized and "operator" not in normalized:
        normalized["operator"] = normalized.pop("op")
    else:
        normalized.pop("op", None)
    if "type" in normalized and "card_type" not in normalized:
        normalized["card_type"] = normalized.pop("type")
    if "card_type" in normalized and isinstance(normalized["card_type"], str):
        normalized["card_type"] = normalized["card_type"].upper()
    if "HP" in normalized and "hp" not in normalized:
        normalized["hp"] = normalized.pop("HP")
    else:
        normalized.pop("HP", None)
    if "AP" in normalized and "ap" not in normalized:
        normalized["ap"] = normalized.pop("AP")
    else:
        normalized.pop("AP", None)
    if "max_hp" in normalized and "hp" not in normalized:
        normalized["hp"] = normalized.pop("max_hp")
    else:
        normalized.pop("max_hp", None)
    if "link_status" in normalized and "is_linked" not in normalized:
        link_status = str(normalized.pop("link_status")).upper()
        normalized["is_linked"] = link_status in {"LINKED", "TRUE", "YES"}
    if "has_paired_pilot" in normalized:
        has_pilot = bool(normalized.pop("has_paired_pilot"))
        if has_pilot and "paired_pilot_traits" not in normalized:
            normalized["paired_pilot_traits"] = []
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
    if "paired_with_pilot_trait" in normalized and "paired_pilot_traits" not in normalized:
        normalized["paired_pilot_traits"] = [normalized.pop("paired_with_pilot_trait")]
    if "paired_pilot_trait" in normalized and "paired_pilot_traits" not in normalized:
        normalized["paired_pilot_traits"] = [normalized.pop("paired_pilot_trait")]
    if "linked" in normalized and "is_linked" not in normalized:
        normalized["is_linked"] = normalized.pop("linked")
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
    for key in ("level", "ap", "hp"):
        if isinstance(normalized.get(key), dict) and len(normalized[key]) == 1:
            op, value = next(iter(normalized[key].items()))
            if op in {"<=", ">=", "==", "!=", "<", ">"}:
                normalized[key] = {"operator": op, "value": value}
    stat = str(normalized.get("stat") or normalized.get("stat_type") or "").upper()
    if stat in {"LEVEL", "LV", "AP", "HP"} and "operator" in normalized and "value" in normalized:
        key = "level" if stat in {"LEVEL", "LV"} else stat.lower()
        return {key: {"operator": normalized["operator"], "value": normalized["value"]}}
    if stat in {"LEVEL", "LV", "AP", "HP"}:
        key = "level" if stat in {"LEVEL", "LV"} else stat.lower()
        if key in normalized:
            normalized.pop("stat", None)
            normalized.pop("stat_type", None)
            normalized.pop("operator", None)
        elif "value" not in normalized:
            normalized.pop("stat", None)
            normalized.pop("stat_type", None)
            normalized.pop("operator", None)
    for unsupported_key in (
        "amount",
        "can_target_player",
        "condition",
        "conditions",
        "count",
        "limit",
        "most_units_owner",
        "owner",
        "quantity",
        "sort_by",
        "sort_order",
        "stat_filters",
        "target",
        "value",
    ):
        normalized.pop(unsupported_key, None)
    for key in ("level", "ap", "hp"):
        value_key = f"{key}_value"
        if value_key in normalized and isinstance(normalized.get(key), str) and normalized[key] in {"<=", ">=", "==", "!=", "<", ">"}:
            normalized[key] = {"operator": normalized.pop(key), "value": normalized.pop(value_key)}
        elif value_key in normalized and "operator" in normalized:
            normalized[key] = {"operator": normalized.pop("operator"), "value": normalized.pop(value_key)}
        elif key in normalized and "operator" in normalized and not isinstance(normalized[key], dict):
            normalized[key] = {"operator": normalized.pop("operator"), "value": normalized[key]}
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


def _state_conditions_by_selector(conditions: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    states = {}
    for condition in _walk_conditions(conditions):
        if condition.get("type") != "CHECK_CARD_STATE" or condition.get("operator", "==") != "==":
            continue
        selector = _condition_selector(condition)
        state = condition.get("state") or condition.get("value")
        if selector and state in {"ACTIVE", "RESTED"}:
            states[selector] = state
    return states


def _remove_moved_target_qualification_conditions(
    effect: Dict[str, Any],
    expected: Optional[Dict[str, Any]],
) -> List[tuple[str, str]]:
    if not expected:
        return []
    expected_state = expected.get("filters", {}).get("state")
    expected_selector = expected.get("selector")
    if expected_state not in {"ACTIVE", "RESTED"} or expected_selector not in {"ENEMY_UNIT", "FRIENDLY_UNIT"}:
        return []

    kept = []
    removed = []
    for index, condition in enumerate(effect.get("conditions", [])):
        selector = _condition_selector(condition) if isinstance(condition, dict) else None
        state = condition.get("state") or condition.get("value") if isinstance(condition, dict) else None
        if (
            isinstance(condition, dict)
            and condition.get("type") == "CHECK_CARD_STATE"
            and selector == expected_selector
            and state == expected_state
        ):
            removed.append((f"conditions[{index}]", str(state)))
        else:
            kept.append(condition)
    if removed:
        effect["conditions"] = kept
    return removed


def _normalize_selected_target_workflow(
    effect: Dict[str, Any],
    expected: Optional[Dict[str, Any]],
    raw_text: str,
) -> List[str]:
    expected_targets = _expected_targets_from_text(raw_text) or ([expected] if expected else [])
    if not expected_targets or not _has_selected_target_pronoun(raw_text):
        return []

    actions = effect.get("actions", [])
    if not isinstance(actions, list):
        return []
    if any(isinstance(action, dict) and action.get("type") == "SELECT_TARGET" for action in actions):
        return []

    target_actions = [
        action
        for action in actions
        if isinstance(action, dict)
        and action.get("type") in TARGET_ACTION_TYPES
        and action.get("type") != "SELECT_TARGET"
        and isinstance(action.get("target"), dict)
        and not _looks_like_activation_cost(action, raw_text)
    ]
    inferred_action = _infer_selected_target_consumer(raw_text)
    if not target_actions and inferred_action:
        target_actions = [inferred_action]
        actions = [*actions, inferred_action]
    if not target_actions:
        return []

    rewritable: List[Dict[str, Any]] = []
    for action in target_actions:
        selector = action["target"].get("selector")
        if selector == "SELECTED_CARD":
            rewritable.append(action)
            continue
        if any(selector == item["selector"] for item in expected_targets):
            rewritable.append(action)
            continue
        if any(item["selector"] == "FRIENDLY_UNIT" and selector == "OTHER_FRIENDLY_UNIT" for item in expected_targets):
            rewritable.append(action)
            continue
        if (
            action.get("type") == "GRANT_PROTECTION"
            and any(item["selector"] in {"FRIENDLY_UNIT", "OTHER_FRIENDLY_UNIT"} for item in expected_targets)
            and selector == "ENEMY_UNIT"
            and "can't receive battle damage" in raw_text
        ):
            rewritable.append(action)
            continue
        return []

    select_targets = [_select_target_action(item, append=index > 0) for index, item in enumerate(expected_targets)]
    effect["actions"] = [*select_targets, *actions]
    for action in rewritable:
        action["target"] = {"selector": "SELECTED_CARD"}
    return ["actions"]


def _normalize_existing_select_targets(effect: Dict[str, Any], raw_text: str) -> List[str]:
    expected_targets = _expected_targets_from_text(raw_text)
    if not expected_targets:
        return []
    actions = effect.get("actions", [])
    if not isinstance(actions, list):
        return []
    select_actions = [
        action
        for action in actions
        if isinstance(action, dict)
        and action.get("type") == "SELECT_TARGET"
        and isinstance(action.get("target"), dict)
    ]
    changes: List[str] = []
    for index, (action, expected) in enumerate(zip(select_actions, expected_targets)):
        target = action["target"]
        changed = _align_target_to_expected_choice(target, expected)
        if changed:
            changes.append(f"actions[{index}].target")
    return changes


def _align_target_to_expected_choice(target: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    changed = False
    if target.get("selector") != expected["selector"] and _selectors_are_rewritable(target.get("selector"), expected["selector"]):
        target["selector"] = expected["selector"]
        changed = True
    if expected.get("count") is not None and target.get("count") != expected["count"]:
        target["count"] = expected["count"]
        changed = True
    if expected.get("variable_count") is not None and target.get("variable_count") != expected["variable_count"]:
        target["variable_count"] = expected["variable_count"]
        changed = True
    for key, value in expected.get("filters", {}).items():
        current_value = target.get("filters", {}).get(key)
        if key == "card_type" and current_value not in {None, "UNIT", "PILOT", "COMMAND", "BASE", "RESOURCE"}:
            current_value = None
        if current_value != value:
            target.setdefault("filters", {})[key] = copy.deepcopy(value)
            changed = True
    return changed


def _selectors_are_rewritable(actual: Any, expected: str) -> bool:
    if not isinstance(actual, str):
        return False
    if actual == expected:
        return True
    compatible = {
        "FRIENDLY_UNIT": {"OTHER_FRIENDLY_UNIT"},
        "OTHER_FRIENDLY_UNIT": {"FRIENDLY_UNIT"},
        "ENEMY_UNIT": {"FRIENDLY_UNIT", "OTHER_FRIENDLY_UNIT", "SELF", "PAIRED_PILOT"},
        "FRIENDLY_BASE": {"SELF", "FRIENDLY_UNIT"},
        "SELF_TRASH": {"FRIENDLY_UNIT", "SELF", "SELECTED_CARD"},
    }
    return actual in compatible.get(expected, set())


def _select_target_action(expected: Dict[str, Any], *, append: bool = False) -> Dict[str, Any]:
    action = {
        "type": "SELECT_TARGET",
        "target": {
            "selector": expected["selector"],
            "selection_method": "CHOOSE",
        },
    }
    if expected.get("count") is not None:
        action["target"]["count"] = expected["count"]
    if expected.get("variable_count") is not None:
        action["target"]["variable_count"] = expected["variable_count"]
    if expected.get("filters"):
        action["target"]["filters"] = copy.deepcopy(expected["filters"])
    if append:
        action["append"] = True
    return action


def _infer_selected_target_consumer(raw_text: str) -> Optional[Dict[str, Any]]:
    text = _strip_parenthetical_rules(raw_text)
    target = {"selector": "SELECTED_CARD"}
    if re.search(r"\b[Rr]eturn (?:it|them) to (?:its |their )?owner'?s hands?\b", text):
        return {"type": "RETURN_TO_HAND", "target": target}
    if re.search(r"\b[Rr]est (?:it|them)\b", text):
        return {"type": "REST_UNIT", "target": target}
    if re.search(r"\b[Dd]estroy (?:it|them)\b", text):
        return {"type": "DESTROY_CARD", "target": target}
    if re.search(r"\b[Ss]et (?:it|them) as active\b", text):
        return {"type": "SET_ACTIVE", "target": target}
    if re.search(r"\b[Dd]eploy (?:it|them)\b", text):
        return {"type": "DEPLOY_FROM_ZONE", "target": target, "source_zone": "TRASH"}
    if re.search(r"\b[Pp]air (?:it|them) with this Unit\b", text):
        return {"type": "PAIR_PILOT", "target": target, "paired_with": {"selector": "SELF"}}
    reduce_match = re.search(r"\breduce the next damage (?:it|they) receives? by (\d+)\b", text, flags=re.IGNORECASE)
    if reduce_match:
        return {"type": "REDUCE_DAMAGE", "target": target, "amount": int(reduce_match.group(1)), "duration": "THIS_TURN", "uses": 1}
    damage_match = re.search(r"\b[Dd]eal (\d+) damage to (?:it|them)\b", text)
    if damage_match:
        return {"type": "DAMAGE_UNIT", "target": target, "amount": int(damage_match.group(1)), "damage_type": "EFFECT"}
    recover_match = re.search(r"\b(?:It|They|This Unit) recovers? (\d+) HP\b", text)
    if recover_match:
        return {"type": "RECOVER_HP", "target": target, "amount": int(recover_match.group(1))}
    stat_match = re.search(r"\b(?:It|They|This Unit) gets (AP|HP)\s*([+-])\s*(\d+)\b", text, flags=re.IGNORECASE)
    if stat_match:
        action: Dict[str, Any] = {
            "type": "MODIFY_STAT",
            "target": target,
            "stat": stat_match.group(1).upper(),
            "modification": f"{stat_match.group(2)}{stat_match.group(3)}",
        }
        duration = _duration_from_text(text)
        if duration:
            action["duration"] = duration
        return action
    keyword_match = re.search(
        r"\b(?:it|they|this Unit) gains?\s*[<【]([A-Za-z -]+)(?:\s+(\d+))?[>】]",
        text,
        flags=re.IGNORECASE,
    )
    if keyword_match:
        action = {"type": "GRANT_KEYWORD", "target": target, "keyword": _normalize_keyword_name(keyword_match.group(1))}
        if keyword_match.group(2):
            action["value"] = int(keyword_match.group(2))
        duration = _duration_from_text(text)
        if duration:
            action["duration"] = duration
        return action
    return None


def _duration_from_text(text: str) -> Optional[str]:
    lowered = text.lower()
    if "during this battle" in lowered:
        return "THIS_BATTLE"
    if "during this turn" in lowered or "until end of turn" in lowered:
        return "THIS_TURN"
    return None


def _strip_parenthetical_rules(text: str) -> str:
    return re.sub(r"\([^)]*\)", "", text)


def _has_selected_target_pronoun(raw_text: str) -> bool:
    return bool(
        re.search(
            r"(?:^|[.!?]\s+)(?:It|They|Then it|Then they|Return it|Return them|Rest it|Rest them|Set it|Set them|Destroy it|Destroy them|Deploy it|Deploy them|Pair it|Pair them)\b|\b(?:to it|to them|it gets|they get|it receives|they receive|it would receive|they would receive|it may choose|they may choose|them to|return it|return them|rest it|rest them|set it|set them|destroy it|destroy them|deploy it|deploy them|pair it|pair them|next damage it receives|next damage they receive)\b",
            raw_text,
            flags=re.IGNORECASE,
        )
    )


def _normalize_clause_semantics(effect: Dict[str, Any], raw_text: str) -> List[tuple[str, str]]:
    actions = effect.get("actions", [])
    if not isinstance(actions, list) or not actions:
        return []
    lowered = raw_text.lower()
    changes: List[tuple[str, str]] = []

    if "if you do" in lowered and not _has_success_gated_action(actions) and len(actions) >= 2:
        first, *follow_up = actions
        if isinstance(first, dict) and all(isinstance(action, dict) for action in follow_up):
            first["next_if_success"] = follow_up
            effect["actions"] = [first]
            actions = effect["actions"]
            changes.append(("actions", "Moved follow-up actions into next_if_success for If you do semantics."))

    if "you may" in lowered and not _has_optional_action(actions):
        effect["actions"] = [{"type": "OPTIONAL_ACTION", "optional_actions": actions}]
        changes.append(("actions", "Wrapped actions in OPTIONAL_ACTION for optional printed text."))

    return changes


def _condition_selector(condition: Dict[str, Any]) -> Optional[str]:
    target = condition.get("target")
    return target.get("selector") if isinstance(target, dict) else target


def _walk_actions(actions: Iterable[Dict[str, Any]], path: str) -> Iterable[tuple[str, Dict[str, Any]]]:
    for index, action in enumerate(actions or []):
        if not isinstance(action, dict):
            continue
        action_path = f"{path}[{index}]"
        yield action_path, action
        for key in CHAIN_KEYS:
            yield from _walk_actions(_as_list(action.get(key)), f"{action_path}.{key}")
        for key in BRANCH_ACTION_KEYS:
            yield from _walk_actions(_as_list(action.get(key)), f"{action_path}.{key}")
        conditional_next = action.get("conditional_next")
        if isinstance(conditional_next, dict):
            yield from _walk_actions(_as_list(conditional_next.get("actions")), f"{action_path}.conditional_next.actions")


def _walk_conditions(conditions: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for _, condition in _walk_conditions_with_paths(conditions, "conditions"):
        yield condition


def _walk_conditions_with_paths(conditions: Iterable[Dict[str, Any]], path: str) -> Iterable[tuple[str, Dict[str, Any]]]:
    for index, condition in enumerate(conditions or []):
        if isinstance(condition, dict):
            yield f"{path}[{index}]", condition


def _has_condition_type(conditions: Iterable[Dict[str, Any]], condition_type: str) -> bool:
    return any(condition.get("type") == condition_type for condition in _walk_conditions(conditions))


def _has_success_gated_action(actions: Iterable[Dict[str, Any]]) -> bool:
    return any(
        isinstance(action, dict) and (action.get("next_if_success") or action.get("conditional_next"))
        for _, action in _walk_actions(actions or [], "actions")
    )


def _has_ordered_multi_action(actions: Iterable[Dict[str, Any]]) -> bool:
    return len([action for action in actions or [] if isinstance(action, dict)]) >= 2


def _has_optional_action(actions: Iterable[Dict[str, Any]]) -> bool:
    return any(
        isinstance(action, dict) and (action.get("type") == "OPTIONAL_ACTION" or action.get("optional") is True)
        for _, action in _walk_actions(actions or [], "actions")
    )


def _missing_action_issue(card_id: str, path: str, kind: str, action_type: str, raw_text: str) -> SemanticAuditIssue:
    return SemanticAuditIssue(
        card_id=card_id,
        path=f"{path}.actions",
        kind=kind,
        severity="warning",
        message=f"Printed text implies {action_type}, but no matching action was found.",
        raw_text=raw_text,
    )


def _load_authority_texts(
    normalized_cards_path: str | Path | None,
    card_database_dir: str | Path | None,
) -> Dict[str, List[str]]:
    authority: Dict[str, List[str]] = {}
    if normalized_cards_path and Path(normalized_cards_path).exists():
        cards = json.loads(Path(normalized_cards_path).read_text(encoding="utf-8"))
        for card in _card_records(cards):
            if card.get("ID"):
                authority[str(card["ID"])] = _as_text_list(card.get("Effect"))
    if card_database_dir and Path(card_database_dir).exists():
        for path in sorted(Path(card_database_dir).glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for card in _card_records(data):
                if card.get("ID"):
                    authority[str(card["ID"])] = _as_text_list(card.get("Effect"))
    return authority


def _card_records(data: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(data, dict):
        yield data
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item


def _load_effect_file(path: Path) -> Dict[str, Any]:
    effect_data = json.loads(path.read_text(encoding="utf-8"))
    effect_data.setdefault("card_id", path.name)
    return effect_data


def _effect_raw_text(effect: Dict[str, Any]) -> str:
    return _normalize_text(effect.get("metadata", {}).get("raw_text") or effect.get("description") or "")


def _as_text_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _normalize_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _strip_markup(text: str) -> str:
    return _normalize_text(text.replace("<br>", ";").replace("<BR>", ";"))


def _normalize_keyword_name(keyword: Any) -> str:
    normalized = str(keyword).strip().upper().replace("-", "_").replace(" ", "_")
    return {
        "HIGH_MANEUVERS": "HIGH_MANEUVER",
    }.get(normalized, normalized)


def _standalone_or_granted_keyword(raw_text: str) -> Optional[str]:
    match = re.search(r"<([A-Za-z -]+)(?:\s+\d+)?>", raw_text)
    if match:
        keyword = _normalize_keyword_name(match.group(1))
        return keyword if _keyword_requires_grant(raw_text, keyword) else None
    match = re.search(r"^\s*【(Blocker|First Strike|High-Maneuver|Suppression)】", raw_text, flags=re.IGNORECASE)
    if not match:
        return None
    return _normalize_keyword_name(match.group(1))


def _group_issues(issues: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for issue in issues:
        buckets[(str(issue.get("kind", "")), str(issue.get("severity", "validation")))].append(issue)
    return [
        {
            "kind": kind,
            "severity": severity,
            "count": len(group_issues),
            "examples": sorted({str(issue.get("card_id", "")) for issue in group_issues})[:10],
        }
        for (kind, severity), group_issues in sorted(
            buckets.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit ExBurst IR against printed card text semantics")
    parser.add_argument("--output-dir", default="card_effects_exburst", help="ExBurst IR directory")
    parser.add_argument("--normalized-cards", default="exburst_cards_normalized.json", help="Normalized card database JSON")
    parser.add_argument("--card-database-dir", default="card_database", help="Per-card database directory")
    parser.add_argument("--json-out", help="Write machine-readable audit report")
    parser.add_argument("--markdown-out", help="Write markdown audit summary")
    parser.add_argument("--llm-queue-out", help="Write cards with review-level semantic issues for LLM test generation")
    parser.add_argument("--fix", action="store_true", help="Apply conservative normalizations in-place")
    args = parser.parse_args()

    fix_summary = apply_normalizations(args.output_dir) if args.fix else None
    audit = audit_exburst_semantics(
        args.output_dir,
        normalized_cards_path=args.normalized_cards,
        card_database_dir=args.card_database_dir,
    )
    if fix_summary is not None:
        audit["fix_summary"] = fix_summary
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown_out:
        write_markdown_report(audit, args.markdown_out)
    if args.llm_queue_out:
        queue = _llm_review_queue(audit)
        Path(args.llm_queue_out).write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(render_markdown_report(audit))


def _llm_review_queue(audit: Dict[str, Any]) -> Dict[str, Any]:
    review_issues = [
        issue
        for issue in audit["issues"]
        if issue["severity"] == "review" and not is_essential_cosmetic_card_id(issue["card_id"])
    ]
    return {
        "card_count": len({issue["card_id"] for issue in review_issues}),
        "cards": [
            {"card_id": card_id, "issues": [issue for issue in review_issues if issue["card_id"] == card_id]}
            for card_id in sorted({issue["card_id"] for issue in review_issues})
        ],
    }


if __name__ == "__main__":
    main()
