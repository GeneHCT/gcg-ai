"""
Game Manager Integration for Effect System
Hooks effect triggers into game events
"""
from simulator.game_manager import GameState, TurnManager, Phase
from simulator.trigger_manager import get_trigger_manager
from simulator.unit import UnitInstance


class EffectIntegration:
    """Integrates effect system with game manager"""
    
    @staticmethod
    def initialize():
        """Initialize the effect system"""
        trigger_manager = get_trigger_manager()
        print(f"✓ Effect system initialized with {len(trigger_manager.effects_cache)} card effects")
    
    @staticmethod
    def on_unit_deployed(game_state: GameState, unit: UnitInstance) -> GameState:
        """
        Trigger when a unit is deployed (enters battle area).
        
        Args:
            game_state: Current game state
            unit: Unit that was deployed
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger ON_DEPLOY effects
        results = trigger_manager.trigger_event(
            event_type="ON_DEPLOY",
            game_state=game_state,
            source_card=unit,
            source_player_id=unit.owner_id
        )
        
        # Log results
        for result in results:
            print(f"  [Deploy Effect] {result}")
        
        return game_state
    
    @staticmethod
    def on_unit_destroyed(game_state: GameState, unit: UnitInstance, 
                         destroyed_by: str = "damage") -> GameState:
        """
        Trigger when a unit is destroyed.
        
        Args:
            game_state: Current game state
            unit: Unit that was destroyed
            destroyed_by: How it was destroyed (damage, effect, etc.)
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger ON_DESTROYED effects
        results = trigger_manager.trigger_event(
            event_type="ON_DESTROYED",
            game_state=game_state,
            source_card=unit,
            source_player_id=unit.owner_id,
            destroyed_by=destroyed_by
        )
        
        # Log results
        for result in results:
            print(f"  [Destroyed Effect] {result}")
        
        return game_state
    
    @staticmethod
    def on_unit_attacks(game_state: GameState, attacker: UnitInstance,
                       target = None) -> GameState:
        """
        Trigger when a unit declares an attack.
        
        Args:
            game_state: Current game state
            attacker: Unit that is attacking
            target: Target of the attack (Unit or Player)
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger ON_ATTACK effects
        results = trigger_manager.trigger_event(
            event_type="ON_ATTACK",
            game_state=game_state,
            source_card=attacker,
            source_player_id=attacker.owner_id,
            target=target
        )
        
        # Log results
        for result in results:
            print(f"  [Attack Effect] {result}")
        
        return game_state
    
    @staticmethod
    def on_unit_paired(game_state: GameState, unit: UnitInstance) -> GameState:
        """
        Trigger when a unit is paired with a pilot.
        
        Args:
            game_state: Current game state
            unit: Unit that was paired
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger ON_PAIRED effects
        results = trigger_manager.trigger_event(
            event_type="ON_PAIRED",
            game_state=game_state,
            source_card=unit,
            source_player_id=unit.owner_id
        )
        
        # Log results
        for result in results:
            print(f"  [Paired Effect] {result}")
        
        return game_state
    
    @staticmethod
    def on_unit_linked(game_state: GameState, unit: UnitInstance) -> GameState:
        """
        Trigger when a unit becomes linked (pilot satisfies link condition).
        
        Args:
            game_state: Current game state
            unit: Unit that was linked
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger ON_LINKED effects (【When Linked】)
        results = trigger_manager.trigger_event(
            event_type="ON_LINKED",
            game_state=game_state,
            source_card=unit,
            source_player_id=unit.owner_id
        )
        
        # Log results
        for result in results:
            print(f"  [Linked Effect] {result}")
        
        return game_state
    
    @staticmethod
    def on_base_deployed(game_state: GameState, base) -> GameState:
        """
        Trigger when a BASE card is deployed.
        
        Args:
            game_state: Current game state
            base: BaseInstance that was deployed
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger ON_DEPLOY effects for BASE
        results = trigger_manager.trigger_event(
            event_type="ON_DEPLOY",
            game_state=game_state,
            source_card=base,
            source_player_id=base.owner_id
        )
        
        # Log results
        for result in results:
            print(f"  [Base Deploy Effect] {result}")
        
        return game_state
    
    @staticmethod
    def on_base_destroyed(game_state: GameState, base) -> GameState:
        """
        Trigger when a BASE is destroyed.
        
        Args:
            game_state: Current game state
            base: BaseInstance that was destroyed
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger ON_DESTROYED effects for BASE
        results = trigger_manager.trigger_event(
            event_type="ON_DESTROYED",
            game_state=game_state,
            source_card=base,
            source_player_id=base.owner_id
        )
        
        # Log results
        for result in results:
            print(f"  [Base Destroyed Effect] {result}")
        
        return game_state
    
    @staticmethod
    def on_burst_triggered(game_state: GameState, burst_card, player_id: int) -> GameState:
        """
        Trigger a Burst effect from a card.
        
        Args:
            game_state: Current game state
            burst_card: Card with Burst effect
            player_id: Player whose burst is activating
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        
        # Trigger BURST effects
        results = trigger_manager.trigger_event(
            event_type="BURST",
            game_state=game_state,
            source_card=burst_card,
            source_player_id=player_id
        )
        
        # Log results
        for result in results:
            print(f"  [Burst Effect] {result}")
        
        return game_state
    
    @staticmethod
    def apply_continuous_effects(game_state: GameState) -> GameState:
        """
        Apply all continuous effects.
        Called at the start of each phase.
        
        Args:
            game_state: Current game state
            
        Returns:
            Updated game state
        """
        trigger_manager = get_trigger_manager()
        trigger_manager.apply_continuous_effects(game_state)
        
        return game_state
    
    @staticmethod
    def check_destroyed_units(game_state: GameState) -> GameState:
        """
        Check for destroyed units and trigger their effects.
        
        Args:
            game_state: Current game state
            
        Returns:
            Updated game state
        """
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            
            # Check for destroyed units (HP <= 0)
            destroyed_units = [u for u in player.battle_area if u.current_hp <= 0]
            
            for unit in destroyed_units:
                # Trigger destroyed effect
                game_state = EffectIntegration.on_unit_destroyed(game_state, unit)
                
                # Remove from battle area
                player.battle_area.remove(unit)
                
                # Move to trash
                player.trash.append(unit.card_data)
        
        return game_state


def patch_turn_manager():
    """Patch TurnManager to include effect triggers"""
    
    # Store original methods
    original_start_phase = TurnManager.start_phase
    original_draw_phase = TurnManager.draw_phase
    original_end_phase = TurnManager.end_phase
    
    @staticmethod
    def patched_start_phase(game_state: GameState) -> GameState:
        """Start phase with effect integration"""
        # Apply continuous effects
        game_state = EffectIntegration.apply_continuous_effects(game_state)
        
        # Run original start phase
        game_state = original_start_phase(game_state)
        
        # Check for destroyed units
        game_state = EffectIntegration.check_destroyed_units(game_state)
        
        return game_state
    
    @staticmethod
    def patched_draw_phase(game_state: GameState) -> GameState:
        """Draw phase with effect integration"""
        # Run original draw phase
        game_state = original_draw_phase(game_state)
        
        # Check for destroyed units (in case of deck-out)
        game_state = EffectIntegration.check_destroyed_units(game_state)
        
        return game_state
    
    @staticmethod
    def patched_end_phase(game_state: GameState) -> GameState:
        """End phase with effect integration"""
        # Run original end phase
        game_state = original_end_phase(game_state)
        
        # Check for destroyed units
        game_state = EffectIntegration.check_destroyed_units(game_state)
        
        return game_state
    
    # Replace methods
    TurnManager.start_phase = patched_start_phase
    TurnManager.draw_phase = patched_draw_phase
    TurnManager.end_phase = patched_end_phase


if __name__ == "__main__":
    # Initialize effect system
    EffectIntegration.initialize()
    
    # Patch turn manager
    patch_turn_manager()
    
    print("✓ Effect integration complete")
