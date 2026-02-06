class BattleState:
    attacker: UnitInstance
    target: Union[UnitInstance, PlayerTarget]
    current_step: str # ATTACK, BLOCK, ACTION, DAMAGE, END
    priority_player: int # The player currently allowed to act
    consecutive_passes: int = 0 # Track for ending the Action Step
    
    
    def run_action_step(state):
        # Rule: Standby (Defending) player gets priority first
        state.priority_player = state.opponent_id 
        state.consecutive_passes = 0
        
        while state.consecutive_passes < 2:
            # Get legal actions for the player with priority
            # Only Command [Action] cards or [Activate: Action] abilities
            legal_actions = get_legal_combat_actions(state, state.priority_player)
            
            # RL Agent (or Heuristic) chooses an action
            action = state.players[state.priority_player].choose_action(legal_actions)
            
            if action.is_pass():
                state.consecutive_passes += 1
            else:
                # Rule: Effects resolve immediately (No Stack)
                execute_effect(state, action)
                state.consecutive_passes = 0 # Reset pass counter
                
            # Pass priority to the other player
            state.priority_player = 1 - state.priority_player

        # Once two passes occur, move to Damage Step
        transition_to_damage_step(state)
    
    def resolve_damage(state):
        attacker = state.attacker
        target = state.target
        
        # 1. First Strike Check
        if attacker.has_keyword("First Strike") and not target.has_keyword("First Strike"):
            apply_damage(attacker, target)
            if target.is_destroyed():
                return # Combat ends, attacker takes no return damage
                
        # 2. Simultaneous Damage
        apply_damage(attacker, target)
        apply_damage(target, attacker)
        
        # 3. Shield Destruction & [Burst] Timing
        if isinstance(target, PlayerTarget):
            shield_card = state.opponent.shield_area.pop_front()
            if shield_card.has_burst():
                # Interrupt damage step to resolve Burst
                # The owner of the shield chooses to activate
                if state.opponent.decide_burst(shield_card):
                    execute_burst_effect(state, shield_card)
            
            state.opponent.trash.append(shield_card)