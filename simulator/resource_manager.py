"""
Resource Management System for Gundam Card Game

Implements resource-related game rules:
- Rule 2-9: Lv (Level) condition checking
- Rule 2-10: Cost payment by resting resources
- Rule 4-4: Resource area management (max 15 resources, max 5 EX resources)
- Rule 5-4: Active/Rested state for resources
- Rule 7-5-2-2: Playing cards from hand (Lv check + Cost payment)

Resources are Card objects placed in the resource area.
Each resource can be Active (vertical) or Rested (horizontal).
"""
from typing import TYPE_CHECKING, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from simulator.game_manager import GameState, Player
    from simulator.unit import Card


@dataclass
class ResourceState:
    """
    Tracks the rested state of resources in a player's resource area.
    
    Since Card objects don't inherently have an is_rested attribute,
    we track which resource indices are rested separately.
    """
    rested_indices: set = field(default_factory=set)
    
    def is_rested(self, index: int) -> bool:
        """Check if resource at given index is rested"""
        return index in self.rested_indices
    
    def rest(self, index: int):
        """Rest a resource at given index"""
        self.rested_indices.add(index)
    
    def set_active(self, index: int):
        """Set resource at given index to active"""
        self.rested_indices.discard(index)
    
    def reset_all(self):
        """Reset all resources to active (start of turn)"""
        self.rested_indices.clear()
    
    def count_active(self, total_resources: int) -> int:
        """Count active resources"""
        return total_resources - len(self.rested_indices)
    
    def get_active_indices(self, total_resources: int) -> List[int]:
        """Get indices of all active resources"""
        return [i for i in range(total_resources) if i not in self.rested_indices]
    
    def remove_resource(self, index: int):
        """
        Update rested state when a resource is removed.
        Shift down all indices above the removed one.
        """
        # Remove the index if it was rested
        self.rested_indices.discard(index)
        
        # Shift down all higher indices
        new_rested = set()
        for i in self.rested_indices:
            if i > index:
                new_rested.add(i - 1)
            else:
                new_rested.add(i)
        self.rested_indices = new_rested


class ResourceManager:
    """
    Manages resource-related operations for the Gundam Card Game.
    
    Handles:
    - Checking if player can play a card (Lv + Cost)
    - Paying cost by resting resources
    - Resource area limits
    - Resource active/rested state
    """
    
    @staticmethod
    def get_resource_state(game_state: 'GameState', player_id: int) -> ResourceState:
        """
        Get ResourceState for a player.
        
        Now uses the Player's internal _rested_resource_indices set.
        """
        player = game_state.players[player_id]
        # Create a ResourceState wrapper around the player's internal set
        state = ResourceState()
        state.rested_indices = player._rested_resource_indices
        return state
    
    @staticmethod
    def can_play_card(game_state: 'GameState', player_id: int, card: 'Card') -> bool:
        """
        Check if player can play a card from hand.
        
        Requirements (Rule 7-5-2-2):
        1. Lv condition: total resources >= card level (Rule 2-9-1)
        2. Cost condition: active resources >= card cost (Rule 2-10-1)
        
        Args:
            game_state: Current game state
            player_id: Player attempting to play the card
            card: Card to play
            
        Returns:
            True if player can play the card, False otherwise
        """
        player = game_state.players[player_id]
        
        # Rule 7-5-2-2-2: Check Lv condition
        if not ResourceManager.check_lv_condition(game_state, player_id, card.level):
            return False
        
        # Rule 7-5-2-2-3: Check Cost condition
        if not ResourceManager.can_pay_cost(game_state, player_id, card.cost):
            return False
        
        return True
    
    @staticmethod
    def check_lv_condition(game_state: 'GameState', player_id: int, required_lv: int) -> bool:
        """
        Check if player meets the Lv condition.
        
        Rule 2-9-1: "The number of resources that are required when playing a card.
        This condition is satisfied when the number of resources in your resource
        area is equal to or greater than the card's level. Whether a Resource is
        active or rested makes no difference."
        
        Rule 2-9-4: "Treat the Lv of a player as the current number of Resources
        that player has (including EX Resources) when referring to it."
        
        Args:
            game_state: Current game state
            player_id: Player to check
            required_lv: Required level
            
        Returns:
            True if player has enough total resources
        """
        player = game_state.players[player_id]
        total_resources = len(player.resource_area) + player.ex_resources
        return total_resources >= required_lv
    
    @staticmethod
    def can_pay_cost(game_state: 'GameState', player_id: int, cost: int) -> bool:
        """
        Check if player can pay a cost.
        
        Rule 2-10-1: "The cost paid when playing a card. You can pay this cost
        by resting the necessary number of active Resources in your resource area."
        
        Args:
            game_state: Current game state
            player_id: Player to check
            cost: Cost to pay
            
        Returns:
            True if player has enough active resources
        """
        player = game_state.players[player_id]
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        
        active_resources = resource_state.count_active(len(player.resource_area))
        return active_resources >= cost
    
    @staticmethod
    def pay_cost(game_state: 'GameState', player_id: int, cost: int) -> bool:
        """
        Pay a cost by resting resources.
        
        Rule 7-5-2-2-3: "Choose the number of Resources necessary to pay its cost
        and rest them."
        
        Args:
            game_state: Current game state
            player_id: Player paying the cost
            cost: Cost to pay
            
        Returns:
            True if cost was paid successfully, False otherwise
        """
        if cost == 0:
            return True
        
        if not ResourceManager.can_pay_cost(game_state, player_id, cost):
            return False
        
        player = game_state.players[player_id]
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        
        # Get active resource indices
        active_indices = resource_state.get_active_indices(len(player.resource_area))
        
        # Rest the first 'cost' number of active resources
        rested = 0
        for index in active_indices:
            if rested >= cost:
                break
            resource_state.rest(index)
            rested += 1
        
        return rested == cost
    
    @staticmethod
    def reset_all_resources(game_state: 'GameState', player_id: int):
        """
        Reset all resources to active at start of turn.
        
        Rule 5-4-2: "When a card is placed into the battle area, resource area,
        or base section, it is generally set as active."
        
        Args:
            game_state: Current game state
            player_id: Player whose resources to reset
        """
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        resource_state.reset_all()
    
    @staticmethod
    def can_add_resource(game_state: 'GameState', player_id: int, is_ex: bool = False) -> bool:
        """
        Check if player can add a resource to their resource area.
        
        Rule 4-4-2: "You may have up to 15 Resources in your resource area."
        Rule 4-4-2-1: "You may have up to five EX Resources in your resource area."
        
        Args:
            game_state: Current game state
            player_id: Player to check
            is_ex: Whether this is an EX resource
            
        Returns:
            True if resource can be added
        """
        player = game_state.players[player_id]
        
        # Check total resource limit
        total_resources = len(player.resource_area) + player.ex_resources
        if total_resources >= 15:
            return False
        
        # Check EX resource limit
        if is_ex and player.ex_resources >= 5:
            return False
        
        return True
    
    @staticmethod
    def add_resource(game_state: 'GameState', player_id: int, 
                    rested: bool = False) -> bool:
        """
        Add a resource from resource deck to resource area.
        
        Rule 5-4-2: Resources are "generally set as active" when placed.
        
        Args:
            game_state: Current game state
            player_id: Player adding resource
            rested: Whether to place the resource rested (default: False/Active)
            
        Returns:
            True if resource was added, False if resource deck is empty or limit reached
        """
        player = game_state.players[player_id]
        
        # Check if we can add a resource
        if not ResourceManager.can_add_resource(game_state, player_id, is_ex=False):
            return False
        
        # Check if resource deck has cards
        if not player.resource_deck:
            return False
        
        # Move top card from resource deck to resource area
        resource_card = player.resource_deck.pop(0)
        player.resource_area.append(resource_card)
        
        # Set rested state if needed
        if rested:
            resource_state = ResourceManager.get_resource_state(game_state, player_id)
            new_index = len(player.resource_area) - 1
            resource_state.rest(new_index)
        
        return True
    
    @staticmethod
    def add_ex_resource(game_state: 'GameState', player_id: int) -> bool:
        """
        Add an EX resource.
        
        Rule 4-4-2-1: "You may have up to five EX Resources in your resource area."
        
        Args:
            game_state: Current game state
            player_id: Player adding EX resource
            
        Returns:
            True if EX resource was added, False if limit reached
        """
        player = game_state.players[player_id]
        
        # Check if we can add an EX resource
        if not ResourceManager.can_add_resource(game_state, player_id, is_ex=True):
            return False
        
        player.ex_resources += 1
        return True
    
    @staticmethod
    def count_active_resources(game_state: 'GameState', player_id: int) -> int:
        """
        Count the number of active (not rested) resources.
        
        Args:
            game_state: Current game state
            player_id: Player to check
            
        Returns:
            Number of active resources
        """
        player = game_state.players[player_id]
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        return resource_state.count_active(len(player.resource_area))
    
    @staticmethod
    def count_total_resources(game_state: 'GameState', player_id: int) -> int:
        """
        Count total resources (for Lv condition).
        
        Rule 2-9-4: "Treat the Lv of a player as the current number of Resources
        that player has (including EX Resources) when referring to it."
        
        Args:
            game_state: Current game state
            player_id: Player to check
            
        Returns:
            Total number of resources (including EX resources)
        """
        player = game_state.players[player_id]
        return len(player.resource_area) + player.ex_resources
    
    @staticmethod
    def get_active_resource_indices(game_state: 'GameState', player_id: int) -> List[int]:
        """
        Get indices of all active resources.
        
        Args:
            game_state: Current game state
            player_id: Player to check
            
        Returns:
            List of indices of active resources
        """
        player = game_state.players[player_id]
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        return resource_state.get_active_indices(len(player.resource_area))
    
    @staticmethod
    def is_resource_active(game_state: 'GameState', player_id: int, index: int) -> bool:
        """
        Check if a specific resource is active.
        
        Args:
            game_state: Current game state
            player_id: Player to check
            index: Index of resource in resource area
            
        Returns:
            True if resource is active (not rested)
        """
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        return not resource_state.is_rested(index)
    
    @staticmethod
    def rest_resource(game_state: 'GameState', player_id: int, index: int) -> bool:
        """
        Rest a specific resource.
        
        Args:
            game_state: Current game state
            player_id: Player whose resource to rest
            index: Index of resource to rest
            
        Returns:
            True if resource was rested, False if already rested or invalid index
        """
        player = game_state.players[player_id]
        
        if index < 0 or index >= len(player.resource_area):
            return False
        
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        
        if resource_state.is_rested(index):
            return False  # Already rested
        
        resource_state.rest(index)
        return True
    
    @staticmethod
    def set_resource_active(game_state: 'GameState', player_id: int, index: int) -> bool:
        """
        Set a specific resource to active.
        
        Args:
            game_state: Current game state
            player_id: Player whose resource to activate
            index: Index of resource to activate
            
        Returns:
            True if resource was activated, False if already active or invalid index
        """
        player = game_state.players[player_id]
        
        if index < 0 or index >= len(player.resource_area):
            return False
        
        resource_state = ResourceManager.get_resource_state(game_state, player_id)
        
        if not resource_state.is_rested(index):
            return False  # Already active
        
        resource_state.set_active(index)
        return True
