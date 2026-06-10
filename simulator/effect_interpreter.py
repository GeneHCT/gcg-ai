"""
Effect Interpreter for Gundam Card Game
Executes card effects from JSON schema
"""
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
from simulator.ir_vocabulary import SUPPORTED_CONDITION_TYPES

DEFAULT_EFFECT_DIRS = ["card_effects_converted", "card_effects_exburst"]


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
    def load_effect(card_id: str, effects_dir: str | List[str] | None = None) -> Optional[Dict]:
        """
        Load effect JSON for a card.
        
        Args:
            card_id: Card ID (e.g., "GD01-007")
            effects_dir: Directory containing effect JSON files
            
        Returns:
            Effect dict or None if not found
        """
        effects_dir = effects_dir or DEFAULT_EFFECT_DIRS
        if isinstance(effects_dir, list):
            for directory in reversed(effects_dir):
                effect_data = EffectLoader.load_effect(card_id, directory)
                if effect_data is not None:
                    return effect_data
            return None
        
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
    def load_all_effects(effects_dir: str | List[str] | None = None) -> Dict[str, Dict]:
        """
        Load all effect JSONs into memory.
        
        Returns:
            Dict mapping card_id to effect dict
        """
        effects_dir = effects_dir or DEFAULT_EFFECT_DIRS
        effects = {}
        if isinstance(effects_dir, list):
            for directory in effects_dir:
                effects.update(EffectLoader.load_all_effects(directory))
            return effects
        
        effects_path = Path(effects_dir)
        
        if not effects_path.exists():
            if effects_path.name == "card_effects_exburst":
                print(f"Warning: ExBurst effect directory not found: {effects_path}")
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
        if isinstance(target_spec, str):
            target_spec = {"selector": target_spec}
        if target_spec is None:
            target_spec = {"selector": "SELF"}
        selector = target_spec.get("selector")
        filters = target_spec.get("filters", {})
        count = target_spec.get("count", 1)
        variable_count = target_spec.get("variable_count")
        selection_method = target_spec.get("selection_method", "CHOOSE")
        
        # Get base targets based on selector
        candidates = TargetResolver._get_candidates(context, selector)
        
        # Apply filters
        filtered = TargetResolver._apply_filters(candidates, filters, context)
        if selector == "SELECTED_CARD" and "count" not in target_spec and not variable_count:
            count = len(filtered)
        
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
        
        elif selector == "FRIENDLY_PLAYER":
            return [game_state.players[source_player_id]]
        
        elif selector == "ALL_PLAYERS":
            return [game_state.players[0], game_state.players[1]]
        
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
        
        elif selector == "ENEMY_RESOURCE":
            return game_state.players[opponent_id].resource_area.copy()
        
        # Contextual selectors
        elif selector == "BATTLING_UNIT":
            # Get the unit being battled (from trigger data)
            return [context.trigger_data.get("battling_unit")] if "battling_unit" in context.trigger_data else []
        
        elif selector == "LOOKED_AT_CARD":
            if "looked_at_cards" in context.trigger_data:
                return context.trigger_data["looked_at_cards"].copy()
            return [context.trigger_data.get("looked_at_card")] if "looked_at_card" in context.trigger_data else []

        elif selector == "SELECTED_CARD":
            return context.trigger_data.get("selected_cards", []).copy()
        
        # Zone selectors
        elif selector == "FRIENDLY_RESOURCE":
            return game_state.players[source_player_id].resource_area.copy()
        
        elif selector == "SELF_TRASH":
            return game_state.players[source_player_id].trash.copy()
        
        elif selector == "OPPONENT_TRASH":
            return game_state.players[opponent_id].trash.copy()
        
        elif selector == "SELF_SHIELDS":
            return game_state.players[source_player_id].shield_area.copy()
        
        elif selector == "FRIENDLY_SHIELDS":
            return game_state.players[source_player_id].shield_area.copy()
        
        elif selector == "OPPONENT_SHIELDS":
            return game_state.players[opponent_id].shield_area.copy()
        
        elif selector == "ENEMY_SHIELDS":
            return game_state.players[opponent_id].shield_area.copy()
        
        elif selector == "SELF_HAND":
            return game_state.players[source_player_id].hand.copy()
        
        elif selector == "OPPONENT_HAND":
            return game_state.players[opponent_id].hand.copy()
        
        elif selector == "SELF_DECK":
            return game_state.players[source_player_id].main_deck.copy()
        
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
            card_data = target.card_data if hasattr(target, 'card_data') else target
            if not hasattr(card_data, 'type'):
                return False
            if str(card_data.type).upper() != str(filters["card_type"]).upper():
                return False
        
        # Color filter
        if "color" in filters:
            card_data = target.card_data if hasattr(target, 'card_data') else target
            if not hasattr(card_data, 'color'):
                return False
            if str(card_data.color).lower() != str(filters["color"]).lower():
                return False
        
        # Name/text filters
        if "name_contains" in filters:
            card_data = target.card_data if hasattr(target, 'card_data') else target
            names = TargetResolver._card_names(card_data)
            if not any(str(filters["name_contains"]).lower() in name.lower() for name in names):
                return False

        if "text_contains" in filters:
            card_data = target.card_data if hasattr(target, 'card_data') else target
            effect_text = " ".join(getattr(card_data, 'effect', []) or [])
            searchable_text = f"{getattr(card_data, 'name', '')} {effect_text}".lower()
            if str(filters["text_contains"]).lower() not in searchable_text:
                return False
        
        # Traits filter
        if "traits" in filters:
            required_traits = filters["traits"]
            trait_operator = filters.get("trait_operator", "ANY")
            card_data = target.card_data if hasattr(target, 'card_data') else target
            target_traits = card_data.traits if hasattr(card_data, 'traits') else []
            
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
            if isinstance(level_filter, dict):
                operator = level_filter.get("operator", "==")
                value = level_filter.get("value")
            else:
                operator = "=="
                value = level_filter
            
            card_data = target.card_data if hasattr(target, 'card_data') else target
            if not hasattr(card_data, 'level'):
                return False
            target_level = card_data.level
            
            if not TargetResolver._compare(target_level, operator, value):
                return False
        
        # HP filter
        if "hp" in filters:
            hp_filter = filters["hp"]
            if isinstance(hp_filter, dict):
                operator = hp_filter.get("operator", "==")
                value = hp_filter.get("value")
            else:
                operator = "=="
                value = hp_filter
            
            if not hasattr(target, 'current_hp'):
                return False
            
            if not TargetResolver._compare(target.current_hp, operator, value):
                return False
        
        # AP filter
        if "ap" in filters:
            ap_filter = filters["ap"]
            if isinstance(ap_filter, dict):
                operator = ap_filter.get("operator", "==")
                value = ap_filter.get("value")
            else:
                operator = "=="
                value = ap_filter
            
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
        
        # Damage/link/pilot filters used for printed target qualifications.
        if "damaged" in filters:
            is_damaged = hasattr(target, 'current_hp') and hasattr(target, 'hp') and target.current_hp < target.hp
            if is_damaged != filters["damaged"]:
                return False
        
        if "is_linked" in filters:
            is_linked = bool(getattr(target, 'is_linked', False))
            if is_linked != filters["is_linked"]:
                return False
        
        if "paired_pilot_traits" in filters:
            required_traits = filters["paired_pilot_traits"]
            if isinstance(required_traits, str):
                required_traits = [required_traits]
            pilot = getattr(target, 'paired_pilot', None)
            if not required_traits:
                if pilot is None:
                    return False
                return True
            pilot_card = getattr(pilot, 'card_data', None)
            pilot_traits = getattr(pilot_card, 'traits', []) if pilot_card else []
            if not any(trait in pilot_traits for trait in required_traits):
                return False
        
        # Token filter
        if "is_token" in filters:
            is_token_required = filters["is_token"]
            
            card_data = target.card_data if hasattr(target, 'card_data') else target
            card_id = str(getattr(card_data, "id", "")).upper()
            card_type = str(getattr(card_data, "type", "")).upper()
            is_token = bool(getattr(card_data, "is_token", False)) or "TOKEN" in card_id or "TOKEN" in card_type or card_id.startswith("T-")
            
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
    def _card_names(card_data: Any) -> list[str]:
        names = [str(getattr(card_data, "name", ""))]
        names.extend(str(alias) for alias in getattr(card_data, "name_aliases", []) if alias)
        card_id = getattr(card_data, "id", None)
        if card_id:
            try:
                effect_data = EffectLoader.load_effect(str(card_id))
            except Exception:
                effect_data = None
            for effect in (effect_data or {}).get("continuous_effects", []):
                for action in [*effect.get("actions", []), *effect.get("modifiers", effect.get("modifications", []))]:
                    if isinstance(action, dict) and action.get("type") == "ADD_NAME_ALIAS":
                        alias = action.get("alias") or action.get("name")
                        if alias:
                            names.append(str(alias))
        return names
    
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
    def evaluate_all(context: EffectContext, conditions: List[Dict], strict: bool = False) -> bool:
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
            if not ConditionEvaluator.evaluate(context, condition, strict=strict):
                return False
        
        return True
    
    @staticmethod
    def evaluate(context: EffectContext, condition: Dict, strict: bool = False) -> bool:
        """Evaluate a single condition"""
        if condition is None:
            return True
        condition_type = condition.get("type")
        if strict and condition_type not in SUPPORTED_CONDITION_TYPES:
            raise ValueError(f"Unknown condition type: {condition_type}")
        
        if condition_type == "COUNT_CARDS":
            return ConditionEvaluator._evaluate_count_cards(context, condition)
        
        elif condition_type == "CHECK_STAT":
            return ConditionEvaluator._evaluate_check_stat(context, condition)
        
        elif condition_type == "CHECK_TURN":
            return ConditionEvaluator._evaluate_check_turn(context, condition)
        
        elif condition_type == "CHECK_CARD_STATE":
            return ConditionEvaluator._evaluate_check_card_state(context, condition)

        elif condition_type == "CHECK_DAMAGE":
            return ConditionEvaluator._evaluate_check_damage(context, condition)
        
        elif condition_type == "CHECK_TRAIT":
            return ConditionEvaluator._evaluate_check_trait(context, condition)
        
        elif condition_type == "CHECK_COLOR":
            return ConditionEvaluator._evaluate_check_color(context, condition)
        
        elif condition_type == "CHECK_KEYWORD":
            return ConditionEvaluator._evaluate_check_keyword(context, condition)
        
        elif condition_type == "CHECK_PLAYER_LEVEL":
            return ConditionEvaluator._evaluate_check_player_level(context, condition)
        
        elif condition_type == "CHECK_MILLED_TRAITS":
            return ConditionEvaluator._evaluate_check_milled_traits(context, condition)
        
        elif condition_type == "CHECK_LINK_STATUS":
            return ConditionEvaluator._evaluate_check_link_status(context, condition)
        
        elif condition_type == "CHECK_PAIR_STATUS":
            return ConditionEvaluator._evaluate_check_pair_status(context, condition)
        
        elif condition_type == "CHECK_TARGET":
            return ConditionEvaluator._evaluate_check_target(context, condition)
        
        elif condition_type == "CHECK_PAIRED_PILOT_COLOR":
            return ConditionEvaluator._evaluate_check_paired_pilot_color(context, condition)
        
        elif condition_type == "CHECK_PAIRED_PILOT_TRAIT":
            return ConditionEvaluator._evaluate_check_paired_pilot_trait(context, condition)
        
        elif condition_type in {"ACTION_COMPLETED", "CHECK_ACTION_SUCCESS", "CONDITIONAL_BRANCH"}:
            return True
        
        elif condition_type == "ON_UNIT_DESTROYED_BY_DAMAGE":
            return bool(context.trigger_data.get("destroyed_by_damage", True))
        
        # Add more condition types as needed
        
        return True  # Unknown condition types pass by default outside strict validation
    
    @staticmethod
    def _evaluate_count_cards(context: EffectContext, condition: Dict) -> bool:
        """Evaluate COUNT_CARDS condition"""
        if condition.get("target") or condition.get("selector") or condition.get("filters"):
            target_spec = condition.get("target") or {"selector": condition.get("selector", condition.get("zone", "SELF_TRASH"))}
            if isinstance(target_spec, str):
                target_spec = {"selector": target_spec}
            if condition.get("filters"):
                target_spec = dict(target_spec)
                target_spec["filters"] = condition["filters"]
            count = len(TargetResolver.resolve_target(context, target_spec))
            return TargetResolver._compare(count, condition.get("operator", ">="), condition.get("value", 1))
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
    def _evaluate_check_trait(context: EffectContext, condition: Dict) -> bool:
        traits = condition.get("traits") or condition.get("required_traits") or []
        if isinstance(traits, str):
            traits = [traits]
        trait_operator = condition.get("trait_operator", "ANY")
        targets = ConditionEvaluator._condition_targets(context, condition)
        if not targets:
            return False
        return any(
            ConditionEvaluator._target_has_traits(target, traits, trait_operator)
            for target in targets
        )

    @staticmethod
    def _evaluate_check_color(context: EffectContext, condition: Dict) -> bool:
        expected_color = str(condition.get("color") or "").lower()
        targets = ConditionEvaluator._condition_targets(context, condition)
        if not targets or not expected_color:
            return False
        return any(
            str(getattr(ConditionEvaluator._card_data(target), 'color', '')).lower() == expected_color
            for target in targets
        )

    @staticmethod
    def _evaluate_check_keyword(context: EffectContext, condition: Dict) -> bool:
        keyword = str(condition.get("keyword") or condition.get("has_keyword") or "").lower()
        targets = ConditionEvaluator._condition_targets(context, condition)
        if not targets or not keyword:
            return False
        return any(hasattr(target, 'has_keyword') and target.has_keyword(keyword) for target in targets)

    @staticmethod
    def _condition_targets(context: EffectContext, condition: Dict) -> List[Any]:
        target_spec = condition.get("target")
        if target_spec:
            return ConditionEvaluator._resolve_condition_targets(context, target_spec)
        return [context.source_card]

    @staticmethod
    def _resolve_condition_targets(context: EffectContext, target_spec: Any) -> List[Any]:
        if isinstance(target_spec, str):
            normalized_target = {"selector": target_spec}
        elif isinstance(target_spec, dict):
            normalized_target = dict(target_spec)
        else:
            return []
        normalized_target.setdefault("count", 999)
        return TargetResolver.resolve_target(context, normalized_target)

    @staticmethod
    def _target_has_traits(target: Any, traits: List[str], trait_operator: str) -> bool:
        target_traits = getattr(ConditionEvaluator._card_data(target), 'traits', [])
        if trait_operator == "ALL":
            return all(trait in target_traits for trait in traits)
        return any(trait in target_traits for trait in traits)

    @staticmethod
    def _card_data(target: Any) -> Any:
        return target.card_data if hasattr(target, 'card_data') else target
    
    @staticmethod
    def _evaluate_check_card_state(context: EffectContext, condition: Dict) -> bool:
        """Evaluate CHECK_CARD_STATE condition"""
        target_spec = condition.get("target")
        state = condition.get("state") or condition.get("value")
        
        # Resolve target
        if target_spec:
            targets = ConditionEvaluator._resolve_condition_targets(context, target_spec)
        else:
            targets = [context.source_card]
        
        if not targets:
            return False
        
        def matches(target: Any) -> bool:
            if state == "ACTIVE":
                return not target.is_rested if hasattr(target, 'is_rested') else False
            if state == "RESTED":
                return target.is_rested if hasattr(target, 'is_rested') else False
            if state == "PAIRED":
                return target.paired_pilot is not None if hasattr(target, 'paired_pilot') else False
            if state == "LINKED":
                return target.is_linked if hasattr(target, 'is_linked') else False
            if state == "DESTROYED":
                return target.is_destroyed if hasattr(target, 'is_destroyed') else False
            if state == "ATTACKING":
                return context.trigger_event == "ON_ATTACK" and target == context.source_card
            return False

        if state in {"ACTIVE", "RESTED", "PAIRED", "LINKED", "DESTROYED", "ATTACKING"}:
            return any(matches(target) for target in targets)
        
        return False

    @staticmethod
    def _evaluate_check_damage(context: EffectContext, condition: Dict) -> bool:
        target_spec = condition.get("target")
        operator = condition.get("operator", ">")
        value = condition.get("value", 0)
        targets = ConditionEvaluator._resolve_condition_targets(context, target_spec) if target_spec else [context.source_card]
        if not targets:
            return False
        for target in targets:
            if not hasattr(target, "current_hp") or not hasattr(target, "hp"):
                continue
            damage = max(0, target.hp - target.current_hp)
            if TargetResolver._compare(damage, operator, value):
                return True
        return False
    
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
    def _evaluate_check_pair_status(context: EffectContext, condition: Dict) -> bool:
        target_spec = condition.get("target", {"selector": "SELF"})
        expected = condition.get("is_paired", condition.get("paired", True))
        targets = TargetResolver.resolve_target(context, target_spec) if isinstance(target_spec, dict) else [context.source_card]
        if not targets:
            return False
        return any((getattr(target, "paired_pilot", None) is not None) == expected for target in targets)
    
    @staticmethod
    def _evaluate_check_target(context: EffectContext, condition: Dict) -> bool:
        target_spec = condition.get("target")
        filters = condition.get("filters", {})
        if target_spec or filters or condition.get("exists") is not None:
            targets = ConditionEvaluator._resolve_condition_targets(context, target_spec or {"selector": "SELF"})
            if filters:
                targets = [target for target in targets if TargetResolver._matches_filters(target, filters, context)]
            exists = bool(targets)
            if condition.get("exists") is not None:
                return exists == bool(condition.get("exists"))
            if filters:
                return exists

        event = str(condition.get("event") or "").upper()
        if event == "DEPLOY_SOURCE":
            expected_zone = str(condition.get("source_zone") or "").upper()
            actual_zone = str(
                context.trigger_data.get("source_zone")
                or context.trigger_data.get("from_zone")
                or context.trigger_data.get("deployed_from")
                or ""
            ).upper()
            return bool(expected_zone) and actual_zone == expected_zone
        if event == "USED_EX_RESOURCE":
            return bool(
                context.trigger_data.get("used_ex_resource")
                or context.trigger_data.get("paid_with_ex_resource")
                or context.trigger_data.get("ex_resource_used")
            )
        if event == "ACTIVATED":
            return bool(context.trigger_data.get("activated", True))
        if event == "RECEIVING_EFFECT_DAMAGE":
            return context.trigger_event == "ON_RECEIVE_EFFECT_DAMAGE"
        if event == "BATTLE_TARGET":
            actual_target = (
                context.trigger_data.get("target")
                or context.trigger_data.get("attack_target")
                or context.trigger_data.get("battle_target")
                or context.trigger_data.get("battling_unit")
                or context.trigger_data.get("defender")
            )
            return hasattr(actual_target, "card_data")
        if event == "BLOCKING_UNIT":
            actual_target = (
                context.trigger_data.get("blocker")
                or context.trigger_data.get("blocking_unit")
                or context.trigger_data.get("defender")
            )
            return hasattr(actual_target, "card_data")

        expected = str(
            condition.get("target_type")
            or condition.get("target_selector")
            or condition.get("attack_target")
            or condition.get("value")
            or ""
        ).upper()
        if not expected and condition.get("attacking_player") is True:
            expected = "PLAYER"
        actual_target = (
            context.trigger_data.get("target")
            or context.trigger_data.get("attack_target")
            or context.trigger_data.get("defender")
        )
        if expected in {"PLAYER", "ENEMY_PLAYER", "OPPONENT_PLAYER"}:
            return actual_target in {"PLAYER", "ENEMY_PLAYER"} or not hasattr(actual_target, "card_data")
        if expected in {"UNIT", "ENEMY_UNIT"}:
            return hasattr(actual_target, "card_data")
        return True
    
    @staticmethod
    def _evaluate_check_paired_pilot_color(context: EffectContext, condition: Dict) -> bool:
        expected_color = str(condition.get("color") or condition.get("required_color") or "").lower()
        targets = ConditionEvaluator._condition_targets(context, condition)
        if not targets or not expected_color:
            return False
        for unit in targets:
            pilot = getattr(unit, "paired_pilot", None)
            pilot_card = getattr(pilot, "card_data", None)
            if pilot_card and str(getattr(pilot_card, "color", "")).lower() == expected_color:
                return True
        return False
    
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
