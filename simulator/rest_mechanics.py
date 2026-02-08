"""
Rest/Active Mechanics Implementation for Gundam Card Game

Implements:
- Resting cards (Units, Resources, Bases)
- Setting cards Active
- Reset all cards at start of turn
- Checking if cards can be rested/activated
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.unit import UnitInstance
    from simulator.base_system import BaseInstance
    from simulator.game_manager import GameState, Player, Card


class RestManager:
    """
    Manages Rest/Active state for cards in play.
    
    Rules from 5-4:
    - Cards in battle area, resource area, and base section can be Active or Rested
    - Active: card is placed vertically
    - Rested: card is placed horizontally
    - When placed into play, cards are generally set as Active
    """
    
    @staticmethod
    def rest_unit(unit: 'UnitInstance') -> bool:
        """
        Rest a unit (place horizontally).
        
        Args:
            unit: Unit to rest
            
        Returns:
            True if unit was rested (was active), False if already rested
        """
        if unit.is_rested:
            return False  # Already rested
        
        unit.is_rested = True
        return True
    
    @staticmethod
    def set_unit_active(unit: 'UnitInstance') -> bool:
        """
        Set a unit to active (place vertically).
        
        Args:
            unit: Unit to activate
            
        Returns:
            True if unit was activated (was rested), False if already active
        """
        if not unit.is_rested:
            return False  # Already active
        
        unit.is_rested = False
        return True
    
    @staticmethod
    def rest_base(base: 'BaseInstance') -> bool:
        """
        Rest a base.
        
        Args:
            base: Base to rest
            
        Returns:
            True if base was rested
        """
        if base.is_rested:
            return False
        
        base.is_rested = True
        return True
    
    @staticmethod
    def set_base_active(base: 'BaseInstance') -> bool:
        """
        Set a base to active.
        
        Args:
            base: Base to activate
            
        Returns:
            True if base was activated
        """
        if not base.is_rested:
            return False
        
        base.is_rested = False
        return True
    
    @staticmethod
    def rest_resource(game_state: 'GameState', player_id: int, 
                     resource_index: int) -> bool:
        """
        Rest a resource card.
        
        Note: In the current implementation, resources don't have individual
        rest state tracking. This is a placeholder for future enhancement.
        
        Args:
            game_state: Current game state
            player_id: Player whose resource to rest
            resource_index: Index of resource in resource area
            
        Returns:
            True if resource was rested
        """
        player = game_state.players[player_id]
        
        if resource_index < 0 or resource_index >= len(player.resource_area):
            return False
        
        # TODO: Add rest tracking for individual resources
        # For now, we track this at player level for simplicity
        print(f"  Rested resource #{resource_index + 1}")
        return True
    
    @staticmethod
    def reset_all_cards(game_state: 'GameState', player_id: int):
        """
        Reset (set active) all cards at the start of player's turn.
        
        Rules:
        - All units in battle area become active
        - All resources become active
        - All bases become active
        
        Args:
            game_state: Current game state
            player_id: Player whose cards to reset
        """
        player = game_state.players[player_id]
        
        units_reset = 0
        bases_reset = 0
        
        # Reset all units
        for unit in player.battle_area:
            if RestManager.set_unit_active(unit):
                units_reset += 1
        
        # Reset all bases
        for base in player.bases:
            if RestManager.set_base_active(base):
                bases_reset += 1
        
        # Reset resources (implicit - all become available)
        # In current implementation, resources don't have individual rest state
        
        if units_reset > 0 or bases_reset > 0:
            print(f"  All units reset to active")
    
    @staticmethod
    def can_unit_be_rested(unit: 'UnitInstance') -> bool:
        """
        Check if a unit can be rested.
        
        Args:
            unit: Unit to check
            
        Returns:
            True if unit can be rested (is currently active)
        """
        return not unit.is_rested
    
    @staticmethod
    def count_active_units(player: 'Player') -> int:
        """
        Count number of active (not rested) units.
        
        Args:
            player: Player to check
            
        Returns:
            Number of active units
        """
        return sum(1 for unit in player.battle_area if not unit.is_rested)
    
    @staticmethod
    def count_rested_units(player: 'Player') -> int:
        """
        Count number of rested units.
        
        Args:
            player: Player to check
            
        Returns:
            Number of rested units
        """
        return sum(1 for unit in player.battle_area if unit.is_rested)
    
    @staticmethod
    def get_active_units(player: 'Player') -> list:
        """
        Get list of active units.
        
        Args:
            player: Player to check
            
        Returns:
            List of active UnitInstances
        """
        return [unit for unit in player.battle_area if not unit.is_rested]
    
    @staticmethod
    def get_rested_units(player: 'Player') -> list:
        """
        Get list of rested units.
        
        Args:
            player: Player to check
            
        Returns:
            List of rested UnitInstances
        """
        return [unit for unit in player.battle_area if unit.is_rested]


class RestCostManager:
    """
    Manages paying costs by resting cards.
    """
    
    @staticmethod
    def can_pay_rest_cost(player: 'Player', cost: int, game_state: 'GameState' = None) -> bool:
        """
        Check if player can pay a cost by resting resources.
        
        DEPRECATED: Use ResourceManager.can_pay_cost() instead.
        
        Args:
            player: Player to check
            cost: Cost to pay
            game_state: Game state (required for accurate check)
            
        Returns:
            True if player has enough active resources
        """
        if game_state is None:
            # Fallback to old behavior
            active_resources = player.get_active_resources()
            return active_resources >= cost
        
        # Use ResourceManager for accurate check
        from simulator.resource_manager import ResourceManager
        return ResourceManager.can_pay_cost(game_state, player.player_id, cost)
    
    @staticmethod
    def pay_rest_cost(game_state: 'GameState', player_id: int, cost: int) -> bool:
        """
        Pay a cost by resting resources.
        
        DEPRECATED: Use ResourceManager.pay_cost() instead.
        
        Args:
            game_state: Current game state
            player_id: Player paying the cost
            cost: Amount to pay
            
        Returns:
            True if cost was paid successfully
        """
        # Delegate to ResourceManager
        from simulator.resource_manager import ResourceManager
        return ResourceManager.pay_cost(game_state, player_id, cost)
    
    @staticmethod
    def rest_unit_as_cost(unit: 'UnitInstance', effect_description: str = "") -> bool:
        """
        Rest a unit as a cost for an ability.
        
        Example: Blocker units rest to redirect attacks
        
        Args:
            unit: Unit to rest
            effect_description: Description of what the rest is for
            
        Returns:
            True if unit was rested
        """
        if unit.is_rested:
            return False  # Can't rest if already rested
        
        unit.is_rested = True
        
        if effect_description:
            print(f"  {unit.card_data.name} rested for {effect_description}")
        
        return True
