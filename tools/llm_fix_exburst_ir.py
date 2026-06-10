"""Batch LLM-assisted fixer for ExBurst IR audit findings."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests

from simulator.effect_discovery import load_openrouter_config
from simulator.ir_validator import validate_ir_effect_data
from tools.semantic_exburst_audit import audit_card_semantics


DEFAULT_GROUPS = (
    "target_filter_mismatch",
    "missing_target_action_for_choice",
    "selected_target_selector_mismatch",
    "target_variable_count_mismatch",
    "stat_modifier_mismatch",
    "damage_amount_mismatch",
    "draw_amount_mismatch",
    "recover_amount_mismatch",
    "keyword_missing_from_ir",
)


def build_issue_batches(
    audit_report: Dict[str, Any],
    *,
    output_dir: str | Path = "card_effects_exburst",
    groups: Iterable[str] = DEFAULT_GROUPS,
    cards_per_group: int = 8,
    max_batches: int | None = None,
) -> List[Dict[str, Any]]:
    group_set = set(groups)
    issue_groups: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for issue in audit_report.get("issues", []):
        if issue.get("kind") not in group_set:
            continue
        if issue.get("severity") == "validation":
            continue
        issue_groups[issue["kind"]][issue["card_id"]].append(issue)

    batches: List[Dict[str, Any]] = []
    output_path = Path(output_dir)
    for kind, cards in sorted(issue_groups.items(), key=lambda item: (-sum(len(v) for v in item[1].values()), item[0])):
        card_ids = sorted(cards)
        for start in range(0, len(card_ids), cards_per_group):
            selected_ids = card_ids[start : start + cards_per_group]
            batch_cards = []
            for card_id in selected_ids:
                effect_path = output_path / card_id
                if not effect_path.exists():
                    continue
                effect_data = json.loads(effect_path.read_text(encoding="utf-8"))
                batch_cards.append(
                    {
                        "card_id": card_id,
                        "issues": cards[card_id],
                        "effect_data": effect_data,
                    }
                )
            if batch_cards:
                batches.append({"issue_kind": kind, "cards": batch_cards})
            if max_batches is not None and len(batches) >= max_batches:
                return batches
    return batches


def call_llm_for_batch(batch: Dict[str, Any], *, credentials_path: str | Path = ".credentials") -> Dict[str, Any]:
    config = load_openrouter_config(credentials_path)
    response = requests.post(
        f"{config.base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model,
            "response_format": {"type": "json_object"},
            "messages": [
            {
                "role": "system",
                "content": (
                    "You repair Gundam Card Game simulator IR. Return JSON only. "
                    "Do not invent unsupported runtime vocabulary. Keep card_id and metadata. "
                    "For each input card, either return a full corrected effect_data object or a skip_reason. "
                    "Target restrictions in printed choice text must live on action.target.filters. "
                    "Use SELECTED_CARD only when a previous action really stores selected targets. "
                    "For uncertain delayed effects or unsupported mechanics, skip instead of guessing."
                ),
            },
            {"role": "user", "content": _batch_prompt(batch)},
            ],
        },
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"] or "{}"
    return json.loads(content)


def apply_llm_response(response: Dict[str, Any], *, output_dir: str | Path = "card_effects_exburst") -> Dict[str, Any]:
    output_path = Path(output_dir)
    applied = []
    skipped = []
    rejected = []
    for item in response.get("cards", []):
        card_id = str(item.get("card_id") or "")
        if not card_id:
            rejected.append({"card_id": card_id, "reason": "Missing card_id"})
            continue
        if item.get("skip_reason"):
            skipped.append({"card_id": card_id, "reason": item["skip_reason"]})
            continue
        effect_data = item.get("effect_data")
        if not isinstance(effect_data, dict):
            rejected.append({"card_id": card_id, "reason": "Missing effect_data object"})
            continue
        if str(effect_data.get("card_id") or "") != card_id:
            rejected.append({"card_id": card_id, "reason": "effect_data.card_id mismatch"})
            continue
        ir_report = validate_ir_effect_data(effect_data)
        if ir_report.issues:
            rejected.append(
                {
                    "card_id": card_id,
                    "reason": "IR validation failed",
                    "issues": [
                        {
                            "path": issue.path,
                            "kind": issue.kind,
                            "value": issue.value,
                            "message": issue.message,
                        }
                        for issue in ir_report.issues
                    ],
                }
            )
            continue
        semantic_issues = audit_card_semantics(effect_data)
        blocking = [issue for issue in semantic_issues if issue.severity in {"fixable", "warning"}]
        if blocking:
            rejected.append(
                {
                    "card_id": card_id,
                    "reason": "Semantic audit still reports targeted issues",
                    "issues": [issue.__dict__ for issue in blocking[:5]],
                }
            )
            continue
        (output_path / card_id).write_text(json.dumps(effect_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        applied.append(card_id)
    return {"applied": applied, "skipped": skipped, "rejected": rejected}


def _batch_prompt(batch: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "task": "Repair these cards for the named semantic audit issue group.",
            "issue_kind": batch["issue_kind"],
            "runtime_vocabulary": {
                "selectors": [
                    "SELF",
                    "SELECTED_CARD",
                    "ENEMY_UNIT",
                    "FRIENDLY_UNIT",
                    "OTHER_FRIENDLY_UNIT",
                    "ENEMY_BASE",
                    "FRIENDLY_BASE",
                    "SELF_HAND",
                    "SELF_TRASH",
                    "SELF_DECK",
                    "OPPONENT_TRASH",
                ],
                "target_filters": ["state", "traits", "level", "hp", "ap", "color", "has_keyword", "text_contains", "name_contains"],
                "state_values": ["ACTIVE", "RESTED", "PAIRED", "LINKED"],
                "actions": [
                    "DAMAGE_UNIT",
                    "REST_UNIT",
                    "SET_ACTIVE",
                    "DESTROY_CARD",
                    "RETURN_TO_HAND",
                    "DRAW",
                    "RECOVER_HP",
                    "MODIFY_STAT",
                    "GRANT_KEYWORD",
                    "GRANT_ATTACK_TARGETING",
                    "OPTIONAL_ACTION",
                    "CONDITIONAL_BRANCH",
                ],
            },
            "response_schema": {
                "cards": [
                    {
                        "card_id": "string",
                        "effect_data": "full corrected card effect JSON, or omit when skipped",
                        "skip_reason": "string when uncertain or unsupported",
                    }
                ]
            },
            "cards": batch["cards"],
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Use grouped LLM calls to repair ExBurst IR findings")
    parser.add_argument("--audit-report", required=True)
    parser.add_argument("--output-dir", default="card_effects_exburst")
    parser.add_argument("--credentials", default=".credentials")
    parser.add_argument("--groups", nargs="*", default=list(DEFAULT_GROUPS))
    parser.add_argument("--cards-per-group", type=int, default=6)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--responses-out", default="/tmp/exburst_llm_fix_responses.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audit_report = json.loads(Path(args.audit_report).read_text(encoding="utf-8"))
    batches = build_issue_batches(
        audit_report,
        output_dir=args.output_dir,
        groups=args.groups,
        cards_per_group=args.cards_per_group,
        max_batches=args.max_batches,
    )
    response_path = Path(args.responses_out)
    summary = {"batch_count": len(batches), "applied": [], "skipped": [], "rejected": []}
    with response_path.open("a", encoding="utf-8") as handle:
        for index, batch in enumerate(batches, start=1):
            result = {"batch_index": index, "batch": {"issue_kind": batch["issue_kind"], "card_ids": [c["card_id"] for c in batch["cards"]]}}
            try:
                response = call_llm_for_batch(batch, credentials_path=args.credentials)
            except Exception as exc:
                result["error"] = str(exc)
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                handle.flush()
                print(json.dumps({"batch": index, "issue_kind": batch["issue_kind"], "error": str(exc)}, ensure_ascii=False))
                continue
            result["response"] = response
            if not args.dry_run:
                apply_result = apply_llm_response(response, output_dir=args.output_dir)
                result["apply_result"] = apply_result
                summary["applied"].extend(apply_result["applied"])
                summary["skipped"].extend(apply_result["skipped"])
                summary["rejected"].extend(apply_result["rejected"])
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            handle.flush()
            print(json.dumps({"batch": index, "issue_kind": batch["issue_kind"], "summary": summary}, ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
