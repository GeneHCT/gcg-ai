# Since units normally cannot attack the turn they are played, your UnitInstance needs a hidden flag that the Pilot can override.

class UnitInstance:
    card_data: Card
    is_rested: bool = False
    turn_deployed: int
    paired_pilot: Pilot = None
    
    @property
    def can_attack(self):
        # Base rule: Can't attack turn deployed
        if self.turn_deployed == current_turn:
            # Exception: Link Condition (Rule 3. Card Types)
            if self.is_linked:
                return True
            return False
        return True

    @property
    def is_linked(self):
        if not self.paired_pilot: return False
        # Check card-specific link requirements (e.g., "Amuro Ray" or "Trait: Zeon")
        return check_link_requirements(self.card_data, self.paired_pilot)