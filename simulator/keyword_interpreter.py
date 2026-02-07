"""
KeywordInterpreter class for Gundam Card Game.
Handles all keyword logic including combat mechanics, damage resolution,
and feature vector generation for RL agents.

Based on Section 13 of the Official Game Rules.
"""
from typing import List, Tuple, Optional, Union
import numpy as np
from enum import Enum

from simulator.unit import UnitInstance, PilotInstance
from simulator.keywords import Keywords


class BattlePhase(Enum):
    """Battle phases for tracking combat flow"""
    DECLARE_ATTACK = "declare_attack"
    DECLARE_BLOCK = "declare_block"
    ACTION_STEP = "action_step"
    DAMAGE_STEP = "damage_step"
    END_BATTLE = "end_battle"


class KeywordInterpreter:
    """
    Interprets and applies keyword effects during gameplay.
    Handles combat mechanics, damage resolution, and keyword interactions.
    """
    
    # ============================================================================
    # Keyword Stacking Logic
    # ============================================================================
    
    @staticmethod
    def apply_additive_keyword(unit: UnitInstance, keyword: str, value: int, source: str = ""):
        """
        Apply an additive keyword (Repair, Breach, Support).
        Multiple instances stack by summing their values.
        
        Args:
            unit: The target unit
            keyword: "repair", "breach", or "support"
            value: The numeric value to add
            source: Description of the source
            
        Rule References:
            - 13-1-1-2: Repair stacking
            - 13-1-2-5: Breach stacking
            - 13-1-3-2: Support stacking
        """
        if keyword not in ["repair", "breach", "support"]:
            raise ValueError(f"Invalid additive keyword: {keyword}")
        
        unit.add_keyword(keyword, value, source)
    
    @staticmethod
    def apply_boolean_keyword(unit: UnitInstance, keyword: str, source: str = ""):
        """
        Apply a boolean keyword (Blocker, First Strike, High-Maneuver, Suppression).
        Multiple instances do not stack.
        
        Args:
            unit: The target unit
            keyword: The keyword name
            source: Description of the source
            
        Rule References:
            - 13-1-4-2: Blocker non-stackable
            - 13-1-5-3: First Strike non-stackable
            - 13-1-6-2: High-Maneuver non-stackable
            - 13-1-7-2: Suppression non-stackable
        """
        if keyword not in ["blocker", "first_strike", "high_maneuver", "suppression"]:
            raise ValueError(f"Invalid boolean keyword: {keyword}")
        
        unit.add_keyword(keyword, True, source)
    
    # ============================================================================
    # Combat Mechanics
    # ============================================================================
    
    @staticmethod
    def can_block(attacker: UnitInstance, potential_blocker: UnitInstance) -> bool:
        """
        Check if a unit can block an attack.
        
        Rule 13-1-6-1: High-Maneuver Priority
        If the attacker has <High-Maneuver>, blockers cannot be activated.
        
        Args:
            attacker: The attacking unit
            potential_blocker: The unit attempting to block
            
        Returns:
            bool: True if the blocker can block, False otherwise
        """
        # Rule 13-1-6-1: High-Maneuver prevents blocking
        if attacker.has_keyword("high_maneuver"):
            return False
        
        # Check if potential blocker has Blocker keyword
        if not potential_blocker.has_keyword("blocker"):
            return False
        
        # Check if blocker is active (not rested)
        if potential_blocker.is_rested:
            return False
        
        return True
    
    @staticmethod
    def resolve_first_strike(attacker: UnitInstance, defender: UnitInstance) -> Tuple[bool, bool]:
        """
        Resolve First Strike priority in combat.
        
        Rule 13-1-5: First Strike Priority
        If only one combatant has First Strike, it deals damage first.
        If the defender is destroyed, it cannot deal counter-damage.
        
        Args:
            attacker: The attacking unit
            defender: The defending unit
            
        Returns:
            Tuple[bool, bool]: (attacker_strikes_first, defender_can_counter)
        """
        attacker_has_fs = attacker.has_keyword("first_strike")
        defender_has_fs = defender.has_keyword("first_strike")
        
        # Case 1: Only attacker has First Strike
        if attacker_has_fs and not defender_has_fs:
            return (True, False)  # Attacker strikes first, defender may not counter
        
        # Case 2: Only defender has First Strike
        if defender_has_fs and not attacker_has_fs:
            return (False, True)  # Defender strikes first
        
        # Case 3: Both or neither have First Strike - simultaneous damage
        return (False, False)  # Simultaneous
    
    @staticmethod
    def apply_combat_damage(attacker: UnitInstance, defender: UnitInstance) -> bool:
        """
        Apply combat damage from attacker to defender.
        
        Args:
            attacker: The attacking unit
            defender: The defending unit
            
        Returns:
            bool: True if defender was destroyed
        """
        damage = attacker.ap
        defender.current_hp -= damage
        
        return defender.is_destroyed
    
    @staticmethod
    def resolve_combat_damage(attacker: UnitInstance, defender: UnitInstance):
        """
        Resolve damage between two units, considering First Strike.
        
        This is the main combat damage resolution function.
        
        Rule 13-1-5: First Strike Priority
        - If only one unit has First Strike, it deals damage first
        - If the opponent is destroyed, they don't deal counter-damage
        - If both or neither have First Strike, damage is simultaneous
        
        Args:
            attacker: The attacking unit
            defender: The defending unit
        """
        attacker_first, defender_first = KeywordInterpreter.resolve_first_strike(attacker, defender)
        
        # Case 1: Attacker has First Strike advantage
        if attacker_first:
            defender_destroyed = KeywordInterpreter.apply_combat_damage(attacker, defender)
            if not defender_destroyed:
                # Defender survives and deals counter-damage
                KeywordInterpreter.apply_combat_damage(defender, attacker)
            # If defender is destroyed, they don't counter-attack
            return
        
        # Case 2: Defender has First Strike advantage
        if defender_first:
            attacker_destroyed = KeywordInterpreter.apply_combat_damage(defender, attacker)
            if not attacker_destroyed:
                # Attacker survives and deals damage
                KeywordInterpreter.apply_combat_damage(attacker, defender)
            return
        
        # Case 3: Simultaneous damage (both or neither have First Strike)
        KeywordInterpreter.apply_combat_damage(attacker, defender)
        KeywordInterpreter.apply_combat_damage(defender, attacker)
    
    # ============================================================================
    # Shield Damage Resolution
    # ============================================================================
    
    @staticmethod
    def resolve_shield_damage(attacker: UnitInstance, defender_player: 'PlayerState', 
                             game_state: 'GameState') -> List['ShieldCard']:
        """
        Resolve damage to shields when attacking a player directly.
        
        Rule 13-1-7: Suppression (Dual-Shield Hit)
        If attacker has <Suppression>, it damages 2 shields simultaneously.
        Otherwise, only 1 shield is damaged.
        
        Args:
            attacker: The attacking unit
            defender_player: The player being attacked
            game_state: The current game state
            
        Returns:
            List of shield cards that were destroyed
        """
        destroyed_shields = []
        
        # Rule 13-1-7: Check for Suppression
        if attacker.has_keyword("suppression"):
            # Damage first TWO shields simultaneously
            num_shields = min(2, len(defender_player.shield_area))
            for i in range(num_shields):
                if defender_player.shield_area:
                    shield = defender_player.shield_area.pop(0)  # Remove from front
                    destroyed_shields.append(shield)
        else:
            # Standard: Damage only 1 shield
            # Check for Breach keyword
            breach_value = attacker.get_keyword_value("breach")
            num_shields_to_destroy = 1 + breach_value  # Base 1 + breach amount
            
            for i in range(num_shields_to_destroy):
                if defender_player.shield_area:
                    shield = defender_player.shield_area.pop(0)
                    destroyed_shields.append(shield)
                else:
                    # No more shields - game over condition
                    break
        
        return destroyed_shields
    
    @staticmethod
    def process_burst_triggers(shields: List['ShieldCard'], defender_player: 'PlayerState',
                               game_state: 'GameState'):
        """
        Process [Burst] triggers for destroyed shields.
        
        For Suppression, both shields are destroyed simultaneously,
        so Burst triggers happen in order chosen by defending player.
        
        Args:
            shields: List of shield cards that were destroyed
            defender_player: The player who owns the shields
            game_state: The current game state
        """
        burst_shields = [s for s in shields if s.has_burst()]
        
        # Defender chooses order of Burst resolution
        for shield in burst_shields:
            if defender_player.decide_burst_activation(shield, game_state):
                # Execute burst effect
                KeywordInterpreter.execute_burst_effect(shield, game_state)
        
        # Move shields to trash
        for shield in shields:
            defender_player.trash.append(shield)
    
    @staticmethod
    def execute_burst_effect(shield_card: 'ShieldCard', game_state: 'GameState'):
        """
        Execute the [Burst] effect of a shield card.
        This is a placeholder - actual effect execution depends on card text.
        
        Args:
            shield_card: The shield card with Burst
            game_state: The current game state
        """
        # TODO: Implement effect execution based on card text
        pass
    
    # ============================================================================
    # Breach Damage Resolution
    # ============================================================================
    
    @staticmethod
    def resolve_breach_damage(attacker: UnitInstance, destroyed_unit: UnitInstance,
                             game_state: 'GameState'):
        """
        Resolve Breach damage when a unit is destroyed in combat.
        
        FAQ Rule: Breach resolves BEFORE [Destroyed] triggered abilities.
        Active player's effects have priority.
        
        Args:
            attacker: The attacking unit
            destroyed_unit: The unit that was destroyed
            game_state: The current game state
        """
        breach_value = attacker.get_keyword_value("breach")
        
        if breach_value > 0:
            # Deal breach damage to shields
            defender_player = game_state.players[destroyed_unit.owner_id]
            
            for i in range(breach_value):
                if defender_player.shield_area:
                    shield = defender_player.shield_area.pop(0)
                    # Check for burst
                    if shield.has_burst() and defender_player.decide_burst_activation(shield, game_state):
                        KeywordInterpreter.execute_burst_effect(shield, game_state)
                    defender_player.trash.append(shield)
                else:
                    # No more shields
                    break
    
    # ============================================================================
    # Repair Resolution
    # ============================================================================
    
    @staticmethod
    def resolve_repair(unit: UnitInstance):
        """
        Resolve Repair at the end of turn.
        
        Rule 13-1-1: Repair
        At the end of the turn, recover the specified amount of HP.
        Multiple Repair effects stack additively.
        
        Args:
            unit: The unit with Repair keyword
        """
        repair_value = unit.get_keyword_value("repair")
        
        if repair_value > 0:
            # Recover HP, but don't exceed max HP
            unit.current_hp = min(unit.hp, unit.current_hp + repair_value)
    
    @staticmethod
    def resolve_all_repairs(units: List[UnitInstance]):
        """
        Resolve Repair for all units at end of turn.
        
        Args:
            units: List of all units in play
        """
        for unit in units:
            KeywordInterpreter.resolve_repair(unit)
    
    # ============================================================================
    # Support Resolution
    # ============================================================================
    
    @staticmethod
    def apply_support_bonus(supporter: UnitInstance, target: UnitInstance):
        """
        Apply Support bonus when a unit is activated to support.
        
        Rule 13-1-3: Support
        The supported unit gains +AP equal to the Support value.
        Multiple Support effects stack additively.
        
        Args:
            supporter: The unit providing support
            target: The unit receiving support
        """
        support_value = supporter.get_keyword_value("support")
        
        if support_value > 0:
            # Add temporary AP bonus to target
            # This is typically stored as a temporary keyword
            target.add_keyword("support_bonus", support_value, f"support from {supporter.card_data.name}")
    
    # ============================================================================
    # Feature Vector Generation for RL
    # ============================================================================
    
    @staticmethod
    def get_keyword_feature_vector(unit: UnitInstance) -> np.ndarray:
        """
        Extract keyword features as a NumPy array for RL agent.
        
        Returns a feature vector containing:
        - Additive keywords: repair, breach, support (numeric values)
        - Boolean keywords: blocker, first_strike, high_maneuver, suppression (0/1)
        
        Args:
            unit: The unit to extract features from
            
        Returns:
            NumPy array of keyword features
        """
        features = [
            # Additive keywords
            float(unit.get_keyword_value("repair")),
            float(unit.get_keyword_value("breach")),
            float(unit.get_keyword_value("support")),
            
            # Boolean keywords
            float(unit.has_keyword("blocker")),
            float(unit.has_keyword("first_strike")),
            float(unit.has_keyword("high_maneuver")),
            float(unit.has_keyword("suppression")),
        ]
        
        return np.array(features, dtype=np.float32)
    
    @staticmethod
    def get_battle_state_features(attacker: UnitInstance, defender: Optional[UnitInstance],
                                  phase: BattlePhase) -> np.ndarray:
        """
        Get feature vector for battle state (for RL agent).
        
        Args:
            attacker: The attacking unit
            defender: The defending unit (None if attacking player)
            phase: Current battle phase
            
        Returns:
            NumPy array of battle state features
        """
        features = []
        
        # Attacker features
        features.extend(attacker.to_feature_vector())
        
        # Defender features (zeros if attacking player)
        if defender:
            features.extend(defender.to_feature_vector())
        else:
            features.extend([0.0] * 16)  # Padding for missing defender
        
        # Battle phase (one-hot encoding)
        phase_encoding = [0.0] * len(BattlePhase)
        phase_encoding[list(BattlePhase).index(phase)] = 1.0
        features.extend(phase_encoding)
        
        # Combat prediction features
        if defender:
            attacker_first, defender_first = KeywordInterpreter.resolve_first_strike(attacker, defender)
            can_be_blocked = KeywordInterpreter.can_block(attacker, defender)
            
            features.extend([
                float(attacker_first),
                float(defender_first),
                float(can_be_blocked),
            ])
        else:
            features.extend([0.0, 0.0, 0.0])
        
        return np.array(features, dtype=np.float32)
    
    @staticmethod
    def get_all_keywords_vector(unit: UnitInstance) -> np.ndarray:
        """
        Get a comprehensive feature vector of all keywords for a unit.
        Useful for RL agent observation space.
        
        Args:
            unit: The unit to extract features from
            
        Returns:
            NumPy array containing all keyword information
        """
        return KeywordInterpreter.get_keyword_feature_vector(unit)


# ============================================================================
# Helper Classes
# ============================================================================

class PlayerState:
    """
    Player state container for shield area and other player-specific data.
    """
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.shield_area: List = []
        self.trash: List = []
        self.hand: List = []
        self.battle_area: List[UnitInstance] = []
        self.resource_area: List = []
    
    def decide_burst_activation(self, shield_card, game_state) -> bool:
        """
        Decide whether to activate a [Burst] effect.
        This should be implemented by the player's decision logic (RL agent or heuristic).
        
        Args:
            shield_card: The shield card with Burst
            game_state: The current game state
            
        Returns:
            bool: True if activating Burst, False otherwise
        """
        # Placeholder - should be implemented by player agent
        return True


class ShieldCard:
    """Placeholder for shield card"""
    def __init__(self, card_data):
        self.card_data = card_data
    
    def has_burst(self) -> bool:
        """Check if card has [Burst] keyword"""
        # TODO: Parse from card effect text
        return "Burst" in str(self.card_data)
