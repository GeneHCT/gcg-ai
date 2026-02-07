"""
Card Keyword Parser for Gundam Card Game.
Automatically extracts and applies keywords from card effect text.
"""
import re
import json
from typing import List, Dict, Any
from simulator.unit import UnitInstance, Card
from simulator.keyword_interpreter import KeywordInterpreter


class CardKeywordParser:
    """
    Parses keywords from card effect text and applies them to units.
    """
    
    # Regex patterns for keyword detection
    PATTERNS = {
        'repair': r'<Repair\s+(\d+)>',
        'breach': r'<Breach\s+(\d+)>',
        'support': r'<Support\s+(\d+)>',
        'first_strike': r'<First Strike>',
        'blocker': r'<Blocker>',
        'high_maneuver': r'<High-Maneuver>',
        'suppression': r'<Suppression>',
    }
    
    @staticmethod
    def parse_and_apply_keywords(card_data: Card, unit: UnitInstance) -> Dict[str, Any]:
        """
        Parse keywords from card effect text and apply them to the unit.
        
        Args:
            card_data: The card data containing effect text
            unit: The unit instance to apply keywords to
            
        Returns:
            Dictionary of parsed keywords and their values
        """
        parsed_keywords = {}
        
        # Combine all effect text
        effect_text = ' '.join(card_data.effect) if isinstance(card_data.effect, list) else str(card_data.effect)
        
        # Parse additive keywords (with values)
        for keyword in ['repair', 'breach', 'support']:
            match = re.search(CardKeywordParser.PATTERNS[keyword], effect_text, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                KeywordInterpreter.apply_additive_keyword(unit, keyword, value, "Card base effect")
                parsed_keywords[keyword] = value
        
        # Parse boolean keywords
        for keyword in ['first_strike', 'blocker', 'high_maneuver', 'suppression']:
            if re.search(CardKeywordParser.PATTERNS[keyword], effect_text, re.IGNORECASE):
                KeywordInterpreter.apply_boolean_keyword(unit, keyword, "Card base effect")
                parsed_keywords[keyword] = True
        
        return parsed_keywords
    
    @staticmethod
    def parse_conditional_keywords(card_data: Card) -> Dict[str, List[str]]:
        """
        Parse conditional keywords (e.g., "When Paired", "During Link").
        These require special handling as they activate under specific conditions.
        
        Args:
            card_data: The card data containing effect text
            
        Returns:
            Dictionary mapping conditions to their effects
        """
        conditional_effects = {
            'when_paired': [],
            'during_pair': [],
            'when_linked': [],
            'during_link': [],
            'attack': [],
            'deploy': [],
            'destroyed': [],
        }
        
        effect_text = ' '.join(card_data.effect) if isinstance(card_data.effect, list) else str(card_data.effect)
        
        # Split effects by periods and brackets
        effects = re.split(r'[\.\n](?=【)', effect_text)
        
        for effect in effects:
            effect = effect.strip()
            if not effect:
                continue
            
            # Check for timing keywords
            if '【When Paired】' in effect or '[When Paired]' in effect:
                conditional_effects['when_paired'].append(effect)
            elif '【During Pair】' in effect or '[During Pair]' in effect:
                conditional_effects['during_pair'].append(effect)
            elif '【When Linked】' in effect or '[When Linked]' in effect:
                conditional_effects['when_linked'].append(effect)
            elif '【During Link】' in effect or '[During Link]' in effect:
                conditional_effects['during_link'].append(effect)
            elif '【Attack】' in effect or '[Attack]' in effect:
                conditional_effects['attack'].append(effect)
            elif '【Deploy】' in effect or '[Deploy]' in effect:
                conditional_effects['deploy'].append(effect)
            elif '【Destroyed】' in effect or '[Destroyed]' in effect:
                conditional_effects['destroyed'].append(effect)
        
        # Remove empty lists
        conditional_effects = {k: v for k, v in conditional_effects.items() if v}
        
        return conditional_effects
    
    @staticmethod
    def apply_conditional_keywords(unit: UnitInstance, condition: str, effect_text: str) -> bool:
        """
        Apply keywords from conditional effects when condition is met.
        
        Args:
            unit: The unit to apply keywords to
            condition: The condition that was met (e.g., "when_paired")
            effect_text: The effect text to parse
            
        Returns:
            True if any keywords were applied
        """
        applied = False
        
        # Parse keywords from the conditional effect
        for keyword in ['repair', 'breach', 'support']:
            match = re.search(CardKeywordParser.PATTERNS[keyword], effect_text, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                KeywordInterpreter.apply_additive_keyword(
                    unit, keyword, value, f"Conditional: {condition}"
                )
                applied = True
        
        for keyword in ['first_strike', 'blocker', 'high_maneuver', 'suppression']:
            if re.search(CardKeywordParser.PATTERNS[keyword], effect_text, re.IGNORECASE):
                KeywordInterpreter.apply_boolean_keyword(
                    unit, keyword, f"Conditional: {condition}"
                )
                applied = True
        
        return applied
    
    @staticmethod
    def create_unit_from_card_data(card_dict: Dict[str, Any], owner_id: int) -> UnitInstance:
        """
        Create a unit instance from card database dictionary and apply all base keywords.
        
        Args:
            card_dict: Dictionary from card_database (loaded from JSON)
            owner_id: Owner player ID (0 or 1)
            
        Returns:
            UnitInstance with keywords applied
        """
        # Create Card object
        card = Card(
            name=card_dict.get('Name', ''),
            id=card_dict.get('ID', ''),
            type=card_dict.get('Type', ''),
            color=card_dict.get('Color', ''),
            level=card_dict.get('Level', 0),
            cost=card_dict.get('Cost', 0),
            ap=card_dict.get('Ap', 0),
            hp=card_dict.get('Hp', 0),
            traits=card_dict.get('Traits', []),
            zones=card_dict.get('Zones', []),
            link=card_dict.get('Link', []),
            effect=card_dict.get('Effect', [])
        )
        
        # Create unit instance
        unit = UnitInstance(card_data=card, owner_id=owner_id)
        
        # Parse and apply base keywords
        CardKeywordParser.parse_and_apply_keywords(card, unit)
        
        return unit
    
    @staticmethod
    def load_and_create_units_from_database(json_file_path: str, 
                                           card_ids: List[str], 
                                           owner_id: int) -> List[UnitInstance]:
        """
        Load cards from JSON database and create unit instances.
        
        Args:
            json_file_path: Path to all_cards.json
            card_ids: List of card IDs to load
            owner_id: Owner player ID
            
        Returns:
            List of UnitInstance objects with keywords applied
        """
        # Load card database
        with open(json_file_path, 'r', encoding='utf-8') as f:
            all_cards = json.load(f)
        
        # Create dictionary for quick lookup
        card_dict = {card['ID']: card for card in all_cards}
        
        # Create units
        units = []
        for card_id in card_ids:
            if card_id in card_dict:
                unit = CardKeywordParser.create_unit_from_card_data(
                    card_dict[card_id], owner_id
                )
                units.append(unit)
            else:
                print(f"Warning: Card ID {card_id} not found in database")
        
        return units
    
    @staticmethod
    def analyze_card_keywords(json_file_path: str) -> Dict[str, Dict[str, int]]:
        """
        Analyze all cards in database and count keyword usage.
        Useful for understanding card distribution and balancing.
        
        Args:
            json_file_path: Path to all_cards.json
            
        Returns:
            Dictionary with keyword statistics
        """
        with open(json_file_path, 'r', encoding='utf-8') as f:
            all_cards = json.load(f)
        
        stats = {
            'total_cards': len(all_cards),
            'units': 0,
            'keywords': {
                'repair': {'count': 0, 'values': []},
                'breach': {'count': 0, 'values': []},
                'support': {'count': 0, 'values': []},
                'first_strike': 0,
                'blocker': 0,
                'high_maneuver': 0,
                'suppression': 0,
            }
        }
        
        for card in all_cards:
            if card.get('Type') != 'UNIT':
                continue
            
            stats['units'] += 1
            effect_text = ' '.join(card.get('Effect', []))
            
            # Count additive keywords
            for keyword in ['repair', 'breach', 'support']:
                match = re.search(CardKeywordParser.PATTERNS[keyword], effect_text, re.IGNORECASE)
                if match:
                    value = int(match.group(1))
                    stats['keywords'][keyword]['count'] += 1
                    stats['keywords'][keyword]['values'].append(value)
            
            # Count boolean keywords
            for keyword in ['first_strike', 'blocker', 'high_maneuver', 'suppression']:
                if re.search(CardKeywordParser.PATTERNS[keyword], effect_text, re.IGNORECASE):
                    stats['keywords'][keyword] += 1
        
        return stats


def example_usage():
    """
    Example of using the CardKeywordParser.
    """
    print("=== Card Keyword Parser Example ===\n")
    
    # Example 1: Load cards from database
    print("1. Loading cards from database...")
    card_db_path = "card_database/all_cards.json"
    
    try:
        # Load specific cards
        card_ids = ["GD01-001", "GD01-003", "GD01-004"]  # Gundam, Banshee, Guncannon
        units = CardKeywordParser.load_and_create_units_from_database(
            card_db_path, card_ids, owner_id=0
        )
        
        print(f"   Loaded {len(units)} units\n")
        
        # Display parsed keywords
        for unit in units:
            print(f"   {unit.card_data.name} ({unit.card_data.id})")
            print(f"     AP: {unit.ap}, HP: {unit.hp}")
            print(f"     Keywords:")
            for keyword, value in unit.keywords.items():
                print(f"       - {keyword}: {value}")
            print()
        
        # Example 2: Analyze keyword distribution
        print("\n2. Analyzing keyword distribution in database...")
        stats = CardKeywordParser.analyze_card_keywords(card_db_path)
        
        print(f"   Total cards: {stats['total_cards']}")
        print(f"   Unit cards: {stats['units']}")
        print(f"\n   Keyword Usage:")
        
        for keyword, data in stats['keywords'].items():
            if isinstance(data, dict):
                # Additive keyword
                if data['count'] > 0:
                    avg_value = sum(data['values']) / len(data['values'])
                    print(f"     {keyword}: {data['count']} cards (avg value: {avg_value:.1f})")
            else:
                # Boolean keyword
                if data > 0:
                    print(f"     {keyword}: {data} cards")
        
        # Example 3: Parse conditional keywords
        print("\n3. Parsing conditional keywords...")
        if units:
            card_data = units[0].card_data
            conditional = CardKeywordParser.parse_conditional_keywords(card_data)
            
            if conditional:
                print(f"   {card_data.name} has conditional effects:")
                for condition, effects in conditional.items():
                    print(f"     {condition}:")
                    for effect in effects:
                        print(f"       - {effect[:60]}...")
            else:
                print(f"   {card_data.name} has no conditional effects")
        
        print("\n✓ Card Keyword Parser Example Complete!")
        
    except FileNotFoundError:
        print(f"   Error: Could not find {card_db_path}")
        print("   Using mock data instead...\n")
        
        # Use mock data
        mock_card = Card(
            name="Mock Gundam",
            id="MOCK-001",
            type="UNIT",
            color="Blue",
            level=4,
            cost=3,
            ap=3,
            hp=3,
            traits=["Earth Federation"],
            zones=["Space"],
            link=["Test Pilot"],
            effect=["<Repair 2>", "<Breach 1>", "【Attack】Rest target enemy unit."]
        )
        
        mock_unit = UnitInstance(card_data=mock_card, owner_id=0)
        CardKeywordParser.parse_and_apply_keywords(mock_card, mock_unit)
        
        print(f"   {mock_unit.card_data.name}")
        print(f"     Keywords: {mock_unit.keywords}")
        print("\n✓ Mock Example Complete!")


if __name__ == "__main__":
    example_usage()
