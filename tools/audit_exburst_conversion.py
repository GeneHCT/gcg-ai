"""Audit ExBurst candidate IR failures by category and card ID."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


CREDIT_PATTERNS = ("Error code: 402", "Insufficient credits")


def audit_exburst_outputs(output_dir: str | Path = "card_effects_exburst") -> Dict[str, Any]:
    """Summarize non-credit unsupported/partial ExBurst conversion issues."""
    cards = [_load_effect_file(path) for path in sorted(Path(output_dir).iterdir()) if path.is_file()]
    relevant_cards = [
        card for card in cards
        if not _is_ignored_ex_resource(card.get("card_id", "")) and _card_issues(card)
    ]
    issues = [
        issue
        for card in relevant_cards
        for issue in _card_issues(card)
        if not _is_credit_issue(issue)
    ]
    grouped = _group_issues(issues)
    statuses = Counter(card.get("metadata", {}).get("support_status", "unknown") for card in cards)
    return {
        "total_cards": len(cards),
        "supported": statuses["supported"],
        "partial": statuses["partial"],
        "unsupported": statuses["unsupported"],
        "non_credit_issue_count": len(issues),
        "affected_cards": sorted({issue["card_id"] for issue in issues}),
        "groups": grouped,
    }


def print_audit(audit: Dict[str, Any]) -> None:
    print("ExBurst conversion audit")
    print(f"  Total cards: {audit['total_cards']}")
    print(f"  Supported: {audit['supported']}")
    print(f"  Partial: {audit['partial']}")
    print(f"  Unsupported: {audit['unsupported']}")
    print(f"  Non-credit issues: {audit['non_credit_issue_count']}")
    print(f"  Affected cards: {len(audit['affected_cards'])}")
    for group in audit["groups"]:
        examples = ", ".join(group["examples"])
        print(
            f"  - {group['kind']} | {group['value']} | {group['theme']}: "
            f"{group['count']} issue(s), examples: {examples}"
        )


def _load_effect_file(path: Path) -> Dict[str, Any]:
    effect_data = json.loads(path.read_text(encoding="utf-8"))
    effect_data.setdefault("card_id", path.name)
    return effect_data


def _card_issues(card: Dict[str, Any]) -> List[Dict[str, str]]:
    card_id = str(card.get("card_id") or "")
    raw_issues = card.get("metadata", {}).get("validation_issues", [])
    return [
        {
            "card_id": card_id,
            "path": str(issue.get("path", "")),
            "kind": str(issue.get("kind", "")),
            "value": str(issue.get("value", "")),
            "message": str(issue.get("message", "")),
        }
        for issue in raw_issues
    ]


def _group_issues(issues: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
    buckets: Dict[tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for issue in issues:
        key = (issue["kind"], _compact_value(issue["value"]), _message_theme(issue["message"]))
        buckets[key].append(issue)

    return [
        {
            "kind": kind,
            "value": value,
            "theme": theme,
            "count": len(group_issues),
            "examples": sorted({issue["card_id"] for issue in group_issues})[:8],
        }
        for (kind, value, theme), group_issues in sorted(
            buckets.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]


def _compact_value(value: str) -> str:
    if len(value) <= 80:
        return value or "<empty>"
    return f"{value[:77]}..."


def _message_theme(message: str) -> str:
    text = re.sub(r"\s+", " ", message).strip()
    if "LLM parser failed" in text:
        return "llm_parser_fallback"
    if "not executed by the runtime" in text:
        return "runtime_vocabulary"
    if "must include stat" in text:
        return "malformed_stat_modifier"
    if "not in runtime vocabulary" in text:
        return "runtime_vocabulary"
    return text[:80] if text else "<empty>"


def _is_credit_issue(issue: Dict[str, str]) -> bool:
    haystack = f"{issue.get('value', '')} {issue.get('message', '')}"
    return any(pattern in haystack for pattern in CREDIT_PATTERNS)


def _is_ignored_ex_resource(card_id: str) -> bool:
    return card_id.upper().startswith(("EXB-", "EXBP-", "EXR-", "EXRP-", "R-", "RP-"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit ExBurst candidate IR conversion issues")
    parser.add_argument("--output-dir", default="card_effects_exburst", help="ExBurst candidate IR directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    audit = audit_exburst_outputs(args.output_dir)
    if args.json:
        print(json.dumps(audit, indent=2, ensure_ascii=False))
    else:
        print_audit(audit)


if __name__ == "__main__":
    main()
