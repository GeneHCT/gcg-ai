"""
Audit script: Compare card_database Effect timing (【Main】/【Action】) with card_effects_converted triggers.
Reports mismatches where MAIN_PHASE vs ACTION_PHASE conversion is incorrect.
"""
import json
import re
from pathlib import Path
from typing import List, Optional, Tuple


def parse_expected_triggers(effect_text: str) -> Optional[List[str]]:
    """
    Parse expected triggers from effect text.
    Returns None if no main/action timing found (e.g. 【Deploy】, 【Burst】, etc.)
    """
    # Skip lines that don't have 【Main】 or 【Action】
    if '【Main】' not in effect_text and '【Action】' not in effect_text:
        return None

    # Dual timing: 【Main】/【Action】 or 【Action】/【Main】
    if '【Main】/【Action】' in effect_text or '【Action】/【Main】' in effect_text:
        return ["MAIN_PHASE", "ACTION_PHASE"]

    # Main only (standalone 【Main】, not part of dual)
    if re.search(r'【Main[^】]*】', effect_text) and '/【Action】' not in effect_text and '【Action】/' not in effect_text:
        return ["MAIN_PHASE"]

    # Action only
    if re.search(r'【Action[^】]*】', effect_text):
        return ["ACTION_PHASE"]

    return None


def get_timing_effects_and_triggers(converted: dict) -> List[List[str]]:
    """
    Get list of trigger lists for effects that have MAIN_PHASE or ACTION_PHASE.
    Order matches the order in the converted file.
    """
    result = []
    for eff in converted.get("effects", []):
        triggers = eff.get("triggers", [])
        if "MAIN_PHASE" in triggers or "ACTION_PHASE" in triggers:
            timing_triggers = [t for t in triggers if t in ("MAIN_PHASE", "ACTION_PHASE")]
            result.append(sorted(timing_triggers))
    return result


def audit_card(card_id: str, card_data: dict, converted_path: Path) -> List[Tuple[str, List[str], List[str], str]]:
    """
    Audit a single card. Returns list of (card_id, expected, actual, effect_text) for mismatches.
    """
    mismatches = []
    effects_text = card_data.get("Effect", [])

    if not effects_text:
        return mismatches

    if not converted_path.exists():
        return mismatches  # No converted file to compare

    with open(converted_path, "r") as f:
        converted = json.load(f)

    # Collect expected triggers per line (only for lines with main/action timing)
    expected_list = []
    effect_lines_with_timing = []
    for effect_line in effects_text:
        if not effect_line or effect_line.strip() == "-":
            continue
        expected = parse_expected_triggers(effect_line)
        if expected is not None:
            expected_list.append(sorted(expected))
            effect_lines_with_timing.append(effect_line)

    actual_list = get_timing_effects_and_triggers(converted)

    # Match by index: i-th timing line <-> i-th timing effect
    for i, (expected_sorted, effect_line) in enumerate(zip(expected_list, effect_lines_with_timing)):
        actual_sorted = actual_list[i] if i < len(actual_list) else []
        if expected_sorted != actual_sorted:
            actual = actual_list[i] if i < len(actual_list) else []
            mismatches.append((card_id, list(expected_sorted), actual, effect_line[:80]))

    return mismatches


def main():
    card_db_dir = Path("card_database")
    converted_dir = Path("card_effects_converted")

    if not card_db_dir.exists() or not converted_dir.exists():
        print("card_database/ or card_effects_converted/ not found")
        return 1

    all_mismatches = []

    for json_path in sorted(card_db_dir.glob("*.json")):
        if json_path.name == "all_cards.json":
            continue

        card_id = json_path.stem

        try:
            with open(json_path, "r") as f:
                card_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load {json_path}: {e}")
            continue

        converted_path = converted_dir / card_id
        ms = audit_card(card_id, card_data, converted_path)
        all_mismatches.extend(ms)

    if not all_mismatches:
        print("Audit complete: No timing mismatches found.")
        return 0

    print("Timing mismatches found:\n")
    for card_id, expected, actual, effect_text in all_mismatches:
        print(f"  {card_id}")
        print(f"    Effect: {effect_text}...")
        print(f"    Expected triggers: {expected}")
        print(f"    Actual triggers:   {actual}")
        print()

    print(f"Total: {len(all_mismatches)} mismatch(es)")
    return 1


if __name__ == "__main__":
    exit(main())
