"""
Card data loading and ExBurst normalization.

The simulator still consumes the original card dict shape internally. This
module keeps that boundary stable while allowing ExBurst raw API records to be
the runtime source of truth.
"""
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXBURST_CARDS_PATH = PROJECT_ROOT / "exburst_cards.json"
DEFAULT_NORMALIZED_CARDS_PATH = PROJECT_ROOT / "exburst_cards_normalized.json"


def load_simulator_cards(card_database_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load old-shaped cards or normalize raw ExBurst records on demand."""
    path = Path(card_database_path) if card_database_path else DEFAULT_EXBURST_CARDS_PATH

    with path.open("r", encoding="utf-8") as file:
        cards = json.load(file)

    if not cards:
        return []

    first_card = cards[0]
    if "ID" in first_card and "Name" in first_card:
        return cards
    if "cardno" in first_card or "originalid" in first_card:
        return normalize_exburst_cards(cards)

    raise ValueError(f"Unsupported card database shape: {path}")


def load_card_lookup(card_database_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Load cards keyed by canonical simulator ID."""
    return {card["ID"]: card for card in load_simulator_cards(card_database_path)}


def write_normalized_card_database(
    raw_path: str | Path = DEFAULT_EXBURST_CARDS_PATH,
    output_path: str | Path = DEFAULT_NORMALIZED_CARDS_PATH,
) -> List[Dict[str, Any]]:
    """Normalize raw ExBurst JSON and write a simulator-shaped cache."""
    with Path(raw_path).open("r", encoding="utf-8") as file:
        raw_cards = json.load(file)

    normalized = normalize_exburst_cards(raw_cards)
    Path(output_path).write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return normalized


def normalize_exburst_cards(raw_cards: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert raw ExBurst records into canonical old-shaped simulator cards."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for card in raw_cards:
        if card.get("published") is False:
            continue
        canonical_id = _canonical_id(card)
        if not canonical_id:
            continue
        grouped.setdefault(canonical_id, []).append(card)

    normalized = [
        _normalize_exburst_card(_choose_printing(canonical_id, printings), printings)
        for canonical_id, printings in sorted(grouped.items())
    ]
    return normalized


def _canonical_id(card: Dict[str, Any]) -> str:
    return str(card.get("originalid") or card.get("cardno") or "").strip()


def _choose_printing(canonical_id: str, printings: List[Dict[str, Any]]) -> Dict[str, Any]:
    exact = [card for card in printings if str(card.get("cardno", "")).strip() == canonical_id]
    if exact:
        return sorted(exact, key=lambda card: str(card.get("cardno", "")))[0]
    return sorted(printings, key=lambda card: str(card.get("cardno", "")))[0]


def _normalize_exburst_card(
    card: Dict[str, Any],
    printings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    canonical_id = _canonical_id(card)
    effects = _split_effect_text(card.get("effectdata"))
    traits = _split_slash_list(card.get("trait"))
    link = _split_slash_list(card.get("link"))
    card_type = _classify_type(canonical_id, card.get("name"), effects, traits, link)

    return {
        "Name": str(card.get("name") or "").strip(),
        "ID": canonical_id,
        "Effect": effects,
        "Color": _normalize_color(card.get("color")),
        "Type": card_type,
        "Rarity": None,
        "Traits": traits,
        "Level": _parse_int(card.get("level")),
        "Cost": _parse_int(card.get("cost")),
        "Ap": _parse_int(card.get("apdata")),
        "Hp": _parse_int(card.get("hp")),
        "Block": None,
        "Zones": [],
        "Link": link,
        "Set": canonical_id.split("-", 1)[0] if "-" in canonical_id else "",
        "CardNo": str(card.get("cardno") or "").strip(),
        "OriginalID": canonical_id,
        "AlternateCardNos": sorted(
            str(printing.get("cardno") or "").strip()
            for printing in printings
            if str(printing.get("cardno") or "").strip()
        ),
    }


def _normalize_color(value: Any) -> str:
    color = str(value or "").strip()
    return color if color else "-"


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return int(text) if re.fullmatch(r"-?\d+", text) else None


def _split_slash_list(value: Any) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [
        _clean_bracketed_text(part)
        for part in re.split(r"\s*/\s*", text)
        if _clean_bracketed_text(part)
    ]


def _split_effect_text(value: Any) -> List[str]:
    if value is None:
        return []
    text = html.unescape(str(value)).replace("\r", "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<([^>]+)>", _strip_html_tag_preserving_keywords, text)

    lines: List[str] = []
    for line in [line.strip() for line in text.split("\n") if line.strip()]:
        if line.startswith("(") and lines:
            lines[-1] = f"{lines[-1]} {line}"
        else:
            lines.append(line)
    return lines


def _strip_html_tag_preserving_keywords(match: re.Match[str]) -> str:
    tag = match.group(1).strip()
    tag_name = tag.split()[0].lstrip("/").lower() if tag else ""
    html_tags = {
        "a",
        "b",
        "div",
        "em",
        "i",
        "li",
        "p",
        "ruby",
        "rt",
        "span",
        "strong",
        "ul",
    }
    return "" if tag_name in html_tags else f"<{tag}>"


def _clean_bracketed_text(value: str) -> str:
    text = html.unescape(str(value)).strip()
    if (text.startswith("[") and text.endswith("]")) or (
        text.startswith("(") and text.endswith(")")
    ):
        text = text[1:-1].strip()
    return text


def _classify_type(
    canonical_id: str,
    name: Any,
    effects: List[str],
    traits: List[str],
    link: List[str],
) -> str:
    effect_text = " ".join(effects)
    card_name = str(name or "").strip()
    trait_set = {trait.lower() for trait in traits}

    if canonical_id.startswith("R-"):
        return "RESOURCE"
    if canonical_id.startswith("T-"):
        return "UNIT TOKEN"
    if card_name == "EX Base":
        return "BASE"
    if _is_base_text(effect_text, trait_set):
        return "BASE"
    if _is_command_text(effect_text):
        return "COMMAND"
    if _is_pilot_text(effect_text, link):
        return "PILOT"
    return "UNIT"


def _is_base_text(effect_text: str, trait_set: set[str]) -> bool:
    if "This Base" in effect_text or "Rest this Base" in effect_text:
        return True
    if "【Burst】Deploy this card" in effect_text and "【Deploy】Add 1 of your Shields" in effect_text:
        return True
    return bool({"warship", "stronghold"} & trait_set) and "【Deploy】" in effect_text


def _is_command_text(effect_text: str) -> bool:
    if "【Pilot】" in effect_text:
        return True
    return bool(re.search(r"【(?:Main|Action)】", effect_text))


def _is_pilot_text(effect_text: str, link: List[str]) -> bool:
    return not link and "【Burst】Add this card to your hand" in effect_text
