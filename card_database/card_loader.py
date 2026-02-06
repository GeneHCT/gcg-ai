#!/usr/bin/env python3
"""
Card Database Loader
Utilities for loading and querying the card database
"""

import json
import os
from typing import List, Dict, Any, Optional


class CardDatabase:
    """Card database manager"""
    
    def __init__(self, db_path: str = "card_database"):
        """Initialize the card database"""
        self.db_path = db_path
        self.cards = []
        self.cards_by_id = {}
        self.load_cards()
    
    def load_cards(self):
        """Load all cards from the database"""
        all_cards_file = os.path.join(self.db_path, "all_cards.json")
        
        if not os.path.exists(all_cards_file):
            print(f"Warning: {all_cards_file} not found")
            return
        
        with open(all_cards_file, 'r', encoding='utf-8') as f:
            self.cards = json.load(f)
        
        # Build index by ID
        self.cards_by_id = {card["ID"]: card for card in self.cards}
        
        print(f"Loaded {len(self.cards)} cards from database")
    
    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get a card by its ID"""
        return self.cards_by_id.get(card_id)
    
    def get_cards_by_color(self, color: str) -> List[Dict[str, Any]]:
        """Get all cards of a specific color"""
        return [card for card in self.cards if card["Color"].lower() == color.lower()]
    
    def get_cards_by_type(self, card_type: str) -> List[Dict[str, Any]]:
        """Get all cards of a specific type"""
        return [card for card in self.cards if card["Type"].lower() == card_type.lower()]
    
    def get_cards_by_set(self, set_name: str) -> List[Dict[str, Any]]:
        """Get all cards from a specific set"""
        return [card for card in self.cards if card["Set"].upper() == set_name.upper()]
    
    def get_cards_by_rarity(self, rarity: str) -> List[Dict[str, Any]]:
        """Get all cards of a specific rarity"""
        return [card for card in self.cards if card["Rarity"].upper() == rarity.upper()]
    
    def get_units_by_level(self, level: int) -> List[Dict[str, Any]]:
        """Get all units of a specific level"""
        return [card for card in self.cards 
                if card["Type"] == "Unit" and card["Level"] == level]
    
    def get_cards_with_trait(self, trait: str) -> List[Dict[str, Any]]:
        """Get all cards with a specific trait"""
        return [card for card in self.cards 
                if any(trait.lower() in t.lower() for t in card["Traits"])]
    
    def search_cards(self, name_query: str) -> List[Dict[str, Any]]:
        """Search cards by name (case-insensitive partial match)"""
        query = name_query.lower()
        return [card for card in self.cards 
                if query in card["Name"].lower()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            "total_cards": len(self.cards),
            "by_type": {},
            "by_color": {},
            "by_rarity": {},
            "by_set": {}
        }
        
        for card in self.cards:
            # Count by type
            card_type = card["Type"]
            stats["by_type"][card_type] = stats["by_type"].get(card_type, 0) + 1
            
            # Count by color
            color = card["Color"]
            stats["by_color"][color] = stats["by_color"].get(color, 0) + 1
            
            # Count by rarity
            rarity = card["Rarity"]
            stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1
            
            # Count by set
            set_name = card["Set"]
            stats["by_set"][set_name] = stats["by_set"].get(set_name, 0) + 1
        
        return stats
    
    def print_card(self, card: Dict[str, Any]):
        """Pretty print a card"""
        print(f"\n{'='*60}")
        print(f"{card['Name']} ({card['ID']})")
        print(f"{'='*60}")
        print(f"Type: {card['Type']}")
        print(f"Color: {card['Color']}")
        print(f"Rarity: {card['Rarity']}")
        print(f"Set: {card['Set']}")
        
        if card['Traits']:
            print(f"Traits: {', '.join(card['Traits'])}")
        
        if card['Type'] == 'Unit':
            print(f"\nLevel: {card['Level']} | Cost: {card['Cost']}")
            print(f"AP: {card['Ap']} | HP: {card['Hp']} | Block: {card['Block']}")
            if card['Zones']:
                print(f"Zones: {', '.join(card['Zones'])}")
            if card['Link']:
                print(f"Link: {', '.join(card['Link'])}")
        else:
            print(f"Cost: {card['Cost']}")
        
        if card['Effect']:
            print(f"\nEffects:")
            for effect in card['Effect']:
                print(f"  • {effect}")
        
        print(f"{'='*60}\n")


def demo():
    """Demo the card database functionality"""
    print("="*60)
    print("Gundam Card Game - Card Database Demo")
    print("="*60 + "\n")
    
    # Load database
    db = CardDatabase()
    
    # Get statistics
    stats = db.get_stats()
    print(f"\n--- Database Statistics ---")
    print(f"Total Cards: {stats['total_cards']}")
    print(f"\nBy Type:")
    for card_type, count in sorted(stats['by_type'].items()):
        print(f"  {card_type}: {count}")
    print(f"\nBy Color:")
    for color, count in sorted(stats['by_color'].items()):
        print(f"  {color}: {count}")
    print(f"\nBy Set:")
    for set_name, count in sorted(stats['by_set'].items()):
        print(f"  {set_name}: {count}")
    
    # Search examples
    print(f"\n--- Search Examples ---")
    
    print(f"\n1. Get card by ID:")
    card = db.get_card_by_id("GD01-001")
    if card:
        db.print_card(card)
    
    print(f"\n2. Search by name:")
    results = db.search_cards("gundam")
    print(f"Found {len(results)} cards with 'gundam' in name:")
    for card in results[:3]:
        print(f"  - {card['Name']} ({card['ID']})")
    
    print(f"\n3. Get all Units:")
    units = db.get_cards_by_type("Unit")
    print(f"Found {len(units)} units")
    
    print(f"\n4. Get Blue cards:")
    blue_cards = db.get_cards_by_color("Blue")
    print(f"Found {len(blue_cards)} blue cards:")
    for card in blue_cards[:3]:
        print(f"  - {card['Name']} ({card['ID']})")
    
    print(f"\n5. Get cards with 'Earth Federation' trait:")
    ef_cards = db.get_cards_with_trait("Earth Federation")
    print(f"Found {len(ef_cards)} Earth Federation cards:")
    for card in ef_cards[:3]:
        print(f"  - {card['Name']} ({card['ID']})")
    
    print(f"\n6. Get Level 5+ units:")
    high_level = [card for card in db.get_cards_by_type("Unit") 
                  if card["Level"] and card["Level"] >= 5]
    print(f"Found {len(high_level)} level 5+ units:")
    for card in high_level[:3]:
        print(f"  - {card['Name']} (Lv{card['Level']}) - AP:{card['Ap']} HP:{card['Hp']}")


if __name__ == "__main__":
    demo()
