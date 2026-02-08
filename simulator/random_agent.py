"""
Random Agent Implementation for Gundam Card Game

Agents that pick random legal moves for testing game simulation.
"""
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from simulator.game_manager import GameState, Phase, Player
from simulator.unit import UnitInstance, Card
from simulator.keyword_interpreter import KeywordInterpreter


class ActionType(Enum):
    """Types of actions available in the game"""
    PASS = "pass"
    PLAY_UNIT = "play_unit"
    PLAY_PILOT = "play_pilot"
    PLAY_COMMAND = "play_command"  # NEW: For playing command cards
    ATTACK_PLAYER = "attack_player"
    ATTACK_UNIT = "attack_unit"
    BLOCK = "block"  # NEW: For blocking with <Blocker> units
    DISCARD = "discard"
    END_PHASE = "end_phase"


@dataclass
class Action:
    """Represents a game action"""
    action_type: ActionType
    card: Optional[Card] = None
    unit: Optional[UnitInstance] = None
    target: Optional[UnitInstance] = None
    cards_to_discard: Optional[List[Card]] = None
    
    def __str__(self):
        if self.action_type == ActionType.PASS:
            return "PASS"
        elif self.action_type == ActionType.PLAY_UNIT:
            return f"PLAY_UNIT: {self.card.name} (Lv{self.card.level}, Cost{self.card.cost})"
        elif self.action_type == ActionType.PLAY_COMMAND:
            return f"PLAY_COMMAND: {self.card.name}"
        elif self.action_type == ActionType.ATTACK_PLAYER:
            return f"ATTACK_PLAYER with {self.unit.card_data.name}"
        elif self.action_type == ActionType.ATTACK_UNIT:
            return f"ATTACK_UNIT: {self.unit.card_data.name} -> {self.target.card_data.name}"
        elif self.action_type == ActionType.BLOCK:
            return f"BLOCK with {self.unit.card_data.name}"
        elif self.action_type == ActionType.DISCARD:
            return f"DISCARD: {len(self.cards_to_discard)} cards"
        elif self.action_type == ActionType.END_PHASE:
            return "END_PHASE"
        return str(self.action_type)


class LegalActionGenerator:
    """
    Generates legal actions for a given game state.
    """
    
    @staticmethod
    def get_legal_actions(game_state: GameState) -> List[Action]:
        """
        Get all legal actions for the current player.
        
        Args:
            game_state: Current game state
            
        Returns:
            List of legal actions
        """
        actions = []
        player = game_state.players[game_state.turn_player]
        opponent = game_state.players[game_state.get_opponent_id(game_state.turn_player)]
        
        # In Main Phase, can play cards or attack
        if game_state.current_phase == Phase.MAIN and not game_state.in_battle:
            # 1. Can play unit cards
            for card in player.hand:
                if card.type == 'UNIT' and LegalActionGenerator._can_play_card(player, card, game_state):
                    # Check battle area not full (max 6)
                    if len(player.battle_area) < 6:
                        actions.append(Action(ActionType.PLAY_UNIT, card=card))
            
            # 2. Can play command cards with 【Main】 during Main Phase
            for card in player.hand:
                if card.type == 'COMMAND' and LegalActionGenerator._can_play_card(player, card, game_state):
                    # Load card effect to check triggers
                    from simulator.trigger_manager import get_trigger_manager
                    trigger_manager = get_trigger_manager()
                    effect_data = trigger_manager.effects_cache.get(card.id)
                    
                    if effect_data:
                        effects = effect_data.get("effects", [])
                        for effect in effects:
                            triggers = effect.get("triggers", [])
                            # Can play if has MAIN_PHASE trigger
                            if "MAIN_PHASE" in triggers:
                                actions.append(Action(ActionType.PLAY_COMMAND, card=card))
                                break  # One action per command card
            
            # 3. Can attack with units
            for unit in player.battle_area:
                if LegalActionGenerator._can_attack(unit, game_state):
                    # RULE: If opponent has bases, must attack bases first
                    if opponent.has_bases():
                        # Can only attack bases
                        actions.append(Action(ActionType.ATTACK_PLAYER, unit=unit))
                    else:
                        # Can attack player shields
                        if opponent.has_shields():
                            actions.append(Action(ActionType.ATTACK_PLAYER, unit=unit))
                        
                        # Can attack rested enemy units
                        for enemy_unit in opponent.battle_area:
                            if enemy_unit.is_rested and not enemy_unit.is_destroyed:
                                actions.append(Action(
                                    ActionType.ATTACK_UNIT, 
                                    unit=unit, 
                                    target=enemy_unit
                                ))
            
            # 4. Can end phase
            actions.append(Action(ActionType.END_PHASE))
        
        # In End Phase, may need to discard to hand limit
        elif game_state.current_phase == Phase.END:
            if len(player.hand) > 10:
                # Must discard down to 10
                num_to_discard = len(player.hand) - 10
                # Generate a discard action (random agent will pick random cards)
                actions.append(Action(ActionType.DISCARD))
        
        # Always have option to pass (if no forced actions)
        if not actions or game_state.current_phase == Phase.MAIN:
            actions.append(Action(ActionType.PASS))
        
        return actions
    
    @staticmethod
    def _can_play_card(player: Player, card: Card, game_state: GameState) -> bool:
        """Check if player can afford to play a card"""
        from simulator.resource_manager import ResourceManager
        
        # Use ResourceManager to check both Lv and Cost conditions
        return ResourceManager.can_play_card(game_state, player.player_id, card)
    
    @staticmethod
    def _can_attack(unit: UnitInstance, game_state: GameState) -> bool:
        """Check if unit can attack"""
        # Must be active (not rested)
        if unit.is_rested:
            return False
        
        # Must not be destroyed
        if unit.is_destroyed:
            return False
        
        # Cannot attack on turn deployed (unless linked)
        if unit.turn_deployed == game_state.turn_number:
            if not unit.is_linked:
                return False
        
        return True


class RandomAgent:
    """
    Agent that picks random legal actions.
    """
    
    def __init__(self, player_id: int, seed: Optional[int] = None):
        """
        Initialize random agent.
        
        Args:
            player_id: Player ID (0 or 1)
            seed: Random seed for reproducibility
        """
        self.player_id = player_id
        self.rng = random.Random(seed)
    
    def choose_action(self, game_state: GameState, legal_actions: List[Action]) -> Action:
        """
        Choose a random legal action.
        
        Args:
            game_state: Current game state
            legal_actions: List of legal actions
            
        Returns:
            Chosen action
        """
        if not legal_actions:
            return Action(ActionType.PASS)
        
        # Filter out PASS if there are other actions (make game more interesting)
        non_pass_actions = [a for a in legal_actions if a.action_type != ActionType.PASS]
        
        if non_pass_actions:
            # 80% chance to take action, 20% chance to pass
            if self.rng.random() < 0.8:
                return self.rng.choice(non_pass_actions)
        
        return self.rng.choice(legal_actions)
    
    def choose_cards_to_discard(self, hand: List[Card], num_to_discard: int) -> List[Card]:
        """
        Choose random cards to discard.
        
        Args:
            hand: Current hand
            num_to_discard: Number of cards to discard
            
        Returns:
            List of cards to discard
        """
        return self.rng.sample(hand, min(num_to_discard, len(hand)))


class ActionExecutor:
    """
    Executes actions and updates game state.
    """
    
    @staticmethod
    def execute_action(game_state: GameState, action: Action) -> Tuple[GameState, str]:
        """
        Execute an action and return updated game state with result message.
        
        Args:
            game_state: Current game state
            action: Action to execute
            
        Returns:
            Tuple of (updated game_state, result_message)
        """
        player = game_state.players[game_state.turn_player]
        opponent = game_state.players[game_state.get_opponent_id(game_state.turn_player)]
        
        if action.action_type == ActionType.PASS:
            return game_state, "Pass"
        
        elif action.action_type == ActionType.END_PHASE:
            return game_state, "End Phase"
        
        elif action.action_type == ActionType.PLAY_UNIT:
            # Play the unit
            card = action.card
            
            # Import ResourceManager
            from simulator.resource_manager import ResourceManager
            
            # Check and pay cost using ResourceManager
            if ResourceManager.can_play_card(game_state, player.player_id, card):
                # Pay cost by resting resources
                if ResourceManager.pay_cost(game_state, player.player_id, card.cost):
                    # Remove from hand
                    if card in player.hand:
                        player.hand.remove(card)
                    
                    # Create unit instance
                    unit = UnitInstance(
                        card_data=card,
                        owner_id=player.player_id,
                        turn_deployed=game_state.turn_number
                    )
                    
                    # Parse keywords from card
                    from simulator.card_keyword_parser import CardKeywordParser
                    CardKeywordParser.parse_and_apply_keywords(card, unit)
                    
                    # Add to battle area
                    player.battle_area.append(unit)
                    player.units_deployed_this_turn += 1
                    
                    result = f"Deployed {card.name} (AP={unit.ap}, HP={unit.hp})"
                    if unit.keywords:
                        result += f" Keywords: {list(unit.keywords.keys())}"
                    
                    # Trigger Deploy effects
                    try:
                        from simulator.effect_integration import EffectIntegration
                        game_state = EffectIntegration.on_unit_deployed(game_state, unit)
                    except Exception as e:
                        print(f"  [Effect Error] {e}")
                    
                    return game_state, result
            
            return game_state, "Failed: Cannot afford card"
        
        elif action.action_type == ActionType.PLAY_COMMAND:
            # Play command card
            card = action.card
            
            # Import ResourceManager
            from simulator.resource_manager import ResourceManager
            
            # Check and pay cost using ResourceManager
            if ResourceManager.can_play_card(game_state, player.player_id, card):
                # Remove from hand
                if card in player.hand:
                    player.hand.remove(card)
                
                # Pay cost by resting resources
                ResourceManager.pay_cost(game_state, player.player_id, card.cost)
                
                # Trigger command effect via TriggerManager
                try:
                    from simulator.trigger_manager import get_trigger_manager
                    from simulator.effect_integration import EffectIntegration
                    
                    trigger_manager = get_trigger_manager()
                    
                    # Determine which trigger to use
                    current_trigger = "MAIN_PHASE"
                    if hasattr(game_state, 'in_action_step') and game_state.in_action_step:
                        current_trigger = "ACTION_PHASE"
                    
                    # Execute command effect
                    results = trigger_manager.trigger_event(
                        event_type=current_trigger,
                        game_state=game_state,
                        source_card=card,
                        source_player_id=player.player_id
                    )
                    
                    # Place command card in trash after resolution
                    player.trash.append(card)
                    
                    result = f"Played {card.name}: {'; '.join(results) if results else 'effect resolved'}"
                    return game_state, result
                    
                except Exception as e:
                    # Place card in trash even if effect fails
                    player.trash.append(card)
                    print(f"  [Command Effect Error] {e}")
                    return game_state, f"Played {card.name} (error in effect)"
            
            return game_state, "Failed: Cannot afford command card"
        
        elif action.action_type == ActionType.ATTACK_PLAYER:
            # Delegate to BattleManager for complete battle sequence
            # Note: This is a simplified version that doesn't have agent access
            # For full functionality, use BattleManager.run_complete_battle from game loop
            from simulator.battlemanager import BattleManager
            
            attacker = action.unit
            
            # Run battle without proper block/action steps (no agents available)
            # The game loop should intercept attack actions and call BattleManager directly
            game_state, battle_logs = BattleManager.run_complete_battle(
                game_state=game_state,
                attacker=attacker,
                target="PLAYER",
                target_unit=None,
                agents=[]  # Empty agents - will auto-pass in battle steps
            )
            
            result = "\n".join(battle_logs)
            return game_state, result
        
        elif action.action_type == ActionType.ATTACK_UNIT:
            # Delegate to BattleManager for complete battle sequence
            from simulator.battlemanager import BattleManager
            
            attacker = action.unit
            defender = action.target
            
            # Run battle without proper block/action steps (no agents available)
            # The game loop should intercept attack actions and call BattleManager directly
            game_state, battle_logs = BattleManager.run_complete_battle(
                game_state=game_state,
                attacker=attacker,
                target="UNIT",
                target_unit=defender,
                agents=[]  # Empty agents - will auto-pass in battle steps
            )
            
            result = "\n".join(battle_logs)
            return game_state, result
        
        elif action.action_type == ActionType.DISCARD:
            # Discard cards (hand limit or effect) - move from hand to trash
            if action.cards_to_discard:
                cards = action.cards_to_discard
            else:
                num_to_discard = max(0, len(player.hand) - 10)
                cards = player.hand[:num_to_discard] if num_to_discard > 0 else []
            if cards:
                for card in cards:
                    if card in player.hand:
                        player.hand.remove(card)
                        player.trash.append(card)
                return game_state, f"Discarded {len(cards)} card(s) to hand limit"
            return game_state, "No discard needed"
        
        return game_state, f"Unknown action: {action.action_type}"
