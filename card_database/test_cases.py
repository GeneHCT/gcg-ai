#!/usr/bin/env python3
"""
Test cases for Gundam Card Game card data
"""

import json
import os
from typing import Dict, Any


def validate_card_structure(card: Dict[str, Any]) -> tuple[bool, list]:
    """
    Validate a card's structure matches the expected format
    
    Returns:
        tuple: (is_valid, list_of_errors)
    """
    errors = []
    required_fields = ["Name", "ID", "Effect", "Color", "Type", "Rarity", 
                      "Traits", "Level", "Cost", "Ap", "Hp", "Block", 
                      "Zones", "Link", "Set"]
    
    # Check all required fields exist
    for field in required_fields:
        if field not in card:
            errors.append(f"Missing required field: {field}")
    
    # Type checks
    if "Name" in card and not isinstance(card["Name"], str):
        errors.append("Name must be a string")
    
    if "ID" in card and not isinstance(card["ID"], str):
        errors.append("ID must be a string")
    
    if "Effect" in card and not isinstance(card["Effect"], list):
        errors.append("Effect must be a list")
    
    if "Color" in card and not isinstance(card["Color"], str):
        errors.append("Color must be a string")
    
    if "Type" in card and not isinstance(card["Type"], str):
        errors.append("Type must be a string")
    
    if "Rarity" in card and not isinstance(card["Rarity"], str):
        errors.append("Rarity must be a string")
    
    if "Traits" in card and not isinstance(card["Traits"], list):
        errors.append("Traits must be a list")
    
    if "Level" in card and card["Level"] is not None and not isinstance(card["Level"], int):
        errors.append("Level must be an integer or None")
    
    if "Cost" in card and card["Cost"] is not None and not isinstance(card["Cost"], int):
        errors.append("Cost must be an integer or None")
    
    if "Ap" in card and card["Ap"] is not None and not isinstance(card["Ap"], int):
        errors.append("Ap must be an integer or None")
    
    if "Hp" in card and card["Hp"] is not None and not isinstance(card["Hp"], int):
        errors.append("Hp must be an integer or None")
    
    if "Block" in card and card["Block"] is not None and not isinstance(card["Block"], int):
        errors.append("Block must be an integer or None")
    
    if "Zones" in card and not isinstance(card["Zones"], list):
        errors.append("Zones must be a list")
    
    if "Link" in card and not isinstance(card["Link"], list):
        errors.append("Link must be a list")
    
    if "Set" in card and not isinstance(card["Set"], str):
        errors.append("Set must be a string")
    
    return len(errors) == 0, errors


def test_all_cards(card_dir: str = "card_database"):
    """Test all cards in the database"""
    all_cards_file = os.path.join(card_dir, "all_cards.json")
    
    if not os.path.exists(all_cards_file):
        print(f"Error: {all_cards_file} not found")
        return False
    
    with open(all_cards_file, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    print(f"Testing {len(cards)} cards...\n")
    
    passed = 0
    failed = 0
    
    for idx, card in enumerate(cards, 1):
        card_name = card.get("Name", f"Card {idx}")
        card_id = card.get("ID", "Unknown")
        
        is_valid, errors = validate_card_structure(card)
        
        if is_valid:
            print(f"✓ {card_id} - {card_name}")
            passed += 1
        else:
            print(f"✗ {card_id} - {card_name}")
            for error in errors:
                print(f"    - {error}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    
    return failed == 0


def test_specific_card_types():
    """Test specific card types have appropriate fields"""
    print("\n" + "="*60)
    print("Testing specific card type requirements...")
    print("="*60 + "\n")
    
    all_cards_file = "card_database/all_cards.json"
    if not os.path.exists(all_cards_file):
        print("No cards file found")
        return False
    
    with open(all_cards_file, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    for card in cards:
        card_type = card.get("Type", "")
        card_name = card.get("Name", "Unknown")
        
        if card_type == "Unit":
            # Units should have AP, HP, Level, Block
            if card["Ap"] is None or card["Hp"] is None:
                print(f"✗ Unit '{card_name}' missing AP or HP")
                return False
            if card["Level"] is None:
                print(f"✗ Unit '{card_name}' missing Level")
                return False
        
        elif card_type in ["Command", "Event"]:
            # Commands typically don't have AP, HP, Level
            if card["Level"] is not None:
                print(f"⚠ Warning: Command '{card_name}' has a Level (unusual)")
        
        elif card_type == "Pilot":
            # Pilots typically don't have Level, AP, HP
            pass
    
    print("✓ All card type requirements met\n")
    return True


if __name__ == "__main__":
    print("="*60)
    print("Gundam Card Game - Card Database Tests")
    print("="*60 + "\n")
    
    success = test_all_cards()
    test_specific_card_types()
    
    if success:
        print("\n✓ All tests passed!")
        exit(0)
    else:
        print("\n✗ Some tests failed")
        exit(1)
