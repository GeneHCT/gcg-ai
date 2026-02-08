"""
Action Step Manager for Gundam Card Game
Handles priority-based action step resolution during battle and end phase
"""
from typing import List, Tuple
from simulator.game_manager import GameState, Phase
from simulator.random_agent import Action, ActionType, LegalActionGenerator


class ActionStepManager:
    """Manages action step execution with priority passing"""
    
    @staticmethod
    def enter_action_step(game_state: GameState, is_battle: bool = False) -> GameState:
        """
        Enter action step. Standby player gets priority first.
        
        Args:
            game_state: Current game state
            is_battle: True if action step during battle, False if end phase
            
        Returns:
            Updated game state
        """
        game_state.in_action_step = True
        
        # RULE 9-3: Standby (non-active) player gets priority first
        standby_player = 1 - game_state.turn_player
        game_state.action_step_priority_player = standby_player
        game_state.action_step_consecutive_passes = 0
        
        return game_state
    
    @staticmethod
    def get_action_step_legal_actions(game_state: GameState) -> List[Action]:
        """
        Get legal actions during action step.
        
        Can activate:
        - 【Action】 Command cards
        - 【Activate･Action】 effects
        
        Args:
            game_state: Current game state
            
        Returns:
            List of legal actions
        """
        actions = []
        priority_player_id = game_state.action_step_priority_player
        player = game_state.players[priority_player_id]
        
        # 1. Can play 【Action】 command cards
        from simulator.trigger_manager import get_trigger_manager
        trigger_manager = get_trigger_manager()
        
        for card in player.hand:
            if card.type == 'COMMAND' and LegalActionGenerator._can_play_card(player, card, game_state):
                effect_data = trigger_manager.effects_cache.get(card.id)
                
                if effect_data:
                    effects = effect_data.get("effects", [])
                    for effect in effects:
                        triggers = effect.get("triggers", [])
                        # Can play if has ACTION_PHASE trigger
                        if "ACTION_PHASE" in triggers:
                            actions.append(Action(ActionType.PLAY_COMMAND, card=card))
                            break
        
        # 2. Can activate 【Activate･Action】 abilities
        # TODO: Implement activated abilities from units in play
        # This requires checking units in battle area for ACTIVATE_ACTION triggers
        
        # 3. Can always pass
        actions.append(Action(ActionType.PASS))
        
        return actions
    
    @staticmethod
    def handle_action_step_action(game_state: GameState, action: Action) -> Tuple[GameState, bool]:
        """
        Handle an action during action step.
        
        Args:
            game_state: Current game state
            action: Chosen action
            
        Returns:
            Tuple of (updated game_state, action_step_continues)
        """
        if action.action_type == ActionType.PASS:
            # Increment consecutive passes
            game_state.action_step_consecutive_passes += 1
            
            # Check if both players passed
            if game_state.action_step_consecutive_passes >= 2:
                # Action step ends
                return game_state, False
            
            # Pass priority to other player
            game_state.action_step_priority_player = 1 - game_state.action_step_priority_player
            return game_state, True
        
        else:
            # Action was taken - reset pass counter
            game_state.action_step_consecutive_passes = 0
            
            # Execute the action (command card or activated ability)
            # This will be handled by ActionExecutor
            
            # Pass priority to other player
            game_state.action_step_priority_player = 1 - game_state.action_step_priority_player
            return game_state, True
    
    @staticmethod
    def exit_action_step(game_state: GameState) -> GameState:
        """Exit action step"""
        game_state.in_action_step = False
        game_state.action_step_priority_player = 0
        game_state.action_step_consecutive_passes = 0
        return game_state
