"""Game-essential cosmetic ExBurst cards handled outside card-effect IR."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ESSENTIAL_COSMETIC_PREFIXES = ("EXB-", "EXBP-", "EXR-", "EXRP-", "R-", "RP-")

ESSENTIAL_COSMETIC_NAME_TYPES = {
    ("EX BASE", "BASE"),
    ("EX RESOURCE", "UNIT"),
    ("RESOURCE", "RESOURCE"),
    ("RESOURCE", "UNIT"),
    ("RP - RESOURCE", "UNIT"),
}


def is_essential_cosmetic_card_id(card_id: str) -> bool:
    normalized = str(card_id or "").strip().upper()
    return any(normalized.startswith(prefix) for prefix in ESSENTIAL_COSMETIC_PREFIXES)


def is_essential_cosmetic_card(card: Dict[str, Any]) -> bool:
    card_id = str(card.get("ID") or card.get("OriginalID") or card.get("card_id") or "")
    if is_essential_cosmetic_card_id(card_id):
        return True
    name = str(card.get("Name") or "").strip().upper()
    card_type = str(card.get("Type") or "").strip().upper()
    return (name, card_type) in ESSENTIAL_COSMETIC_NAME_TYPES


def build_essential_cosmetic_effect_data(
    card_id: str,
    *,
    original_text: str = "",
    card_type: str = "RESOURCE",
) -> Dict[str, Any]:
    return {
        "card_id": card_id,
        "effects": [],
        "continuous_effects": [],
        "metadata": {
            "original_text": original_text,
            "parsing_version": "exburst-discovery-v1",
            "card_type": card_type,
            "parser_source": "essential_cosmetic",
            "support_status": "supported",
            "essential_cosmetic": True,
            "validation_issues": [],
            "note": (
                "Game-essential cosmetic card. Setup and payment behavior is handled by "
                "engine rules, not parsed card-effect IR."
            ),
        },
    }


def essential_cosmetic_effect_data_from_card(card: Dict[str, Any]) -> Dict[str, Any]:
    card_id = str(card.get("ID") or card.get("card_id") or "")
    original_text = "; ".join(str(line) for line in card.get("Effect", []) if line)
    if not original_text:
        original_text = str(card.get("EffectData") or card.get("effectdata") or "")
    return build_essential_cosmetic_effect_data(
        card_id,
        original_text=original_text,
        card_type=str(card.get("Type") or "RESOURCE"),
    )


def normalize_essential_cosmetic_effect_data(effect_data: Dict[str, Any]) -> Dict[str, Any]:
    card_id = str(effect_data.get("card_id") or "")
    metadata = effect_data.get("metadata", {}) if isinstance(effect_data.get("metadata"), dict) else {}
    return build_essential_cosmetic_effect_data(
        card_id,
        original_text=str(metadata.get("original_text") or ""),
        card_type=str(metadata.get("card_type") or "RESOURCE"),
    )


def apply_essential_cosmetic_normalization(output_dir: str | Path) -> Dict[str, Any]:
    output_path = Path(output_dir)
    changed: List[str] = []
    for effect_path in sorted(path for path in output_path.iterdir() if path.is_file() and not path.name.startswith(".")):
        card_id = effect_path.name
        if not is_essential_cosmetic_card_id(card_id):
            continue
        normalized = normalize_essential_cosmetic_effect_data(
            {"card_id": card_id, "metadata": {"original_text": "", "card_type": "RESOURCE"}}
        )
        try:
            existing = json.loads(effect_path.read_text(encoding="utf-8"))
            metadata = existing.get("metadata", {}) if isinstance(existing.get("metadata"), dict) else {}
            normalized = build_essential_cosmetic_effect_data(
                card_id,
                original_text=str(metadata.get("original_text") or ""),
                card_type=str(metadata.get("card_type") or "RESOURCE"),
            )
        except (OSError, ValueError, TypeError):
            pass
        effect_path.write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        changed.append(card_id)
    return {"changed_card_count": len(changed), "changed_cards": changed}
