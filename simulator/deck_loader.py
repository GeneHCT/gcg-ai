"""
Deck Loader for Gundam Card Game

Loads deck lists from text files in the format:
4x GD01-118
3x GD03-123
etc.

Each deck must have exactly 50 cards total.
"""
import json
from typing import List, Dict, Tuple


class DeckLoader:
    """
    Loads deck lists from text files.
    """
    
    @staticmethod
    def load_deck(deck_file: str, card_database_path: str = "card_database/all_cards.json") -> Tuple[List[Dict], bool]:
        """
        Load a deck from a text file.
        
        Format:
            4x GD01-118
            3x GD03-123
            ...
        
        Args:
            deck_file: Path to deck text file
            card_database_path: Path to card database JSON
            
        Returns:
            Tuple of (deck_list, is_valid)
            deck_list: List of card dictionaries
            is_valid: True if deck has exactly 50 cards
        """
        # Load card database
        with open(card_database_path, 'r', encoding='utf-8') as f:
            all_cards = json.load(f)
        
        # Create lookup dictionary
        card_dict = {card['ID']: card for card in all_cards}
        
        # Parse deck file
        deck = []
        total_cards = 0
        
        with open(deck_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse format: "4x GD01-118"
                try:
                    parts = line.split('x')
                    if len(parts) != 2:
                        print(f"Warning: Invalid format on line {line_num}: {line}")
                        continue
                    
                    count = int(parts[0].strip())
                    card_id = parts[1].strip()
                    
                    # Look up card
                    if card_id not in card_dict:
                        print(f"Warning: Card not found: {card_id} (line {line_num})")
                        continue
                    
                    # Add copies to deck
                    for _ in range(count):
                        deck.append(card_dict[card_id].copy())
                        total_cards += 1
                
                except Exception as e:
                    print(f"Error parsing line {line_num}: {line} - {e}")
                    continue
        
        # Validate deck size
        is_valid = (total_cards == 50)
        
        if not is_valid:
            print(f"Warning: Deck has {total_cards} cards (should be 50)")
        
        return deck, is_valid
    
    @staticmethod
    def load_deck_with_resource(deck_file: str, 
                                card_database_path: str = "card_database/all_cards.json") -> Tuple[List[Dict], List[Dict], bool]:
        """
        Load a deck and create a resource deck from it.
        
        Resource deck: 10 random cards from the main deck (simplified).
        
        Args:
            deck_file: Path to deck text file
            card_database_path: Path to card database
            
        Returns:
            Tuple of (main_deck, resource_deck, is_valid)
        """
        deck, is_valid = DeckLoader.load_deck(deck_file, card_database_path)
        
        if not is_valid or len(deck) < 10:
            return deck, [], is_valid
        
        # Create resource deck from first 10 cards (will be shuffled anyway)
        resource_deck = deck[:10]
        
        return deck, resource_deck, is_valid
    
    @staticmethod
    def print_deck_summary(deck: List[Dict]):
        """Print a summary of the deck"""
        print(f"Total cards: {len(deck)}")
        
        # Count by card
        card_counts = {}
        for card in deck:
            card_id = card['ID']
            card_name = card['Name']
            key = f"{card_name} ({card_id})"
            card_counts[key] = card_counts.get(key, 0) + 1
        
        print("\nDeck list:")
        for card_key, count in sorted(card_counts.items()):
            print(f"  {count}x {card_key}")
