"""
Link System Implementation for Gundam Card Game

Implements:
- Pilot pairing with Units
- Link condition checking
- Link effects (【When Linked】and【During Link】)
- Link Unit immediate attack ability
"""
from typing import Optional, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from simulator.unit import Card, UnitInstance, PilotInstance
    from simulator.game_manager import GameState, Player


class LinkManager:
    """
    Manages Link operations and rules for Units and Pilots.
    """
    
    @staticmethod
    def check_link_condition(unit_card: 'Card', pilot_card: 'Card') -> bool:
        """
        Check if a pilot satisfies a unit's link condition.
        
        Rules from 3-2-6:
        - Link conditions are Pilot names or traits
        - A portion of card name may be specified with [xyz]
        - The link requirement is satisfied if pilot name contains bracketed text
        
        Examples:
        - Unit requires [Garrod Ran], Pilot is "Garrod Ran & Tiffa Adill" → Match!
        - Unit requires "Amuro Ray", Pilot is "Amuro Ray" → Match!
        - Unit requires (Tekkadan), Pilot has trait "Tekkadan" → Match!
        
        Args:
            unit_card: Unit card with link conditions
            pilot_card: Pilot card to check
            
        Returns:
            True if pilot satisfies link condition
        """
        if not unit_card.link or unit_card.link == ["-"] or unit_card.link == []:
            return False  # No link condition
        
        pilot_name = pilot_card.name
        pilot_traits = pilot_card.traits if pilot_card.traits else []
        
        for condition in unit_card.link:
            condition_str = str(condition).strip()
            
            if not condition_str or condition_str == "-":
                continue
            
            # Check for bracketed name match [xyz]
            # Pattern: [text] anywhere in condition
            bracket_match = re.search(r'\[(.*?)\]', condition_str)
            if bracket_match:
                required_text = bracket_match.group(1)
                if required_text in pilot_name:
                    return True  # Partial name match
            
            # Check for exact name match
            if condition_str == pilot_name:
                return True
            
            # Check for trait match (trait)
            # Pattern: (trait) format
            trait_match = re.match(r'\((.*?)\)', condition_str)
            if trait_match:
                required_trait = trait_match.group(1)
                if required_trait in pilot_traits:
                    return True
            
            # Check if condition is directly in pilot traits
            if condition_str in pilot_traits:
                return True
        
        return False
    
    @staticmethod
    def can_pair_pilot(unit: 'UnitInstance', pilot_card: 'Card') -> bool:
        """
        Check if a pilot can be paired with a unit.
        
        Rules:
        - Unit must not already have a pilot
        - Pilot type must be PILOT
        - ANY pilot can pair with ANY unit (pairing is separate from linking)
        
        Args:
            unit: Unit instance to pair with
            pilot_card: Pilot card to pair
            
        Returns:
            True if pairing is allowed
        """
        if pilot_card.type != "PILOT":
            return False
        
        if unit.paired_pilot is not None:
            return False  # Already has a pilot
        
        # Any pilot can pair with any unit
        return True
    
    @staticmethod
    def pair_pilot(game_state: 'GameState', unit: 'UnitInstance', 
                  pilot_card: 'Card', trigger_effects: bool = True) -> bool:
        """
        Pair a pilot with a unit, creating a Link Unit if conditions are met.
        
        Rules from 3-2-6:
        - A Unit with a Pilot satisfying its link conditions is a Link Unit
        - Link Units can immediately attack during the turn they are deployed
        - Units normally cannot attack the turn they are deployed
        
        Args:
            game_state: Current game state
            unit: Unit to pair with
            pilot_card: Pilot card to pair
            trigger_effects: Whether to trigger Link effects
            
        Returns:
            True if pairing succeeded
        """
        player = game_state.players[unit.owner_id]
        
        # Remove pilot from hand
        if pilot_card not in player.hand:
            return False
        
        player.hand.remove(pilot_card)
        
        # Create pilot instance
        from simulator.unit import PilotInstance
        pilot_instance = PilotInstance(
            card_data=pilot_card,
            owner_id=unit.owner_id
        )
        
        # Pair pilot with unit
        unit.paired_pilot = pilot_instance
        
        # Check if this creates a Link Unit
        is_linked = LinkManager.check_link_condition(unit.card_data, pilot_card)
        
        if is_linked:
            print(f"  [LINK] {unit.card_data.name} + {pilot_card.name} → Link Unit!")
            print(f"    → Can attack immediately this turn")
        else:
            print(f"  [PAIR] {unit.card_data.name} + {pilot_card.name} (not linked)")
        
        # Trigger pairing effects
        if trigger_effects:
            try:
                from simulator.effect_integration import EffectIntegration
                game_state = EffectIntegration.on_unit_paired(game_state, unit)
                
                # Also trigger 【When Linked】effects if this is a Link Unit
                if is_linked:
                    game_state = EffectIntegration.on_unit_linked(game_state, unit)
            except Exception as e:
                print(f"  [Pair/Link Effect Error] {e}")
        
        return True
    
    @staticmethod
    def can_link_unit_attack(unit: 'UnitInstance', current_turn: int) -> bool:
        """
        Check if a Link Unit can attack.
        
        Rules from 3-2-6-3:
        - Units normally cannot attack during the turn in which they are deployed
        - Link Units can immediately attack during the turn in which they are deployed
        
        Args:
            unit: Unit to check
            current_turn: Current turn number
            
        Returns:
            True if unit can attack
        """
        # Can't attack if rested
        if unit.is_rested:
            return False
        
        # If deployed this turn, can only attack if it's a Link Unit
        if unit.turn_deployed == current_turn:
            return unit.is_linked
        
        # If deployed in a previous turn, can always attack
        return True
    
    @staticmethod
    def check_during_link_effects(unit: 'UnitInstance') -> bool:
        """
        Check if unit has active【During Link】effects.
        
        Rules from 13-2-12:
        -【During Link】effects are possessed by the Unit while a pilot 
         that meets the link condition is paired with it
        
        Args:
            unit: Unit to check
            
        Returns:
            True if During Link effects are active
        """
        return unit.is_linked
    
    @staticmethod
    def unpair_pilot(unit: 'UnitInstance') -> Optional['Card']:
        """
        Unpair a pilot from a unit.
        (Used when unit is destroyed or pilot is removed)
        
        Args:
            unit: Unit to unpair from
            
        Returns:
            Pilot card that was unpaired, or None
        """
        if not unit.paired_pilot:
            return None
        
        pilot_card = unit.paired_pilot.card_data
        unit.paired_pilot = None
        
        print(f"  Unpaired pilot {pilot_card.name} from {unit.card_data.name}")
        
        return pilot_card
    
    @staticmethod
    def get_link_bonus_description(unit: 'UnitInstance') -> str:
        """
        Get a description of bonuses from being linked.
        
        Args:
            unit: Unit to check
            
        Returns:
            Description string
        """
        if not unit.is_linked:
            return "Not linked"
        
        bonuses = []
        bonuses.append("Can attack immediately")
        
        # Check for During Link effects in card text
        if unit.card_data.effect:
            for effect in unit.card_data.effect:
                if "【During Link】" in str(effect):
                    bonuses.append(f"During Link: {effect}")
        
        return " | ".join(bonuses)


# Helper function to create PilotInstance if not already defined
if not hasattr(__import__('simulator.unit'), 'PilotInstance'):
    from dataclasses import dataclass
    from simulator.unit import Card
    
    @dataclass
    class PilotInstance:
        """Instance of a Pilot card paired with a Unit"""
        card_data: Card
        owner_id: int
        
        def __post_init__(self):
            """Validate pilot type"""
            if self.card_data.type != "PILOT":
                raise ValueError(f"Card {self.card_data.name} is not a PILOT")
