"""
Card sample selector for validation
Selects a stratified sample of cards across complexity levels
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Set


class CardSampleSelector:
    """Selects representative card samples for validation"""
    
    def __init__(self):
        self.simple_count = 20
        self.medium_count = 30
        self.complex_count = 15
        self.edge_case_count = 10
    
    def select_stratified_sample(self, cards_by_id: Dict, effects_dir: str) -> List[str]:
        """Select stratified sample of cards"""
        # Only consider cards that have been converted
        available_cards = []
        for card_id in cards_by_id.keys():
            effect_path = Path(effects_dir) / card_id
            if effect_path.exists():
                available_cards.append(card_id)
        
        print(f"Found {len(available_cards)} converted cards")
        
        # Categorize cards by complexity
        simple_cards = []
        medium_cards = []
        complex_cards = []
        edge_cases = []
        
        for card_id in available_cards:
            card = cards_by_id[card_id]
            complexity = self._assess_complexity(card)
            
            if complexity == "simple":
                simple_cards.append(card_id)
            elif complexity == "medium":
                medium_cards.append(card_id)
            elif complexity == "complex":
                complex_cards.append(card_id)
            elif complexity == "edge_case":
                edge_cases.append(card_id)
        
        print(f"Categorized: Simple={len(simple_cards)}, Medium={len(medium_cards)}, Complex={len(complex_cards)}, Edge={len(edge_cases)}")
        
        # Select samples from each category
        sample = []
        sample.extend(simple_cards[:self.simple_count])
        sample.extend(medium_cards[:self.medium_count])
        sample.extend(complex_cards[:self.complex_count])
        sample.extend(edge_cases[:self.edge_case_count])
        
        # Add manually curated edge cases
        curated = self._get_curated_edge_cases()
        for card_id in curated:
            if card_id in available_cards and card_id not in sample:
                sample.append(card_id)
        
        return sample
    
    def _assess_complexity(self, card: Dict) -> str:
        """Assess complexity level of a card"""
        effect_text = "; ".join(card.get("Effect", []))
        
        if not effect_text or effect_text == "-":
            return "simple"
        
        # Count complexity indicators
        complexity_score = 0
        
        # Multiple triggers
        trigger_keywords = ["【Deploy】", "【Attack】", "【Destroyed】", "【When Paired】", "【When Linked】", "【Burst】"]
        trigger_count = sum(1 for kw in trigger_keywords if kw in effect_text)
        complexity_score += trigger_count
        
        # Conditional chains
        if "If you do" in effect_text:
            complexity_score += 3
        
        # Optional actions
        if "you may" in effect_text.lower():
            complexity_score += 2
        
        # Multiple conditions
        if_count = effect_text.count("If ")
        complexity_score += if_count
        
        # Complex targeting
        if "Choose 1 to" in effect_text or "up to" in effect_text.lower():
            complexity_score += 2
        
        # Special mechanics
        if any(word in effect_text for word in ["【Pilot】", "Link Unit", "Deploy", "token"]):
            complexity_score += 2
        
        # Continuous effects with conditions
        if "While" in effect_text or "During your turn" in effect_text:
            complexity_score += 1
        
        # Attack targeting modifications
        if "may choose" in effect_text and "attack target" in effect_text:
            complexity_score += 2
        
        # Replacement effects
        if "instead" in effect_text.lower():
            complexity_score += 3
        
        # Edge cases
        if self._is_edge_case(card):
            return "edge_case"
        
        # Categorize based on score
        if complexity_score <= 1:
            return "simple"
        elif complexity_score <= 4:
            return "medium"
        else:
            return "complex"
    
    def _is_edge_case(self, card: Dict) -> bool:
        """Check if card is an edge case"""
        effect_text = "; ".join(card.get("Effect", []))
        
        edge_case_patterns = [
            "【Pilot】",  # Pilot ability
            "token",  # Token generation
            "instead",  # Replacement effect
            "as if it has 0",  # Cost override
            "card name is also treated as",  # Name alias
            "can't be set as active",  # Restriction
            "can't receive",  # Protection
            "unique names",  # Unique counting
        ]
        
        return any(pattern in effect_text for pattern in edge_case_patterns)
    
    def _get_curated_edge_cases(self) -> List[str]:
        """Get manually curated edge case cards"""
        return [
            "GD01-002",  # Unicorn Gundam (Destroy Mode) - cost override with "If you do"
            "GD01-003",  # Unicorn Gundam 02 Banshee - complex combo effect
            "ST02-012",  # Pilot card
            "ST03-001",  # Base card
            "ST04-014",  # Token generation
            "ST08-012",  # Complex continuous effect
            "GD02-072",  # Replacement effect
        ]
    
    def get_simple_cards(self, sample: List[str], cards_by_id: Dict) -> List[str]:
        """Get simple cards from sample"""
        return [cid for cid in sample if self._assess_complexity(cards_by_id[cid]) == "simple"]
    
    def get_medium_cards(self, sample: List[str], cards_by_id: Dict) -> List[str]:
        """Get medium complexity cards from sample"""
        return [cid for cid in sample if self._assess_complexity(cards_by_id[cid]) == "medium"]
    
    def get_complex_cards(self, sample: List[str], cards_by_id: Dict) -> List[str]:
        """Get complex cards from sample"""
        return [cid for cid in sample if self._assess_complexity(cards_by_id[cid]) == "complex"]
    
    def get_edge_cases(self, sample: List[str], cards_by_id: Dict) -> List[str]:
        """Get edge case cards from sample"""
        return [cid for cid in sample if self._assess_complexity(cards_by_id[cid]) == "edge_case"]


def main():
    """Test the sample selector"""
    with open("card_database/all_cards.json", 'r') as f:
        all_cards = json.load(f)
    
    cards_by_id = {card['ID']: card for card in all_cards}
    
    selector = CardSampleSelector()
    sample = selector.select_stratified_sample(cards_by_id, "card_effects_converted")
    
    print(f"\nSelected {len(sample)} cards:")
    print(f"  Simple: {len(selector.get_simple_cards(sample, cards_by_id))}")
    print(f"  Medium: {len(selector.get_medium_cards(sample, cards_by_id))}")
    print(f"  Complex: {len(selector.get_complex_cards(sample, cards_by_id))}")
    print(f"  Edge cases: {len(selector.get_edge_cases(sample, cards_by_id))}")
    
    print("\nSample cards:")
    for card_id in sample[:10]:
        card = cards_by_id[card_id]
        print(f"  {card_id}: {card.get('Name')} [{selector._assess_complexity(card)}]")


if __name__ == "__main__":
    main()
