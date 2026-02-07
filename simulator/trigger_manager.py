"""
Trigger Manager for Gundam Card Game Effect System
Manages effect triggers and event listening
"""
from typing import Dict, List, Any, Optional
from simulator.effect_interpreter import EffectContext, EffectLoader, ConditionEvaluator
from simulator.action_executor import ActionExecutor


class TriggerManager:
    """Manages effect triggers and execution"""
    
    def __init__(self):
        """Initialize trigger manager"""
        self.effects_cache = {}  # Cache loaded effects
        self.event_listeners = {}  # Track continuous effects
        
    def load_effects(self):
        """Load all card effects into memory"""
        self.effects_cache = EffectLoader.load_all_effects()
        print(f"✓ Loaded {len(self.effects_cache)} card effects")
    
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
            if not ConditionEvaluator.evaluate_all(context, conditions):
                continue
            
            # Execute actions
            actions = effect.get("actions", [])
            action_results = ActionExecutor.execute_actions(context, actions)
            
            results.extend(action_results)
        
        return results
    
    def check_continuous_effects(self, game_state: Any) -> Dict[str, List[Any]]:
        """
        Check all continuous effects and apply modifications.
        
        Args:
            game_state: Current game state
            
        Returns:
            Dict of modifications to apply
        """
        modifications = {
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
                        trigger_data={}
                    )
                    
                    # Evaluate conditions
                    conditions = effect.get("conditions", [])
                    if not ConditionEvaluator.evaluate_all(context, conditions):
                        continue
                    
                    # Apply modifications
                    modifications_list = effect.get("modifications", [])
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
            for unit in player.battle_area:
                # Clear continuous effect modifications
                # TODO: Implement proper tracking of temporary vs permanent modifications
                pass
        
        # Apply stat modifiers
        for mod_info in modifications["stat_modifiers"]:
            mod = mod_info["modification"]
            context = mod_info["context"]
            
            # Execute as action
            ActionExecutor.execute(context, mod)
        
        # Apply keyword grants
        for mod_info in modifications["keyword_grants"]:
            mod = mod_info["modification"]
            context = mod_info["context"]
            
            # Execute as action
            ActionExecutor.execute(context, mod)
    
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
        
        # Check units in battle area
        for unit in player.battle_area:
            card_id = unit.card_data.id
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
                restrictions = effect.get("restrictions", {})
                cost = effect.get("cost")
                
                # Check phase restrictions
                current_phase = game_state.current_phase
                valid_phase = False
                
                if "ACTIVATE_MAIN" in triggers and current_phase.value == "MAIN":
                    valid_phase = True
                elif "ACTIVATE_ACTION" in triggers:
                    # During battle action step
                    valid_phase = hasattr(game_state, 'battle_state') and game_state.battle_state
                
                if not valid_phase:
                    continue
                
                # Check once per turn restriction
                if restrictions.get("once_per_turn"):
                    # TODO: Track which abilities have been used this turn
                    pass
                
                # Check cost
                can_pay_cost = TriggerManager._can_pay_cost(game_state, player_id, cost)
                
                if not can_pay_cost:
                    continue
                
                abilities.append({
                    "unit": unit,
                    "effect": effect,
                    "cost": cost
                })
        
        return abilities
    
    @staticmethod
    def _can_pay_cost(game_state: Any, player_id: int, cost: Optional[Dict]) -> bool:
        """Check if player can pay the cost"""
        if not cost:
            return True
        
        cost_type = cost.get("cost_type")
        
        if cost_type == "RESOURCE":
            amount = cost.get("amount", 0)
            player = game_state.players[player_id]
            return player.get_active_resources() >= amount
        
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
        
        return results
    
    @staticmethod
    def _pay_cost(game_state: Any, player_id: int, cost: Optional[Dict], source_unit: Any) -> str:
        """Pay the cost for an activated ability"""
        if not cost:
            return "SUCCESS"
        
        cost_type = cost.get("cost_type")
        player = game_state.players[player_id]
        
        if cost_type == "RESOURCE":
            amount = cost.get("amount", 0)
            # Rest resources
            rested = 0
            for resource in player.resource_area:
                if not resource.is_rested and rested < amount:
                    resource.is_rested = True
                    rested += 1
            
            if rested < amount:
                return f"Not enough resources ({rested}/{amount})"
            
            return "SUCCESS"
        
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


# Global trigger manager instance
_trigger_manager = None

def get_trigger_manager() -> TriggerManager:
    """Get the global trigger manager instance"""
    global _trigger_manager
    if _trigger_manager is None:
        _trigger_manager = TriggerManager()
        _trigger_manager.load_effects()
    return _trigger_manager


if __name__ == "__main__":
    # Test trigger manager
    print("Testing TriggerManager...")
    
    tm = TriggerManager()
    tm.load_effects()
    
    print(f"✓ Trigger manager initialized")
    print(f"  Loaded {len(tm.effects_cache)} card effects")
