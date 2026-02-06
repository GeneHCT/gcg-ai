# This is the core loop. It must be asynchronous-ready because of [Burst] effects and [Action] responses.
class MainPhaseManager:
    def get_legal_actions(state):
        """
        Returns a list of legal action objects for the current state.
        CRITICAL for RL Action Masking.
        """
        actions = []
        
        # Rule 7-5-1: No actions if abilities are pending
        if state.pending_abilities:
            return [ResolvePendingAbility(state.pending_abilities[0])]
            
        # 1. PLAY CARDS (Rule 7-5-2)
        for card in state.active_hand:
            if can_pay_cost(state, card):
                if card.type == "Unit" and len(state.battle_area) < 6:
                    actions.append(PlayUnitAction(card))
                elif card.type == "Pilot" and any_unpaired_units(state):
                    actions.append(PairPilotAction(card, target_unit))
                # ... repeat for Base and Command
                
        # 2. ATTACK (Rule 7-5-4)
        for unit in state.battle_area:
            if unit.is_active and unit.can_attack: # can_attack handles "turn deployed" vs "Link"
                # Target: Opposing Player (Shields)
                actions.append(AttackAction(attacker=unit, target="PLAYER"))
                # Target: Rested Enemy Units
                for enemy in state.opponent_battle_area:
                    if enemy.is_rested:
                        actions.append(AttackAction(attacker=unit, target=enemy))
                        
        # 3. ACTIVATE MAIN (Rule 7-5-3)
        # Scan cards for [Activate: Main] keywords...

        # 4. END PHASE (Rule 7-5-5)
        actions.append(EndMainPhaseAction())
        
        return actions

    def apply_action(state, action):
        """
        The Transition Function: State(t) + Action -> State(t+1)
        """
        if isinstance(action, PlayUnitAction):
            pay_cost(state, action.card)
            unit = deploy_unit(state, action.card)
            # CHECK FOR [DEPLOY] TRIGGERS
            if unit.has_ability("DEPLOY"):
                state.pending_abilities.append(unit.get_ability("DEPLOY"))
                
        elif isinstance(action, AttackAction):
            # Attack is NOT one step. It triggers an "Action Step".
            # This is where RL gets hard. You enter a sub-state.
            return start_battle_sequence(state, action)
            
        return state