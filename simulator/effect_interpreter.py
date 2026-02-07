"""
Effect Interpreter for Gundam Card Game
Executes card effects from JSON schema
"""
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EffectContext:
    """Context for effect execution"""
    game_state: Any  # GameState reference
    source_card: Any  # Card that triggered the effect
    source_player_id: int
    trigger_event: str  # Which event triggered this
    trigger_data: Dict[str, Any]  # Additional data about the trigger
    

class EffectLoader:
    """Loads card effects from JSON files"""
    
    @staticmethod
    def load_effect(card_id: str, effects_dir: str = "card_effects_converted") -> Optional[Dict]:
        """
        Load effect JSON for a card.
        
        Args:
            card_id: Card ID (e.g., "GD01-007")
            effects_dir: Directory containing effect JSON files
            
        Returns:
            Effect dict or None if not found
        """
        effect_path = Path(effects_dir) / card_id
        if not effect_path.exists():
            return None
            
        try:
            with open(effect_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load effect for {card_id}: {e}")
            return None
    
    @staticmethod
    def load_all_effects(effects_dir: str = "card_effects_converted") -> Dict[str, Dict]:
        """
        Load all effect JSONs into memory.
        
        Returns:
            Dict mapping card_id to effect dict
        """
        effects = {}
        effects_path = Path(effects_dir)
        
        if not effects_path.exists():
            return effects
            
        for effect_file in effects_path.iterdir():
            if effect_file.is_file() and not effect_file.name.startswith('.'):
                card_id = effect_file.name
                effect_data = EffectLoader.load_effect(card_id, effects_dir)
                if effect_data:
                    effects[card_id] = effect_data
                    
        return effects


class TargetResolver:
    """Resolves effect targets based on selectors and filters"""
    
    @staticmethod
    def resolve_target(context: EffectContext, target_spec: Dict) -> List[Any]:
        """
        Resolve target specification to actual game objects.
        
        Args:
            context: Effect context
            target_spec: Target specification from JSON
            
        Returns:
            List of resolved targets
        """
        selector = target_spec.get("selector")
        filters = target_spec.get("filters", {})
        count = target_spec.get("count", 1)
        variable_count = target_spec.get("variable_count")
        selection_method = target_spec.get("selection_method", "CHOOSE")
        
        # Get base targets based on selector
        candidates = TargetResolver._get_candidates(context, selector)
        
        # Apply filters
        filtered = TargetResolver._apply_filters(candidates, filters, context)
        
        # Select targets based on count and method
        selected = TargetResolver._select_targets(
            filtered, count, variable_count, selection_method, context
        )
        
        return selected
    
    @staticmethod
    def _get_candidates(context: EffectContext, selector: str) -> List[Any]:
        """Get candidate targets based on selector type"""
        game_state = context.game_state
        source_player_id = context.source_player_id
        opponent_id = 1 - source_player_id
        
        candidates = []
        
        # Self-referential selectors
        if selector == "SELF":
            return [context.source_card]
        
        elif selector == "PAIRED_PILOT":
            if hasattr(context.source_card, 'paired_pilot'):
                return [context.source_card.paired_pilot] if context.source_card.paired_pilot else []
        
        # Friendly selectors
        elif selector == "FRIENDLY_UNIT":
            return game_state.players[source_player_id].battle_area.copy()
        
        elif selector == "OTHER_FRIENDLY_UNIT":
            units = game_state.players[source_player_id].battle_area.copy()
            return [u for u in units if u != context.source_card]
        
        elif selector == "FRIENDLY_BASE":
            return game_state.players[source_player_id].bases.copy()
        
        # Enemy selectors
        elif selector == "ENEMY_UNIT":
            return game_state.players[opponent_id].battle_area.copy()
        
        elif selector == "ENEMY_BASE":
            return game_state.players[opponent_id].bases.copy()
        
        elif selector == "ENEMY_PLAYER":
            return [game_state.players[opponent_id]]
        
        # Contextual selectors
        elif selector == "BATTLING_UNIT":
            # Get the unit being battled (from trigger data)
            return [context.trigger_data.get("battling_unit")] if "battling_unit" in context.trigger_data else []
        
        elif selector == "LOOKED_AT_CARD":
            return [context.trigger_data.get("looked_at_card")] if "looked_at_card" in context.trigger_data else []
        
        # Zone selectors
        elif selector == "FRIENDLY_RESOURCE":
            return game_state.players[source_player_id].resource_area.copy()
        
        elif selector == "SELF_TRASH":
            return game_state.players[source_player_id].trash.copy()
        
        elif selector == "OPPONENT_TRASH":
            return game_state.players[opponent_id].trash.copy()
        
        elif selector == "SELF_SHIELDS":
            return game_state.players[source_player_id].shield_area.copy()
        
        elif selector == "OPPONENT_SHIELDS":
            return game_state.players[opponent_id].shield_area.copy()
        
        elif selector == "SELF_HAND":
            return game_state.players[source_player_id].hand.copy()
        
        elif selector == "OPPONENT_HAND":
            return game_state.players[opponent_id].hand.copy()
        
        return candidates
    
    @staticmethod
    def _apply_filters(candidates: List[Any], filters: Dict, context: EffectContext) -> List[Any]:
        """Apply filters to candidate list"""
        if not filters:
            return candidates
        
        filtered = []
        
        for candidate in candidates:
            if TargetResolver._matches_filters(candidate, filters, context):
                filtered.append(candidate)
        
        return filtered
    
    @staticmethod
    def _matches_filters(target: Any, filters: Dict, context: EffectContext) -> bool:
        """Check if target matches all filters"""
        
        # Card type filter
        if "card_type" in filters:
            if not hasattr(target, 'card_data'):
                return False
            if target.card_data.type != filters["card_type"]:
                return False
        
        # Traits filter
        if "traits" in filters:
            required_traits = filters["traits"]
            trait_operator = filters.get("trait_operator", "ANY")
            
            if not hasattr(target, 'card_data'):
                return False
            
            target_traits = target.card_data.traits if hasattr(target.card_data, 'traits') else []
            
            if trait_operator == "ANY":
                # At least one trait must match
                if not any(trait in target_traits for trait in required_traits):
                    return False
            else:  # ALL
                # All traits must match
                if not all(trait in target_traits for trait in required_traits):
                    return False
        
        # Level filter
        if "level" in filters:
            level_filter = filters["level"]
            operator = level_filter["operator"]
            value = level_filter["value"]
            
            if not hasattr(target, 'card_data'):
                return False
            
            target_level = target.card_data.level
            
            if not TargetResolver._compare(target_level, operator, value):
                return False
        
        # HP filter
        if "hp" in filters:
            hp_filter = filters["hp"]
            operator = hp_filter["operator"]
            value = hp_filter["value"]
            
            if not hasattr(target, 'current_hp'):
                return False
            
            if not TargetResolver._compare(target.current_hp, operator, value):
                return False
        
        # AP filter
        if "ap" in filters:
            ap_filter = filters["ap"]
            operator = ap_filter["operator"]
            value = ap_filter["value"]
            
            if not hasattr(target, 'ap'):
                return False
            
            if not TargetResolver._compare(target.ap, operator, value):
                return False
        
        # State filter (ACTIVE/RESTED)
        if "state" in filters:
            required_state = filters["state"]
            
            if not hasattr(target, 'is_rested'):
                return False
            
            if required_state == "RESTED" and not target.is_rested:
                return False
            elif required_state == "ACTIVE" and target.is_rested:
                return False
        
        # Token filter
        if "is_token" in filters:
            is_token_required = filters["is_token"]
            
            if not hasattr(target, 'card_data'):
                return False
            
            # Check if card ID contains "TOKEN" or has a token flag
            is_token = "TOKEN" in target.card_data.id.upper()
            
            if is_token != is_token_required:
                return False
        
        # Keyword filter
        if "has_keyword" in filters:
            required_keyword = filters["has_keyword"].lower()
            
            if not hasattr(target, 'has_keyword'):
                return False
            
            if not target.has_keyword(required_keyword):
                return False
        
        return True
    
    @staticmethod
    def _compare(value: int, operator: str, target: int) -> bool:
        """Compare two values with operator"""
        if operator == ">=":
            return value >= target
        elif operator == "<=":
            return value <= target
        elif operator == "==":
            return value == target
        elif operator == "!=":
            return value != target
        elif operator == ">":
            return value > target
        elif operator == "<":
            return value < target
        return False
    
    @staticmethod
    def _select_targets(candidates: List[Any], count: Optional[int], 
                       variable_count: Optional[Dict], selection_method: str,
                       context: EffectContext) -> List[Any]:
        """Select final targets from filtered candidates"""
        
        if not candidates:
            return []
        
        # Determine how many to select
        if variable_count:
            # For now, select minimum (agent can choose to select more)
            # TODO: Integrate with agent decision
            num_to_select = variable_count.get("min", 1)
        elif count:
            num_to_select = count
        else:
            num_to_select = 1
        
        # Apply selection method
        if selection_method == "ALL":
            return candidates
        
        elif selection_method == "CHOOSE":
            # TODO: Integrate with agent choice system
            # For now, return first N candidates
            return candidates[:num_to_select]
        
        elif selection_method == "RANDOM":
            import random
            if len(candidates) <= num_to_select:
                return candidates
            return random.sample(candidates, num_to_select)
        
        return candidates[:num_to_select]


class ConditionEvaluator:
    """Evaluates effect conditions"""
    
    @staticmethod
    def evaluate_all(context: EffectContext, conditions: List[Dict]) -> bool:
        """
        Evaluate all conditions - all must be true.
        
        Args:
            context: Effect context
            conditions: List of condition dicts
            
        Returns:
            True if all conditions pass
        """
        if not conditions:
            return True
        
        for condition in conditions:
            if not ConditionEvaluator.evaluate(context, condition):
                return False
        
        return True
    
    @staticmethod
    def evaluate(context: EffectContext, condition: Dict) -> bool:
        """Evaluate a single condition"""
        condition_type = condition.get("type")
        
        if condition_type == "COUNT_CARDS":
            return ConditionEvaluator._evaluate_count_cards(context, condition)
        
        elif condition_type == "CHECK_STAT":
            return ConditionEvaluator._evaluate_check_stat(context, condition)
        
        elif condition_type == "CHECK_TURN":
            return ConditionEvaluator._evaluate_check_turn(context, condition)
        
        elif condition_type == "CHECK_CARD_STATE":
            return ConditionEvaluator._evaluate_check_card_state(context, condition)
        
        elif condition_type == "CHECK_PLAYER_LEVEL":
            return ConditionEvaluator._evaluate_check_player_level(context, condition)
        
        elif condition_type == "CHECK_MILLED_TRAITS":
            return ConditionEvaluator._evaluate_check_milled_traits(context, condition)
        
        elif condition_type == "CHECK_LINK_STATUS":
            return ConditionEvaluator._evaluate_check_link_status(context, condition)
        
        elif condition_type == "CHECK_PAIRED_PILOT_TRAIT":
            return ConditionEvaluator._evaluate_check_paired_pilot_trait(context, condition)
        
        # Add more condition types as needed
        
        return True  # Unknown condition types pass by default
    
    @staticmethod
    def _evaluate_count_cards(context: EffectContext, condition: Dict) -> bool:
        """Evaluate COUNT_CARDS condition"""
        zone = condition.get("zone")
        owner = condition.get("owner", "SELF")
        card_type = condition.get("card_type")
        traits = condition.get("traits", [])
        trait_operator = condition.get("trait_operator", "ANY")
        exclude_self = condition.get("exclude_self", False)
        operator = condition.get("operator", ">=")
        value = condition.get("value", 1)
        
        # Determine which player's zone to check
        if owner == "SELF":
            player_id = context.source_player_id
        elif owner == "OPPONENT":
            player_id = 1 - context.source_player_id
        else:  # ANY
            # Count both players (not common, but supported)
            player_id = None
        
        game_state = context.game_state
        count = 0
        
        # Count cards in zone
        def count_in_zone(pid):
            nonlocal count
            player = game_state.players[pid]
            
            if zone == "BATTLE_AREA":
                cards = player.battle_area
            elif zone == "HAND":
                cards = player.hand
            elif zone == "TRASH":
                cards = player.trash
            elif zone == "SHIELD_AREA":
                cards = player.shield_area
            else:
                cards = []
            
            for card in cards:
                # Exclude self if specified
                if exclude_self and card == context.source_card:
                    continue
                
                # Check card type
                if card_type:
                    card_data = card.card_data if hasattr(card, 'card_data') else card
                    if card_data.type != card_type:
                        continue
                
                # Check traits
                if traits:
                    card_data = card.card_data if hasattr(card, 'card_data') else card
                    card_traits = card_data.traits if hasattr(card_data, 'traits') else []
                    
                    if trait_operator == "ANY":
                        if not any(trait in card_traits for trait in traits):
                            continue
                    else:  # ALL
                        if not all(trait in card_traits for trait in traits):
                            continue
                
                count += 1
        
        # Count for appropriate player(s)
        if player_id is not None:
            count_in_zone(player_id)
        else:
            count_in_zone(0)
            count_in_zone(1)
        
        # Compare count with condition
        return TargetResolver._compare(count, operator, value)
    
    @staticmethod
    def _evaluate_check_stat(context: EffectContext, condition: Dict) -> bool:
        """Evaluate CHECK_STAT condition"""
        target_spec = condition.get("target")
        stat = condition.get("stat")
        operator = condition.get("operator")
        value = condition.get("value")
        
        # Resolve target
        if target_spec:
            targets = TargetResolver.resolve_target(context, target_spec)
        else:
            # Default to self
            targets = [context.source_card]
        
        if not targets:
            return False
        
        # Check if any target matches (for now, check first target)
        target = targets[0]
        
        # Get stat value
        if stat == "HP":
            target_value = target.current_hp if hasattr(target, 'current_hp') else 0
        elif stat == "AP":
            target_value = target.ap if hasattr(target, 'ap') else 0
        elif stat == "LEVEL":
            card_data = target.card_data if hasattr(target, 'card_data') else target
            target_value = card_data.level if hasattr(card_data, 'level') else 0
        elif stat == "COST":
            card_data = target.card_data if hasattr(target, 'card_data') else target
            target_value = card_data.cost if hasattr(card_data, 'cost') else 0
        else:
            return False
        
        return TargetResolver._compare(target_value, operator, value)
    
    @staticmethod
    def _evaluate_check_turn(context: EffectContext, condition: Dict) -> bool:
        """Evaluate CHECK_TURN condition"""
        turn_owner = condition.get("turn_owner")
        
        game_state = context.game_state
        current_player = game_state.turn_player
        
        if turn_owner == "SELF":
            return current_player == context.source_player_id
        elif turn_owner == "OPPONENT":
            return current_player != context.source_player_id
        
        return True
    
    @staticmethod
    def _evaluate_check_card_state(context: EffectContext, condition: Dict) -> bool:
        """Evaluate CHECK_CARD_STATE condition"""
        target_spec = condition.get("target")
        state = condition.get("state")
        
        # Resolve target
        if target_spec:
            targets = TargetResolver.resolve_target(context, target_spec)
        else:
            targets = [context.source_card]
        
        if not targets:
            return False
        
        target = targets[0]
        
        # Check state
        if state == "ACTIVE":
            return not target.is_rested if hasattr(target, 'is_rested') else False
        elif state == "RESTED":
            return target.is_rested if hasattr(target, 'is_rested') else False
        elif state == "PAIRED":
            return target.paired_pilot is not None if hasattr(target, 'paired_pilot') else False
        elif state == "LINKED":
            return target.is_linked if hasattr(target, 'is_linked') else False
        
        return True
    
    @staticmethod
    def _evaluate_check_player_level(context: EffectContext, condition: Dict) -> bool:
        """Evaluate CHECK_PLAYER_LEVEL condition"""
        player = condition.get("player", "SELF")
        operator = condition.get("operator", ">=")
        value = condition.get("value", 0)
        
        if player == "SELF":
            player_id = context.source_player_id
        else:
            player_id = 1 - context.source_player_id
        
        game_state = context.game_state
        player_obj = game_state.players[player_id]
        
        # Get player level (assuming it's stored)
        player_level = getattr(player_obj, 'level', 0)
        
        return TargetResolver._compare(player_level, operator, value)
    
    @staticmethod
    def _evaluate_check_milled_traits(context: EffectContext, condition: Dict) -> bool:
        """
        Evaluate CHECK_MILLED_TRAITS condition.
        Checks if recently milled cards have specific traits.
        
        Args:
            condition: {
                "type": "CHECK_MILLED_TRAITS",
                "traits": ["trait1", "trait2"],
                "count": ">=1" (how many milled cards need the trait)
            }
        """
        traits = condition.get("traits", [])
        count_str = condition.get("count", ">=1")
        
        # Parse count string (e.g., ">=1", "==2")
        import re
        match = re.match(r'([><=!]+)(\d+)', count_str)
        if match:
            operator = match.group(1)
            value = int(match.group(2))
        else:
            operator = ">="
            value = 1
        
        # Get milled cards from context
        milled_cards = getattr(context, 'last_milled_cards', [])
        
        # Count how many milled cards have the traits
        matching_count = 0
        for card in milled_cards:
            card_traits = card.traits if hasattr(card, 'traits') else []
            if any(trait in card_traits for trait in traits):
                matching_count += 1
        
        # Compare count
        return TargetResolver._compare(matching_count, operator, value)
    
    @staticmethod
    def _evaluate_check_link_status(context: EffectContext, condition: Dict) -> bool:
        """
        Evaluate CHECK_LINK_STATUS condition.
        Checks if a unit is linked with a pilot.
        
        Args:
            condition: {
                "type": "CHECK_LINK_STATUS",
                "target": "SELF" or target_spec,
                "is_linked": true/false
            }
        """
        target = condition.get("target", "SELF")
        expected_linked = condition.get("is_linked", True)
        
        # Get target unit
        if target == "SELF":
            unit = context.source_card
        else:
            # Resolve target
            targets = TargetResolver.resolve_target(context, target)
            if not targets:
                return False
            unit = targets[0]
        
        # Check linked status
        is_linked = unit.is_linked if hasattr(unit, 'is_linked') else False
        
        return is_linked == expected_linked
    
    @staticmethod
    def _evaluate_check_paired_pilot_trait(context: EffectContext, condition: Dict) -> bool:
        """
        Evaluate CHECK_PAIRED_PILOT_TRAIT condition.
        Checks if paired pilot has specific trait(s).
        
        Args:
            condition: {
                "type": "CHECK_PAIRED_PILOT_TRAIT",
                "required_traits": ["trait1", "trait2"],
                "trait_operator": "ANY" | "ALL"
            }
        """
        required_traits = condition.get("required_traits", [])
        trait_operator = condition.get("trait_operator", "ANY")
        
        # Get paired pilot
        unit = context.source_card
        if not hasattr(unit, 'paired_pilot') or not unit.paired_pilot:
            return False
        
        pilot = unit.paired_pilot
        pilot_traits = pilot.card_data.traits if hasattr(pilot.card_data, 'traits') else []
        
        # Check traits
        if trait_operator == "ANY":
            # At least one trait must match
            return any(trait in pilot_traits for trait in required_traits)
        else:  # ALL
            # All traits must match
            return all(trait in pilot_traits for trait in required_traits)


if __name__ == "__main__":
    # Test loading
    print("Testing EffectLoader...")
    
    effect = EffectLoader.load_effect("GD01-007")
    if effect:
        print(f"✓ Loaded effect for GD01-007")
        print(f"  Card ID: {effect.get('card_id')}")
        print(f"  Effects: {len(effect.get('effects', []))}")
    else:
        print("✗ Failed to load effect")
    
    print("\nLoading all effects...")
    all_effects = EffectLoader.load_all_effects()
    print(f"✓ Loaded {len(all_effects)} card effects")
