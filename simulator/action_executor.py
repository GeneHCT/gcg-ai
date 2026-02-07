"""
Action Executor for Gundam Card Game Effect System
Executes all action types defined in the schema
"""
from typing import Dict, List, Any, Optional
from simulator.effect_interpreter import EffectContext, TargetResolver, ConditionEvaluator


class ActionExecutor:
    """Executes effect actions"""
    
    @staticmethod
    def execute_actions(context: EffectContext, actions: List[Dict]) -> List[str]:
        """
        Execute a list of actions in sequence.
        
        Args:
            context: Effect context
            actions: List of action dicts
            
        Returns:
            List of result messages
        """
        results = []
        
        for action in actions:
            result = ActionExecutor.execute(context, action)
            results.append(result)
            
            # Check for conditional_next
            if "conditional_next" in action:
                ActionExecutor._handle_conditional_next(context, action, result)
        
        return results
    
    @staticmethod
    def execute(context: EffectContext, action: Dict) -> str:
        """Execute a single action"""
        action_type = action.get("type")
        
        # Check if action is optional
        optional = action.get("optional", False)
        if optional:
            # TODO: Integrate with agent decision system
            # For now, always execute optional actions
            pass
        
        # Route to appropriate handler
        if action_type == "DRAW":
            return ActionExecutor._execute_draw(context, action)
        
        elif action_type == "DAMAGE_UNIT":
            return ActionExecutor._execute_damage_unit(context, action)
        
        elif action_type == "REST_UNIT":
            return ActionExecutor._execute_rest_unit(context, action)
        
        elif action_type == "SET_ACTIVE":
            return ActionExecutor._execute_set_active(context, action)
        
        elif action_type == "MODIFY_STAT":
            return ActionExecutor._execute_modify_stat(context, action)
        
        elif action_type == "RECOVER_HP":
            return ActionExecutor._execute_recover_hp(context, action)
        
        elif action_type == "GRANT_KEYWORD":
            return ActionExecutor._execute_grant_keyword(context, action)
        
        elif action_type == "DESTROY_CARD":
            return ActionExecutor._execute_destroy_card(context, action)
        
        elif action_type == "DEPLOY_TOKEN":
            return ActionExecutor._execute_deploy_token(context, action)
        
        elif action_type == "PLACE_RESOURCE":
            return ActionExecutor._execute_place_resource(context, action)
        
        elif action_type == "SHIELD_TO_HAND":
            return ActionExecutor._execute_shield_to_hand(context, action)
        
        elif action_type == "CONDITIONAL_BRANCH":
            return ActionExecutor._execute_conditional_branch(context, action)
        
        elif action_type == "MILL":
            return ActionExecutor._execute_mill(context, action)
        
        elif action_type == "DEPLOY_FROM_ZONE":
            return ActionExecutor._execute_deploy_from_zone(context, action)
        
        elif action_type == "GRANT_PROTECTION":
            return ActionExecutor._execute_grant_protection(context, action)
        
        elif action_type == "ADD_TO_SHIELDS":
            return ActionExecutor._execute_add_to_shields(context, action)
        
        elif action_type == "OPTIONAL_ACTION":
            return ActionExecutor._execute_optional_action(context, action)
        
        elif action_type == "EXILE_CARDS":
            return ActionExecutor._execute_exile_cards(context, action)
        
        elif action_type == "GRANT_ATTACK_TARGETING":
            return ActionExecutor._execute_grant_attack_targeting(context, action)
        
        # Add more action types as needed
        
        return f"Unknown action type: {action_type}"
    
    @staticmethod
    def _execute_draw(context: EffectContext, action: Dict) -> str:
        """Execute DRAW action"""
        target = action.get("target", "SELF")
        amount = action.get("amount", 1)
        
        # Determine which player draws
        if target == "SELF":
            player_id = context.source_player_id
        else:  # OPPONENT
            player_id = 1 - context.source_player_id
        
        game_state = context.game_state
        player = game_state.players[player_id]
        
        # Draw cards
        drawn = 0
        for _ in range(amount):
            if player.main_deck:
                card = player.main_deck.pop(0)
                player.hand.append(card)
                drawn += 1
            else:
                # Deck empty - handle game over
                game_state.game_result = "DECK_OUT"
                game_state.winner = 1 - player_id
                break
        
        return f"Player {player_id} drew {drawn} card(s)"
    
    @staticmethod
    def _execute_damage_unit(context: EffectContext, action: Dict) -> str:
        """Execute DAMAGE_UNIT action"""
        target_spec = action.get("target")
        amount = action.get("amount")
        calculation = action.get("calculation")
        
        # Resolve targets
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets for damage"
        
        # Calculate damage amount
        if calculation:
            damage_amount = ActionExecutor._calculate_damage(context, calculation)
        else:
            damage_amount = amount or 0
        
        results = []
        for target in targets:
            if hasattr(target, 'current_hp'):
                old_hp = target.current_hp
                target.current_hp = max(0, target.current_hp - damage_amount)
                results.append(f"{target.card_data.name} took {damage_amount} damage ({old_hp} -> {target.current_hp} HP)")
                
                # Check if destroyed
                if target.current_hp <= 0:
                    # Trigger destroyed effects
                    ActionExecutor._trigger_on_destroyed(context, target)
        
        return "; ".join(results)
    
    @staticmethod
    def _calculate_damage(context: EffectContext, calculation: Dict) -> int:
        """Calculate dynamic damage amount"""
        calc_type = calculation.get("type")
        base = calculation.get("base", 0)
        multiplier = calculation.get("multiplier", {})
        
        if calc_type == "FIXED":
            return base
        
        elif calc_type == "PER_STAT":
            # Get stat value
            stat = multiplier.get("stat")
            source = multiplier.get("source", "SELF")
            divisor = multiplier.get("divisor", 1)
            
            if source == "SELF":
                source_obj = context.source_card
            else:
                # Get from trigger data
                source_obj = context.trigger_data.get("target")
            
            if not source_obj:
                return base
            
            # Get stat value
            if stat == "AP":
                stat_value = source_obj.ap if hasattr(source_obj, 'ap') else 0
            elif stat == "HP":
                stat_value = source_obj.current_hp if hasattr(source_obj, 'current_hp') else 0
            else:
                stat_value = 0
            
            # Calculate: base * (stat_value // divisor)
            return base * (stat_value // divisor)
        
        return base
    
    @staticmethod
    def _execute_rest_unit(context: EffectContext, action: Dict) -> str:
        """Execute REST_UNIT action"""
        target_spec = action.get("target")
        
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets to rest"
        
        results = []
        for target in targets:
            if hasattr(target, 'is_rested'):
                if not target.is_rested:
                    target.is_rested = True
                    results.append(f"Rested {target.card_data.name}")
        
        return "; ".join(results) if results else "No units rested"
    
    @staticmethod
    def _execute_set_active(context: EffectContext, action: Dict) -> str:
        """Execute SET_ACTIVE action"""
        target_spec = action.get("target")
        
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets to set active"
        
        results = []
        for target in targets:
            if hasattr(target, 'is_rested'):
                if target.is_rested:
                    target.is_rested = False
                    results.append(f"Set {target.card_data.name} active")
        
        return "; ".join(results) if results else "No units set active"
    
    @staticmethod
    def _execute_modify_stat(context: EffectContext, action: Dict) -> str:
        """Execute MODIFY_STAT action"""
        target_spec = action.get("target")
        stat = action.get("stat")
        modification = action.get("modification")
        duration = action.get("duration", "PERMANENT")
        
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets for stat modification"
        
        # Parse modification string (e.g., "+2", "-1", "=0")
        if modification.startswith('+'):
            mod_value = int(modification[1:])
            mod_type = "add"
        elif modification.startswith('-'):
            mod_value = int(modification[1:])
            mod_type = "subtract"
        elif modification.startswith('='):
            mod_value = int(modification[1:])
            mod_type = "set"
        else:
            return f"Invalid modification format: {modification}"
        
        results = []
        for target in targets:
            # Apply modification based on stat type
            # For now, this is a simplified implementation
            # Full implementation would track temporary vs permanent modifications
            
            if stat == "AP":
                # Add temporary AP bonus via keywords
                if mod_type == "add":
                    target.add_keyword("ap_bonus", mod_value, source=f"effect_{duration}")
                    results.append(f"{target.card_data.name} gets AP+{mod_value}")
            
            elif stat == "HP":
                if hasattr(target, 'hp_modifier'):
                    if mod_type == "add":
                        target.hp_modifier = getattr(target, 'hp_modifier', 0) + mod_value
                        results.append(f"{target.card_data.name} gets HP+{mod_value}")
            
            # TODO: Implement duration tracking for temporary modifications
        
        return "; ".join(results) if results else "No modifications applied"
    
    @staticmethod
    def _execute_recover_hp(context: EffectContext, action: Dict) -> str:
        """Execute RECOVER_HP action"""
        target_spec = action.get("target")
        amount = action.get("amount", 1)
        
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets for HP recovery"
        
        results = []
        for target in targets:
            if hasattr(target, 'current_hp') and hasattr(target, 'hp'):
                old_hp = target.current_hp
                target.current_hp = min(target.hp, target.current_hp + amount)
                healed = target.current_hp - old_hp
                if healed > 0:
                    results.append(f"{target.card_data.name} recovered {healed} HP ({old_hp} -> {target.current_hp})")
        
        return "; ".join(results) if results else "No HP recovered"
    
    @staticmethod
    def _execute_grant_keyword(context: EffectContext, action: Dict) -> str:
        """Execute GRANT_KEYWORD action"""
        target_spec = action.get("target")
        keyword = action.get("keyword").lower()
        value = action.get("value")
        duration = action.get("duration", "PERMANENT")
        
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets for keyword grant"
        
        results = []
        for target in targets:
            if hasattr(target, 'add_keyword'):
                if value is not None:
                    target.add_keyword(keyword, value, source=f"effect_{duration}")
                    results.append(f"{target.card_data.name} gains <{keyword.title()} {value}> ({duration})")
                else:
                    target.add_keyword(keyword, True, source=f"effect_{duration}")
                    results.append(f"{target.card_data.name} gains <{keyword.title()}> ({duration})")
        
        return "; ".join(results) if results else "No keywords granted"
    
    @staticmethod
    def _execute_destroy_card(context: EffectContext, action: Dict) -> str:
        """Execute DESTROY_CARD action"""
        target_spec = action.get("target")
        
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets to destroy"
        
        results = []
        game_state = context.game_state
        
        for target in targets:
            # Remove from battle area and move to trash
            if hasattr(target, 'owner_id'):
                player = game_state.players[target.owner_id]
                
                if target in player.battle_area:
                    player.battle_area.remove(target)
                    player.trash.append(target.card_data if hasattr(target, 'card_data') else target)
                    results.append(f"Destroyed {target.card_data.name}")
                    
                    # Trigger destroyed effects
                    ActionExecutor._trigger_on_destroyed(context, target)
        
        return "; ".join(results) if results else "No cards destroyed"
    
    @staticmethod
    def _execute_deploy_token(context: EffectContext, action: Dict) -> str:
        """Execute DEPLOY_TOKEN action"""
        token_spec = action.get("token")
        count = action.get("count", 1)
        state = action.get("state", "ACTIVE")
        
        if not token_spec:
            return "No token specification"
        
        # Create token unit
        from simulator.unit import Card, UnitInstance
        
        token_card = Card(
            name=token_spec.get("name", "Token"),
            id=f"TOKEN-{token_spec.get('name', 'Unknown')}",
            type="UNIT",
            color="Colorless",
            level=0,
            cost=0,
            ap=token_spec.get("ap", 0),
            hp=token_spec.get("hp", 1),
            traits=token_spec.get("traits", []),
            zones=["Space", "Earth"],
            link=[],
            effect=[]
        )
        
        game_state = context.game_state
        player = game_state.players[context.source_player_id]
        
        results = []
        for _ in range(count):
            # Create unit instance
            token_unit = UnitInstance(
                card_data=token_card,
                owner_id=context.source_player_id,
                is_rested=(state == "RESTED"),
                turn_deployed=game_state.turn_number
            )
            
            # Add keywords from token spec
            keywords = token_spec.get("keywords", [])
            for kw in keywords:
                keyword_name = kw.get("keyword", "").lower()
                keyword_value = kw.get("value")
                if keyword_value is not None:
                    token_unit.add_keyword(keyword_name, keyword_value, source="token_base")
                else:
                    token_unit.add_keyword(keyword_name, True, source="token_base")
            
            # Add to battle area
            if len(player.battle_area) < 6:  # Max 6 units
                player.battle_area.append(token_unit)
                results.append(f"Deployed {token_card.name} token ({state})")
            else:
                results.append(f"Battle area full, cannot deploy {token_card.name} token")
        
        return "; ".join(results)
    
    @staticmethod
    def _execute_place_resource(context: EffectContext, action: Dict) -> str:
        """Execute PLACE_RESOURCE action"""
        resource_type = action.get("resource_type", "NORMAL")
        state = action.get("state", "ACTIVE")
        
        game_state = context.game_state
        player = game_state.players[context.source_player_id]
        
        if resource_type == "EX":
            player.ex_resources += 1
            return f"Placed 1 EX Resource"
        else:
            # Place normal resource from resource deck
            if player.resource_deck:
                resource = player.resource_deck.pop(0)
                resource.is_rested = (state == "RESTED")
                player.resource_area.append(resource)
                return f"Placed 1 Resource ({state})"
            else:
                return "Resource deck empty"
    
    @staticmethod
    def _execute_shield_to_hand(context: EffectContext, action: Dict) -> str:
        """Execute SHIELD_TO_HAND action"""
        amount = action.get("amount", 1)
        
        game_state = context.game_state
        player = game_state.players[context.source_player_id]
        
        taken = 0
        for _ in range(amount):
            if player.shield_area:
                shield = player.shield_area.pop(0)
                player.hand.append(shield)
                taken += 1
        
        return f"Added {taken} Shield(s) to hand"
    
    @staticmethod
    def _execute_conditional_branch(context: EffectContext, action: Dict) -> str:
        """Execute CONDITIONAL_BRANCH action"""
        conditions_list = action.get("conditions", [])
        
        results = []
        
        for branch in conditions_list:
            condition = branch.get("if")
            then_action = branch.get("then")
            
            # Evaluate condition
            if ConditionEvaluator.evaluate(context, condition):
                # Execute then action
                result = ActionExecutor.execute(context, then_action)
                results.append(result)
                break  # Only execute first matching branch
        
        return "; ".join(results) if results else "No branch conditions met"
    
    @staticmethod
    def _handle_conditional_next(context: EffectContext, action: Dict, result: str):
        """Handle conditional_next after an action"""
        conditional_next = action.get("conditional_next", {})
        
        # Check if action was performed (not failed)
        if "No valid" in result or "failed" in result.lower():
            return
        
        # Execute if_performed actions
        if_performed = conditional_next.get("if_performed", [])
        for next_action in if_performed:
            ActionExecutor.execute(context, next_action)
        
        # Check conditions for conditional actions
        conditions = conditional_next.get("conditions", [])
        if conditions and ConditionEvaluator.evaluate_all(context, conditions):
            actions = conditional_next.get("actions", [])
            for next_action in actions:
                ActionExecutor.execute(context, next_action)
        else:
            # Execute else actions
            else_actions = conditional_next.get("else_actions", [])
            for next_action in else_actions:
                ActionExecutor.execute(context, next_action)
    
    @staticmethod
    def _trigger_on_destroyed(context: EffectContext, destroyed_unit):
        """Trigger ON_DESTROYED effects for a destroyed unit"""
        # This will be called by the TriggerManager
        # For now, just a placeholder
        pass
    
    @staticmethod
    def _execute_mill(context: EffectContext, action: Dict) -> str:
        """
        Execute MILL action - Move cards from deck to trash.
        
        Args:
            action: {
                "type": "MILL",
                "target": "SELF" or "OPPONENT",
                "amount": number,
                "destination": "TRASH" (default)
            }
        """
        target = action.get("target", "SELF")
        amount = action.get("amount", 1)
        destination = action.get("destination", "TRASH")
        
        # Determine which player
        if target == "SELF":
            player_id = context.source_player_id
        else:
            player_id = 1 - context.source_player_id
        
        player = context.game_state.players[player_id]
        
        milled_cards = []
        for _ in range(amount):
            if player.main_deck:
                card = player.main_deck.pop(0)
                if destination == "TRASH":
                    player.trash.append(card)
                    milled_cards.append(card)
        
        # Store milled cards in context for conditional checks
        context.last_milled_cards = milled_cards
        
        return f"Milled {len(milled_cards)} card(s) to {destination}"
    
    @staticmethod
    def _execute_deploy_from_zone(context: EffectContext, action: Dict) -> str:
        """
        Execute DEPLOY_FROM_ZONE action - Deploy a card from a non-hand zone.
        
        Args:
            action: {
                "type": "DEPLOY_FROM_ZONE",
                "source_zone": "TRASH" | "BANISH" | "DECK",
                "target": target_spec,
                "pay_cost": bool,
                "destination": "BATTLE_AREA" (default)
            }
        """
        source_zone = action.get("source_zone", "TRASH")
        target_spec = action.get("target", {})
        pay_cost = action.get("pay_cost", False)
        destination = action.get("destination", "BATTLE_AREA")
        
        player = context.game_state.players[context.source_player_id]
        
        # Get source zone
        if source_zone == "TRASH":
            zone = player.trash
        elif source_zone == "BANISH":
            zone = player.banished
        elif source_zone == "DECK":
            zone = player.main_deck
        else:
            return f"Unknown source zone: {source_zone}"
        
        # Find matching cards in zone
        matching_cards = []
        card_type = target_spec.get("card_type", "UNIT")
        filters = target_spec.get("filters", {})
        
        for card in zone:
            if card.type != card_type:
                continue
            
            # Apply filters
            if "level" in filters:
                level_check = filters["level"]
                operator = level_check.get("operator", "==")
                value = level_check.get("value", 0)
                
                if operator == "<=":
                    if not (card.level <= value):
                        continue
                elif operator == ">=":
                    if not (card.level >= value):
                        continue
                elif operator == "==":
                    if not (card.level == value):
                        continue
            
            matching_cards.append(card)
        
        if not matching_cards:
            return f"No valid targets in {source_zone}"
        
        # Select card (for now, take first match)
        # TODO: Integrate with agent selection
        selected_card = matching_cards[0]
        
        # Check if can pay cost
        if pay_cost:
            if player.get_active_resources() < selected_card.cost:
                return f"Cannot pay cost of {selected_card.cost}"
        
        # Remove from source zone
        zone.remove(selected_card)
        
        # Deploy to destination
        if destination == "BATTLE_AREA":
            from simulator.unit import UnitInstance
            unit = UnitInstance(
                card_data=selected_card,
                owner_id=context.source_player_id,
                turn_deployed=context.game_state.turn_number
            )
            player.battle_area.append(unit)
            
            return f"Deployed {selected_card.name} from {source_zone}"
        
        return f"Deployed {selected_card.name} from {source_zone} to {destination}"
    
    @staticmethod
    def _execute_grant_protection(context: EffectContext, action: Dict) -> str:
        """
        Execute GRANT_PROTECTION action - Grant damage/effect protection.
        
        Args:
            action: {
                "type": "GRANT_PROTECTION",
                "target": "SELF_SHIELDS" | target_spec,
                "protection_type": "PREVENT_DAMAGE" | "PREVENT_EFFECTS",
                "source_filter": filter_spec (optional),
                "duration": "THIS_TURN" | "THIS_BATTLE"
            }
        """
        target = action.get("target", "SELF")
        protection_type = action.get("protection_type", "PREVENT_DAMAGE")
        duration = action.get("duration", "THIS_TURN")
        source_filter = action.get("source_filter", {})
        
        # For now, we'll store this as a temporary effect
        # TODO: Implement protection tracking system
        
        player = context.game_state.players[context.source_player_id]
        
        # Store protection info (simplified)
        if not hasattr(player, 'active_protections'):
            player.active_protections = []
        
        protection = {
            'type': protection_type,
            'target': target,
            'duration': duration,
            'source_filter': source_filter,
            'applied_turn': context.game_state.turn_number
        }
        player.active_protections.append(protection)
        
        return f"Granted {protection_type} protection ({duration})"
    
    @staticmethod
    def _execute_add_to_shields(context: EffectContext, action: Dict) -> str:
        """
        Execute ADD_TO_SHIELDS action - Add cards from hand to shields.
        
        Args:
            action: {
                "type": "ADD_TO_SHIELDS",
                "source": "HAND" | "DECK",
                "count": number,
                "selection_method": "CHOOSE" | "RANDOM"
            }
        """
        source = action.get("source", "HAND")
        count = action.get("count", 1)
        selection_method = action.get("selection_method", "CHOOSE")
        
        player = context.game_state.players[context.source_player_id]
        
        # Get source
        if source == "HAND":
            source_zone = player.hand
        elif source == "DECK":
            source_zone = player.main_deck
        else:
            return f"Unknown source: {source}"
        
        if len(source_zone) < count:
            return f"Not enough cards in {source}"
        
        # Select cards
        # TODO: Integrate with agent selection
        # For now, take first cards
        cards_to_add = []
        for _ in range(count):
            if source_zone:
                card = source_zone.pop(0)
                cards_to_add.append(card)
        
        # Add to shields
        for card in cards_to_add:
            player.shield_area.append(card)
        
        return f"Added {len(cards_to_add)} card(s) from {source} to shields"
    
    @staticmethod
    def _execute_optional_action(context: EffectContext, action: Dict) -> str:
        """
        Execute OPTIONAL_ACTION - "You may" effects with follow-up.
        
        Args:
            action: {
                "type": "OPTIONAL_ACTION",
                "optional_actions": [actions],
                "next_if_success": [actions]
            }
        """
        optional_actions = action.get("optional_actions", [])
        next_if_success = action.get("next_if_success", [])
        
        # TODO: Integrate with agent decision
        # For now, always perform optional actions
        should_perform = True
        
        results = []
        
        if should_perform:
            # Execute optional actions
            for opt_action in optional_actions:
                result = ActionExecutor.execute(context, opt_action)
                results.append(result)
            
            # If successful, execute follow-up actions
            if next_if_success:
                for next_action in next_if_success:
                    result = ActionExecutor.execute(context, next_action)
                    results.append(result)
        
        return "; ".join(results) if results else "Optional action declined"
    
    @staticmethod
    def _execute_exile_cards(context: EffectContext, action: Dict) -> str:
        """
        Execute EXILE_CARDS action - Move cards from a zone to banished zone.
        
        Args:
            action: {
                "type": "EXILE_CARDS",
                "source_zone": "TRASH" | "HAND" | "DECK",
                "target": target_spec,
                "destination": "BANISH"
            }
        """
        source_zone = action.get("source_zone", "TRASH")
        target_spec = action.get("target", {})
        destination = action.get("destination", "BANISH")
        
        player = context.game_state.players[context.source_player_id]
        
        # Get source zone
        if source_zone == "TRASH":
            zone = player.trash
        elif source_zone == "HAND":
            zone = player.hand
        elif source_zone == "DECK":
            zone = player.main_deck
        else:
            return f"Unknown source zone: {source_zone}"
        
        # Get filters
        selector = target_spec.get("selector", "SELF_TRASH")
        card_type = target_spec.get("card_type", "UNIT")
        filters = target_spec.get("filters", {})
        count = target_spec.get("count", 1)
        
        # Find matching cards
        matching_cards = []
        for card in zone:
            if card.type != card_type:
                continue
            
            # Apply filters
            if "color" in filters:
                required_color = filters["color"]
                if card.color.lower() != required_color.lower():
                    continue
            
            if "level" in filters:
                level_check = filters["level"]
                operator = level_check.get("operator", "==")
                value = level_check.get("value", 0)
                
                if operator == "<=":
                    if not (card.level <= value):
                        continue
                elif operator == ">=":
                    if not (card.level >= value):
                        continue
                elif operator == "==":
                    if not (card.level == value):
                        continue
            
            matching_cards.append(card)
        
        if len(matching_cards) < count:
            return f"Not enough cards to exile (need {count}, found {len(matching_cards)})"
        
        # Select cards to exile (for now, take first N)
        # TODO: Integrate with agent selection
        cards_to_exile = matching_cards[:count]
        
        # Move to banished zone
        for card in cards_to_exile:
            zone.remove(card)
            player.banished.append(card)
        
        return f"Exiled {len(cards_to_exile)} card(s) from {source_zone}"
    
    @staticmethod
    def _execute_grant_attack_targeting(context: EffectContext, action: Dict) -> str:
        """
        Execute GRANT_ATTACK_TARGETING action - Grant special attack targeting ability.
        
        Args:
            action: {
                "type": "GRANT_ATTACK_TARGETING",
                "target": target_spec,
                "target_restrictions": {"level": {...}, "ap": {...}, "state": "ACTIVE"},
                "duration": "THIS_TURN" | "THIS_BATTLE",
                "description": str
            }
        """
        target_spec = action.get("target", {"selector": "SELF"})
        restrictions = action.get("target_restrictions", {})
        duration = action.get("duration", "THIS_TURN")
        
        # Resolve targets
        targets = TargetResolver.resolve_target(context, target_spec)
        
        if not targets:
            return "No valid targets for attack targeting grant"
        
        # Grant the ability to each target
        # Store as temporary effect on unit
        for unit in targets:
            if not hasattr(unit, 'attack_targeting_overrides'):
                unit.attack_targeting_overrides = []
            
            unit.attack_targeting_overrides.append({
                'restrictions': restrictions,
                'duration': duration,
                'applied_turn': context.game_state.turn_number
            })
        
        desc = f"Granted special attack targeting ({duration})"
        if restrictions:
            desc += f" with filters: {restrictions}"
        
        return desc



