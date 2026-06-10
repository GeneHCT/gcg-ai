"""
Trigger Manager for Gundam Card Game Effect System
Manages effect triggers and event listening
"""
import copy
import re
from typing import Dict, List, Any, Optional
from simulator.effect_interpreter import DEFAULT_EFFECT_DIRS, EffectContext, EffectLoader, ConditionEvaluator
from simulator.action_executor import ActionExecutor


class TriggerManager:
    """Manages effect triggers and execution"""
    
    def __init__(
        self,
        strict: bool = False,
        effects_dirs: Optional[List[str]] = None,
        allow_unsupported: bool = False,
    ):
        """Initialize trigger manager"""
        self.effects_cache = {}  # Cache loaded effects
        self.event_listeners = {}  # Track continuous effects
        self.strict = strict
        self.effects_dirs = effects_dirs or DEFAULT_EFFECT_DIRS
        self.allow_unsupported = allow_unsupported
        self.load_report = {
            "loaded": 0,
            "supported": 0,
            "partial": 0,
            "unsupported": 0,
            "unknown": 0,
            "skipped_effects": 0,
            "skipped_cards": 0,
        }
        
    def load_effects(self, effects_dirs: Optional[List[str]] = None):
        """Load all card effects into memory"""
        self.effects_dirs = effects_dirs or self.effects_dirs
        loaded_effects = EffectLoader.load_all_effects(self.effects_dirs)
        self.effects_cache = self._filter_loaded_effects(loaded_effects)
        self.load_report["loaded"] = len(self.effects_cache)
        print(
            "✓ Loaded "
            f"{len(self.effects_cache)} card effects "
            f"from {', '.join(self.effects_dirs)} "
            f"(supported={self.load_report['supported']}, "
            f"partial={self.load_report['partial']}, "
            f"unsupported={self.load_report['unsupported']}, "
            f"skipped_cards={self.load_report['skipped_cards']}, "
            f"skipped_effects={self.load_report['skipped_effects']})"
        )
    
    def trigger_event(self, event_type: str, game_state: Any, source_card: Any, 
                     source_player_id: int, **trigger_data) -> List[str]:
        """
        Trigger an event and execute all matching effects.
        
        Args:
            event_type: Event type (e.g., "ON_DEPLOY", "ON_ATTACK")
            game_state: Current game state
            source_card: Card that triggered the event
            source_player_id: ID of player who owns the source card
            **trigger_data: Additional data about the trigger
            
        Returns:
            List of effect execution results
        """
        results = []
        
        # Get card effect data
        card_id = source_card.card_data.id if hasattr(source_card, 'card_data') else source_card.id
        effect_data = self.effects_cache.get(card_id)
        
        if not effect_data:
            return results
        
        # Create effect context
        context = EffectContext(
            game_state=game_state,
            source_card=source_card,
            source_player_id=source_player_id,
            trigger_event=event_type,
            trigger_data=trigger_data
        )
        
        # Check all effects for matching triggers
        effects = effect_data.get("effects", [])
        
        for effect in effects:
            effect_type = effect.get("effect_type")
            
            # Only process TRIGGERED and ACTIVATED effects here
            if effect_type not in ["TRIGGERED", "ACTIVATED"]:
                continue
            
            # Check if trigger matches
            triggers = effect.get("triggers", [])
            if event_type not in triggers:
                continue
            
            # For ACTIVATED effects, check if it's being activated
            if effect_type == "ACTIVATED":
                # This would require player choice - skip for now
                # TODO: Integrate with action selection
                continue
            
            # Evaluate conditions
            conditions = effect.get("conditions", [])
            if not ConditionEvaluator.evaluate_all(context, conditions, strict=self.strict):
                continue
            
            # Execute actions
            actions = [
                self._apply_condition_target_filters(action, conditions)
                for action in effect.get("actions", [])
            ]
            action_results = ActionExecutor.execute_actions(context, actions, strict=self.strict)
            
            results.extend(action_results)
        
        return results

    @staticmethod
    def _apply_condition_target_filters(action: Dict[str, Any], conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        action = copy.deepcopy(action)
        target = action.get("target")
        if not isinstance(target, dict):
            return action

        selector = target.get("selector")
        if not selector:
            return action

        for condition in conditions:
            if condition.get("type") != "CHECK_CARD_STATE":
                continue
            condition_target = condition.get("target")
            condition_selector = (
                condition_target.get("selector")
                if isinstance(condition_target, dict)
                else condition_target
            )
            if condition_selector != selector:
                continue
            if condition.get("operator", "==") != "==":
                continue

            state = condition.get("state") or condition.get("value")
            if state in {"ACTIVE", "RESTED"}:
                target.setdefault("filters", {}).setdefault("state", state)

        return action

    def _filter_loaded_effects(self, loaded_effects: Dict[str, Dict]) -> Dict[str, Dict]:
        filtered_effects = {}
        self.load_report.update({
            "supported": 0,
            "partial": 0,
            "unsupported": 0,
            "unknown": 0,
            "skipped_effects": 0,
            "skipped_cards": 0,
        })

        for card_id, effect_data in loaded_effects.items():
            metadata = effect_data.get("metadata", {}) if isinstance(effect_data, dict) else {}
            support_status = metadata.get("support_status", "unknown")
            if support_status not in {"supported", "partial", "unsupported"}:
                support_status = "unknown"
            self.load_report[support_status] += 1

            if support_status == "unsupported" and not self.allow_unsupported:
                self.load_report["skipped_cards"] += 1
                if self.strict:
                    raise ValueError(f"Unsupported effect IR for {card_id}")
                continue

            filtered = dict(effect_data)
            filtered["effects"] = self._filter_effect_list(card_id, effect_data.get("effects", []))
            filtered["continuous_effects"] = self._filter_effect_list(
                card_id,
                effect_data.get("continuous_effects", []),
            )
            filtered_effects[card_id] = filtered

        return filtered_effects

    def _filter_effect_list(self, card_id: str, effects: List[Dict]) -> List[Dict]:
        filtered = []
        for effect in effects:
            if effect.get("is_supported") is False and not self.allow_unsupported:
                self.load_report["skipped_effects"] += 1
                if self.strict:
                    effect_id = effect.get("effect_id", card_id)
                    raise ValueError(f"Unsupported effect IR for {effect_id}")
                continue
            filtered.append(effect)
        return filtered

    def get_missing_effect_ids(self, card_ids: List[str]) -> List[str]:
        """Return card IDs that do not have any loaded effect IR."""
        return sorted({card_id for card_id in card_ids if card_id not in self.effects_cache})

    @staticmethod
    def has_timing(effect: Dict, timing: str) -> bool:
        """Return whether an effect is usable in a runtime timing window."""
        return timing in effect.get("triggers", [])

    @staticmethod
    def normalize_restrictions(restrictions: Any) -> Dict[str, Any]:
        """Accept legacy dict restrictions and ExBurst list restrictions."""
        if isinstance(restrictions, dict):
            return restrictions
        if isinstance(restrictions, list):
            normalized = {}
            for restriction in restrictions:
                key = str(restriction).lower()
                if key == "once_per_turn":
                    normalized["once_per_turn"] = True
            return normalized
        return {}

    @staticmethod
    def normalize_cost(cost: Any) -> Optional[Dict[str, Any] | int]:
        """Accept common activation cost shapes and normalize resource costs."""
        if cost is None:
            return None
        if isinstance(cost, int):
            return cost
        if isinstance(cost, str):
            text = cost.strip()
            circled_costs = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
            if text in circled_costs:
                return {"cost_type": "RESOURCE", "amount": circled_costs[text]}
            if text.isdigit():
                return {"cost_type": "RESOURCE", "amount": int(text)}
        if isinstance(cost, dict):
            if "cost_type" in cost:
                return cost
            if "amount" in cost:
                return {"cost_type": "RESOURCE", "amount": cost.get("amount", 0)}
        return cost
    
    def check_continuous_effects(self, game_state: Any) -> Dict[str, List[Any]]:
        """
        Check all continuous effects and apply modifications.
        
        Args:
            game_state: Current game state
            
        Returns:
            Dict of modifications to apply
        """
        modifications = {
            "cost_modifiers": [],
            "damage_reductions": [],
            "stat_modifiers": [],
            "keyword_grants": []
        }
        
        # Check all cards in play for continuous effects
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            
            # Check units in battle area
            for unit in player.battle_area:
                card_id = unit.card_data.id
                effect_data = self.effects_cache.get(card_id)
                
                if not effect_data:
                    continue
                
                # Check continuous effects
                continuous_effects = effect_data.get("continuous_effects", [])
                
                for effect in continuous_effects:
                    # Create context
                    context = EffectContext(
                        game_state=game_state,
                        source_card=unit,
                        source_player_id=player_id,
                        trigger_event="CONTINUOUS",
                        trigger_data={
                            "effect_text": effect.get("metadata", {}).get("raw_text", effect.get("description", "")),
                        }
                    )
                    
                    # Evaluate conditions
                    conditions = effect.get("conditions", [])
                    if not ConditionEvaluator.evaluate_all(context, conditions, strict=self.strict):
                        continue
                    
                    # Apply modifications
                    modifications_list = [
                        *effect.get("modifiers", effect.get("modifications", [])),
                        *effect.get("actions", []),
                    ]
                    for mod in modifications_list:
                        mod_type = mod.get("type")
                        
                        if mod_type == "MODIFY_STAT":
                            modifications["stat_modifiers"].append({
                                "source": unit,
                                "modification": mod,
                                "context": context
                            })
                        
                        elif mod_type == "GRANT_KEYWORD":
                            modifications["keyword_grants"].append({
                                "source": unit,
                                "modification": mod,
                                "context": context
                            })
                        
                        elif mod_type == "MODIFY_COST":
                            modifications["cost_modifiers"].append({
                                "source": unit,
                                "modification": mod,
                                "context": context
                            })
                        
                        elif mod_type == "REDUCE_DAMAGE":
                            modifications["damage_reductions"].append({
                                "source": unit,
                                "modification": mod,
                                "context": context
                            })
        
        return modifications
    
    def apply_continuous_effects(self, game_state: Any):
        """
        Apply all active continuous effects to game state.
        Called at the start of each phase or after state changes.
        
        Args:
            game_state: Current game state
        """
        modifications = self.check_continuous_effects(game_state)
        
        # Clear temporary modifications first
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            if hasattr(player, "active_cost_modifiers"):
                player.active_cost_modifiers = []
            for unit in player.battle_area:
                if hasattr(unit, "clear_continuous_effects"):
                    unit.clear_continuous_effects()
                if hasattr(unit, "damage_reductions"):
                    unit.damage_reductions = []
        
        # Apply stat modifiers
        for mod_info in modifications["stat_modifiers"]:
            mod = dict(mod_info["modification"])
            mod.setdefault(
                "source_id",
                f"continuous:{getattr(mod_info['source'], 'card_data', mod_info['source']).id}:stat",
            )
            context = mod_info["context"]
            
            # Execute as action
            ActionExecutor.execute(context, mod)
        
        # Apply keyword grants
        for mod_info in modifications["keyword_grants"]:
            mod = dict(mod_info["modification"])
            if self._is_already_applied_printed_keyword(mod_info["source"], mod_info["context"], mod):
                continue
            mod.setdefault(
                "source_id",
                f"continuous:{getattr(mod_info['source'], 'card_data', mod_info['source']).id}:keyword",
            )
            context = mod_info["context"]
            
            # Execute as action
            ActionExecutor.execute(context, mod)
        
        for mod_info in modifications["cost_modifiers"]:
            mod = mod_info["modification"]
            context = mod_info["context"]
            ActionExecutor.execute(context, mod)
        
        for mod_info in modifications["damage_reductions"]:
            mod = mod_info["modification"]
            context = mod_info["context"]
            ActionExecutor.execute(context, mod)

    @staticmethod
    def _is_already_applied_printed_keyword(source: Any, context: EffectContext, mod: Dict) -> bool:
        """Avoid double-counting standalone printed keywords parsed from card text."""
        target_spec = mod.get("target") or {"selector": "SELF"}
        if isinstance(target_spec, str):
            target_spec = {"selector": target_spec}
        if target_spec.get("selector") != "SELF":
            return False

        keyword = str(mod.get("keyword", "")).lower()
        if not keyword:
            return False

        raw_text = str(context.trigger_data.get("effect_text") or "")
        raw_text = raw_text or str(getattr(source, "card_data", source).effect if hasattr(getattr(source, "card_data", source), "effect") else "")
        keyword_text = keyword.replace("_", r"[-\s]+")
        if not re.match(rf"^\s*[<\[]\s*{keyword_text}(?:\s+\d+)?\s*[>\]]", raw_text, re.IGNORECASE):
            return False

        sources = getattr(source, "keyword_sources", {}).get(keyword, [])
        if "Card base effect" not in sources:
            return False

        value = mod.get("value")
        if value is None:
            return True
        return getattr(source, "get_keyword_value", lambda _keyword: 0)(keyword) >= value
    
    def get_activated_abilities(self, game_state: Any, player_id: int) -> List[Dict]:
        """
        Get all activated abilities available to a player.
        
        Args:
            game_state: Current game state
            player_id: Player ID
            
        Returns:
            List of activated ability dicts
        """
        abilities = []
        
        player = game_state.players[player_id]
        
        sources = list(player.battle_area)
        sources.extend(getattr(player, "bases", []))

        for source in sources:
            card_data = getattr(source, "card_data", source)
            if not hasattr(card_data, "id"):
                continue
            card_id = card_data.id
            effect_data = self.effects_cache.get(card_id)
            
            if not effect_data:
                continue
            
            effects = effect_data.get("effects", [])
            
            for effect in effects:
                if effect.get("effect_type") != "ACTIVATED":
                    continue
                
                # Check if this ability can be activated
                # (consider costs, restrictions, etc.)
                triggers = effect.get("triggers", [])
                restrictions = TriggerManager.normalize_restrictions(effect.get("restrictions", {}))
                cost = TriggerManager.normalize_cost(effect.get("cost", effect.get("activation_cost")))
                
                # Check phase restrictions
                current_phase = game_state.current_phase
                phase_value = getattr(current_phase, "value", str(current_phase)).lower()
                valid_phase = False
                
                if "ACTIVATE_MAIN" in triggers and phase_value == "main" and not getattr(game_state, "in_action_step", False):
                    valid_phase = True
                elif "ACTIVATE_ACTION" in triggers and getattr(game_state, "in_action_step", False):
                    valid_phase = True
                
                if not valid_phase:
                    continue
                
                # Check once per turn restriction
                if restrictions.get("once_per_turn") and TriggerManager._ability_used_this_turn(game_state, effect, source):
                    continue
                
                # Check cost
                can_pay_cost = TriggerManager._can_pay_cost(game_state, player_id, cost)
                
                if not can_pay_cost:
                    continue
                
                abilities.append({
                    "unit": source,
                    "effect": effect,
                    "cost": cost
                })
        
        return abilities
    
    @staticmethod
    def _can_pay_cost(game_state: Any, player_id: int, cost: Optional[Dict]) -> bool:
        """Check if player can pay the cost"""
        if not cost:
            return True
        if isinstance(cost, int):
            from simulator.resource_manager import ResourceManager
            return ResourceManager.can_pay_cost(game_state, player_id, cost)
        
        cost_type = cost.get("cost_type")
        
        if cost_type == "RESOURCE":
            amount = cost.get("amount", 0)
            # Use ResourceManager for accurate check
            from simulator.resource_manager import ResourceManager
            return ResourceManager.can_pay_cost(game_state, player_id, amount)
        
        elif cost_type == "EXILE":
            exile_req = cost.get("exile_requirements", {})
            amount = exile_req.get("amount", 0)
            # TODO: Check if enough cards in trash matching filters
            return True  # Simplified for now
        
        elif cost_type == "REST_SELF":
            # Can always rest self (assuming unit is active)
            return True
        
        return True
    
    def activate_ability(self, game_state: Any, ability_info: Dict) -> List[str]:
        """
        Activate an activated ability.
        
        Args:
            game_state: Current game state
            ability_info: Ability info dict from get_activated_abilities
            
        Returns:
            List of effect execution results
        """
        unit = ability_info["unit"]
        effect = ability_info["effect"]
        cost = ability_info["cost"]
        restrictions = TriggerManager.normalize_restrictions(effect.get("restrictions", {}))
        
        # Pay cost
        cost_result = TriggerManager._pay_cost(game_state, unit.owner_id, cost, unit)
        
        if cost_result != "SUCCESS":
            return [f"Failed to pay cost: {cost_result}"]
        
        # Create context
        context = EffectContext(
            game_state=game_state,
            source_card=unit,
            source_player_id=unit.owner_id,
            trigger_event="ACTIVATED",
            trigger_data={}
        )
        
        # Execute actions
        actions = effect.get("actions", [])
        results = ActionExecutor.execute_actions(context, actions)

        if restrictions.get("once_per_turn"):
            TriggerManager._mark_ability_used(game_state, effect, unit)
        
        return results
    
    @staticmethod
    def _pay_cost(game_state: Any, player_id: int, cost: Optional[Dict], source_unit: Any) -> str:
        """Pay the cost for an activated ability"""
        if not cost:
            return "SUCCESS"
        if isinstance(cost, int):
            from simulator.resource_manager import ResourceManager
            return "SUCCESS" if ResourceManager.pay_cost(game_state, player_id, cost) else f"Not enough resources (need {cost})"
        
        cost_type = cost.get("cost_type")
        player = game_state.players[player_id]
        
        if cost_type == "RESOURCE":
            amount = cost.get("amount", 0)
            # Use ResourceManager to pay cost
            from simulator.resource_manager import ResourceManager
            
            if ResourceManager.pay_cost(game_state, player_id, amount):
                return "SUCCESS"
            else:
                return f"Not enough resources (need {amount})"
        
        elif cost_type == "EXILE":
            exile_req = cost.get("exile_requirements", {})
            source = exile_req.get("source", "TRASH")
            filters = exile_req.get("filters", {})
            amount = exile_req.get("amount", 0)
            
            # Find and exile cards from trash
            if source == "TRASH":
                # TODO: Implement card selection with filters
                # For now, just remove first N cards
                exiled = 0
                for _ in range(amount):
                    if player.trash:
                        player.trash.pop(0)
                        exiled += 1
                
                if exiled < amount:
                    return f"Not enough cards to exile ({exiled}/{amount})"
                
                return "SUCCESS"
        
        elif cost_type == "REST_SELF":
            if source_unit and hasattr(source_unit, 'is_rested'):
                source_unit.is_rested = True
                return "SUCCESS"
        
        return "SUCCESS"

    @staticmethod
    def _ability_usage_key(effect: Dict, source_unit: Any) -> str:
        effect_id = effect.get("effect_id", "unknown")
        return f"{id(source_unit)}:{effect_id}"

    @staticmethod
    def _ability_used_this_turn(game_state: Any, effect: Dict, source_unit: Any) -> bool:
        used = getattr(game_state, "activated_abilities_used_this_turn", set())
        return TriggerManager._ability_usage_key(effect, source_unit) in used

    @staticmethod
    def _mark_ability_used(game_state: Any, effect: Dict, source_unit: Any) -> None:
        if not hasattr(game_state, "activated_abilities_used_this_turn"):
            game_state.activated_abilities_used_this_turn = set()
        game_state.activated_abilities_used_this_turn.add(
            TriggerManager._ability_usage_key(effect, source_unit)
        )


# Global trigger manager instance
_trigger_manager = None

def get_trigger_manager(
    strict: bool = False,
    effects_dirs: Optional[List[str]] = None,
    force_reload: bool = False,
    allow_unsupported: bool = False,
) -> TriggerManager:
    """Get the global trigger manager instance"""
    global _trigger_manager
    requested_dirs = (
        effects_dirs
        if effects_dirs is not None
        else (_trigger_manager.effects_dirs if _trigger_manager is not None else DEFAULT_EFFECT_DIRS)
    )
    should_reload = (
        force_reload
        or _trigger_manager is None
        or _trigger_manager.effects_dirs != requested_dirs
        or _trigger_manager.strict != strict
        or _trigger_manager.allow_unsupported != allow_unsupported
    )
    if should_reload:
        _trigger_manager = TriggerManager(
            strict=strict,
            effects_dirs=requested_dirs,
            allow_unsupported=allow_unsupported,
        )
        _trigger_manager.load_effects()
    return _trigger_manager


def reset_trigger_manager() -> None:
    """Clear the global trigger manager so tests or tools can reconfigure it."""
    global _trigger_manager
    _trigger_manager = None


if __name__ == "__main__":
    # Test trigger manager
    print("Testing TriggerManager...")
    
    tm = TriggerManager()
    tm.load_effects()
    
    print(f"✓ Trigger manager initialized")
    print(f"  Loaded {len(tm.effects_cache)} card effects")
