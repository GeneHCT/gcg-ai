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
    ATTACK_PLAYER = "attack_player"
    ATTACK_UNIT = "attack_unit"
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
        elif self.action_type == ActionType.ATTACK_PLAYER:
            return f"ATTACK_PLAYER with {self.unit.card_data.name}"
        elif self.action_type == ActionType.ATTACK_UNIT:
            return f"ATTACK_UNIT: {self.unit.card_data.name} -> {self.target.card_data.name}"
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
                if card.type == 'UNIT' and LegalActionGenerator._can_play_card(player, card):
                    # Check battle area not full (max 6)
                    if len(player.battle_area) < 6:
                        actions.append(Action(ActionType.PLAY_UNIT, card=card))
            
            # 2. Can attack with units
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
            
            # 3. Can end phase
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
    def _can_play_card(player: Player, card: Card) -> bool:
        """Check if player can afford to play a card"""
        # Check Lv condition
        if player.get_total_resources() < card.level:
            return False
        
        # Check Cost condition (active resources)
        if player.get_active_resources() < card.cost:
            return False
        
        return True
    
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
            
            # Pay cost (rest resources)
            # For now, simplified: just check we can afford it
            if player.get_active_resources() >= card.cost:
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
        
        elif action.action_type == ActionType.ATTACK_PLAYER:
            # Attack player's shields or bases
            attacker = action.unit
            
            # Trigger Attack effects
            try:
                from simulator.effect_integration import EffectIntegration
                game_state = EffectIntegration.on_unit_attacks(game_state, attacker, target="PLAYER")
            except Exception as e:
                print(f"  [Effect Error] {e}")
            
            # Rest the attacker
            attacker.is_rested = True
            
            # RULE: If opponent has bases, attack bases first
            if opponent.has_bases():
                # Attack base
                base = next((b for b in opponent.bases if b.current_hp > 0), None)
                if base:
                    damage = attacker.ap
                    base_hp_before = base.current_hp
                    base.take_damage(damage)
                    
                    result = f"{attacker.card_data.name} attacked EX Base! "
                    result += f"Base HP: {base_hp_before}→{base.current_hp}"
                    
                    if base.current_hp <= 0:
                        result += " [BASE DESTROYED]"
                        opponent.bases.remove(base)
                        
                        # Check win condition
                        from simulator.game_manager import WinConditionChecker
                        game_state = WinConditionChecker.check_win_conditions(game_state)
                    
                    return game_state, result
            
            # Attack shields (base is gone or doesn't exist)
            shields_before = len(opponent.shield_area)
            trash_before = len(opponent.trash)
            
            # Determine number of shields to destroy
            num_shields = 2 if attacker.has_keyword("suppression") else 1
            
            destroyed_shields = []
            for _ in range(num_shields):
                if opponent.shield_area:
                    shield = opponent.shield_area.pop(0)
                    destroyed_shields.append(shield)
            
            # Check for burst effects on each destroyed shield
            burst_activated = []
            for shield in destroyed_shields:
                # Check if shield has burst (simplified: check effect text)
                has_burst = False
                if hasattr(shield, 'effect') and shield.effect:
                    effect_text = ' '.join(shield.effect) if isinstance(shield.effect, list) else str(shield.effect)
                    has_burst = 'Burst' in effect_text or '【Burst】' in effect_text
                
                if has_burst:
                    # Random agent decides whether to activate (50% chance for testing)
                    import random
                    if random.random() < 0.5:
                        burst_activated.append(shield.name)
                        # Note: Actual burst effect execution would go here
                
                # Move to trash
                opponent.trash.append(shield)
            
            shields_after = len(opponent.shield_area)
            trash_after = len(opponent.trash)
            
            # Check win condition
            from simulator.game_manager import WinConditionChecker
            game_state = WinConditionChecker.check_win_conditions(game_state)
            
            result = f"{attacker.card_data.name} attacked shields! "
            result += f"Destroyed {shields_before - shields_after} shields. "
            result += f"Shields remaining: {shields_after}"
            
            if attacker.has_keyword("suppression"):
                result += " (SUPPRESSION)"
            if attacker.has_keyword("breach"):
                result += f" (BREACH {attacker.get_keyword_value('breach')})"
            
            if burst_activated:
                result += f" | Burst activated: {', '.join(burst_activated)}"
            
            result += f" | Trash: {trash_before}→{trash_after}"
            
            return game_state, result
        
        elif action.action_type == ActionType.ATTACK_UNIT:
            # Attack enemy unit
            attacker = action.unit
            defender = action.target
            
            # Rest the attacker
            attacker.is_rested = True
            
            # Combat
            attacker_hp_before = attacker.current_hp
            defender_hp_before = defender.current_hp
            
            KeywordInterpreter.resolve_combat_damage(attacker, defender)
            
            result = f"{attacker.card_data.name} attacked {defender.card_data.name}! "
            result += f"Attacker: {attacker_hp_before}→{attacker.current_hp} HP, "
            result += f"Defender: {defender_hp_before}→{defender.current_hp} HP"
            
            if attacker.has_keyword("first_strike"):
                result += " (FIRST STRIKE)"
            
            if defender.is_destroyed:
                result += " [DESTROYED]"
                
                # Trigger Destroyed effects
                try:
                    from simulator.effect_integration import EffectIntegration
                    game_state = EffectIntegration.on_unit_destroyed(game_state, defender, "battle")
                except Exception as e:
                    print(f"  [Effect Error] {e}")
                
                # Breach damage
                breach_value = attacker.get_keyword_value("breach")
                if breach_value > 0:
                    shields_before = len(opponent.shield_area)
                    from simulator.game_manager import WinConditionChecker
                    KeywordInterpreter.resolve_breach_damage(attacker, defender, game_state)
                    shields_after = len(opponent.shield_area)
                    result += f" + BREACH {breach_value} ({shields_before - shields_after} shields destroyed)"
                    
                    # Check win condition
                    game_state = WinConditionChecker.check_win_conditions(game_state)
                
                # Remove destroyed unit
                if defender in opponent.battle_area:
                    opponent.battle_area.remove(defender)
                    opponent.trash.append(defender.card_data)
            
            if attacker.is_destroyed:
                result += f" (Attacker also destroyed!)"
                
                # Trigger Destroyed effects for attacker
                try:
                    from simulator.effect_integration import EffectIntegration
                    game_state = EffectIntegration.on_unit_destroyed(game_state, attacker, "battle")
                except Exception as e:
                    print(f"  [Effect Error] {e}")
                
                if attacker in player.battle_area:
                    player.battle_area.remove(attacker)
                    player.trash.append(attacker.card_data)
            
            return game_state, result
        
        elif action.action_type == ActionType.DISCARD:
            # Discard cards
            num_to_discard = len(player.hand) - 10
            if num_to_discard > 0:
                # Let agent choose (for random agent, this happens before execution)
                result = f"Discarded {num_to_discard} cards to hand limit"
                return game_state, result
            return game_state, "No discard needed"
        
        return game_state, f"Unknown action: {action.action_type}"
