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
    
    def check_block_legality(attacker, potential_blocker):
        # Rule 13-1-6-1: High-Maneuver vs Blocker
        if attacker.has_keyword(Keywords.HIGH_MANEUVER):
            return False # Blocker cannot be activated
        return potential_blocker.has_keyword(Keywords.BLOCKER) and potential_blocker.is_active

    def calculate_damage_sequence(attacker, defender):
        # Rule 13-1-5: First Strike Priority
        if attacker.has_keyword(Keywords.FIRST_STRIKE) and not defender.has_keyword(Keywords.FIRST_STRIKE):
            apply_damage(attacker, defender)
            if defender.is_destroyed:
                return # Defender dies before it can counter-attack
        
        # Simultaneous damage (Standard)
        apply_damage(attacker, defender)
        apply_damage(defender, attacker)
    
    def resolve_shield_damage(attacker, defender_player):
        # Rule 13-1-7: Suppression (Dual-Shield Hit)
        if attacker.has_keyword(Keywords.SUPPRESSION):
            shields = defender_player.shield_area[:2] # Get first two
            process_bursts_simultaneously(shields) 
        else:
            # Standard: Breach or Normal
            target_shield = get_top_shield_or_base(defender_player)
            apply_damage_to_shield(attacker, target_shield)

    def on_unit_destroyed_in_battle(attacker, destroyed_unit):
        # FAQ Rule: Resolve Breach BEFORE [Destroyed] (Active Player Priority)
        if attacker.has_keyword(Keywords.BREACH):
            amount = attacker.keywords[Keywords.BREACH]
            deal_direct_shield_damage(destroyed_unit.owner, amount)
        
        # Now trigger the [Destroyed] ability
        if destroyed_unit.has_ability("DESTROYED"):
            trigger_ability(destroyed_unit.get_ability("DESTROYED"))