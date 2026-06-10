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

from simulator.ir_validator import audit_ir_directory


TARGET_ACTION_TYPES = {
    "DAMAGE_UNIT",
    "DESTROY_CARD",
    "GRANT_ATTACK_TARGETING",
    "GRANT_KEYWORD",
    "GRANT_PROTECTION",
    "MODIFY_STAT",
    "RECOVER_HP",
    "REDUCE_DAMAGE",
    "REST_UNIT",
    "RETURN_TO_HAND",
    "SET_ACTIVE",
}

CHAIN_KEYS = ("conditional_actions", "optional_actions", "next_if_success", "else_actions")
STACKING_KEYWORDS = {"BREACH", "REPAIR", "SUPPORT"}
NON_STACKING_KEYWORDS = {"BLOCKER", "FIRST_STRIKE", "HIGH_MANEUVER", "SUPPRESSION"}
CARD_STATES = {"ACTIVE", "RESTED", "PAIRED", "LINKED"}


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
    issues = [
        issue
        for card in cards
        for issue in audit_card_semantics(card, authority.get(str(card.get("card_id") or "")))
    ]
    grouped = _group_issues([*strict_audit["issues"], *[asdict(issue) for issue in issues]])
    statuses = Counter(card.get("metadata", {}).get("support_status", "unknown") for card in cards)
    return {
        "total_cards": len(cards),
        "strict_validation": {
            "supported": strict_audit["supported"],
            "partial": strict_audit["partial"],
            "unsupported": strict_audit["unsupported"],
            "issue_count": len(strict_audit["issues"]),
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

            state_by_selector = _state_conditions_by_selector(conditions)
            expected = _expected_target_from_text(raw_text)
            for action_path, action in _walk_actions(effect.get("actions", []), f"{path}.actions"):
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

    return normalized, changes


def apply_normalizations(output_dir: str | Path = "card_effects_exburst") -> Dict[str, Any]:
    """Apply conservative normalizations in-place and return a summary."""
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

    issues: List[SemanticAuditIssue] = []
    for action_path, action in target_actions:
        target = action["target"]
        selector = target.get("selector")
        if selector != expected["selector"] and selector != "SELECTED_CARD":
            issues.append(
                SemanticAuditIssue(
                    card_id=card_id,
                    path=f"{action_path}.target.selector",
                    kind="selected_target_selector_mismatch",
                    severity="warning",
                    message=f"Printed target implies {expected['selector']}, but IR action targets {selector}.",
                    raw_text=raw_text,
                    recommendation="Use SELECTED_CARD or the same constrained selector as the printed choice.",
                )
            )
            continue

        issues.extend(_compare_expected_filters(card_id, f"{action_path}.target", raw_text, expected, target, effect))
        actual_count = target.get("count", 1)
        if expected.get("count") is not None and actual_count != expected["count"] and selector != "SELECTED_CARD":
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
        if expected.get("variable_count") and target.get("variable_count") != expected["variable_count"]:
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

    stat_match = re.search(r"\b(AP|HP)\s*([+-])\s*(\d+)", raw_text)
    if stat_match:
        expected_stat = stat_match.group(1).upper()
        expected_mod = f"{stat_match.group(2)}{stat_match.group(3)}"
        for action_path, action in [(p, a) for p, a in actions if a.get("type") == "MODIFY_STAT"]:
            if action.get("stat") != expected_stat or str(action.get("modification")) != expected_mod:
                issues.append(
                    SemanticAuditIssue(
                        card_id=card_id,
                        path=action_path,
                        kind="stat_modifier_mismatch",
                        severity="warning",
                        message=f"Printed stat modifier is {expected_stat}{expected_mod}, but IR has {action}.",
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
        if not any(action.get("keyword") == keyword for _, action in grants):
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
        if keyword in STACKING_KEYWORDS and value is None:
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

    lowered = choice.lower()
    if "rested" in lowered:
        expected["filters"]["state"] = "RESTED"
    if "active" in lowered:
        expected["filters"]["state"] = "ACTIVE"
    trait_filters = re.findall(r"\(([^)]+)\)", choice)
    if trait_filters:
        expected["filters"]["traits"] = [trait.strip() for trait in trait_filters if trait.strip()]
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
        expected["requires_condition"] = "CHECK_LINK_STATUS"
    if re.search(r"paired with a \([^)]+\) Pilot", choice, re.IGNORECASE):
        expected["requires_condition"] = "CHECK_PAIRED_PILOT_TRAIT"
    if re.search(r"\bdamaged\b", choice, re.IGNORECASE):
        expected["requires_condition"] = "CHECK_STAT"
    keyword_match = re.search(r"with\s*[【<]([A-Za-z -]+)[】>]", choice, re.IGNORECASE)
    if keyword_match:
        expected["filters"]["has_keyword"] = _normalize_keyword_name(keyword_match.group(1)).lower()
    return expected


def _choice_phrase(raw_text: str) -> str:
    normalized = re.sub(r"\bLv\.", "Lv", raw_text, flags=re.IGNORECASE)
    match = re.search(r"\bChoose\s+(.+?)(?:\.|,| instead\b)", normalized, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _selector_from_choice(choice: str) -> Optional[str]:
    lowered = choice.lower()
    if "enemy" in lowered or "another player" in lowered:
        if "unit" in lowered:
            return "ENEMY_UNIT"
        if "base" in lowered:
            return "ENEMY_BASE"
    if "friendly" in lowered or "your " in lowered or "of your" in lowered:
        if "unit" in lowered:
            return "FRIENDLY_UNIT"
        if "base" in lowered:
            return "FRIENDLY_BASE"
    return None


def _choice_count(choice: str) -> tuple[Optional[int], Optional[Dict[str, int]]]:
    range_match = re.match(r"1\s+to\s+(\d+)\b", choice)
    if range_match:
        return None, {"min": 1, "max": int(range_match.group(1))}
    count_match = re.match(r"(\d+)\b", choice)
    if count_match:
        return int(count_match.group(1)), None
    return None, None


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
        for action in actions or []
    )


def _has_ordered_multi_action(actions: Iterable[Dict[str, Any]]) -> bool:
    return len([action for action in actions or [] if isinstance(action, dict)]) >= 2


def _has_optional_action(actions: Iterable[Dict[str, Any]]) -> bool:
    return any(
        isinstance(action, dict) and (action.get("type") == "OPTIONAL_ACTION" or action.get("optional") is True)
        for action in actions or []
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
    return str(keyword).strip().upper().replace("-", "_").replace(" ", "_")


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
    review_issues = [issue for issue in audit["issues"] if issue["severity"] == "review"]
    return {
        "card_count": len({issue["card_id"] for issue in review_issues}),
        "cards": [
            {"card_id": card_id, "issues": [issue for issue in review_issues if issue["card_id"] == card_id]}
            for card_id in sorted({issue["card_id"] for issue in review_issues})
        ],
    }


if __name__ == "__main__":
    main()
