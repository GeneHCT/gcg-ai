class Keywords:
    """
    Keyword Effects and Keywords for Gundam Card Game
    Based on Section 13 of the Official Game Rules
    """
    
    # ============================================================================
    # 13-1. Keyword Effects (Continuous/Triggered abilities on cards)
    # ============================================================================
    
    # Additive Keyword Effects: These sum their values when multiple copies are gained
    REPAIR = "repair"           # <Repair (amount)> - Recovers HP at end of turn
    BREACH = "breach"           # <Breach (amount)> - Damages shield when destroying enemy Unit
    SUPPORT = "support"         # <Support (amount)> - Gives AP bonus when activated
    
    # Boolean Keyword Effects: These are either ON or OFF (non-stackable)
    BLOCKER = "blocker"         # <Blocker> - Can intercept attacks
    FIRST_STRIKE = "first_strike"  # <First Strike> - Deals damage before enemy
    HIGH_MANEUVER = "high_maneuver"  # <High-Maneuver> - Cannot be blocked
    SUPPRESSION = "suppression"  # <Suppression> - Damages 2 shields simultaneously
    
    # ============================================================================
    # 13-2. Keywords (Timing/Trigger keywords for effect activation)
    # ============================================================================
    
    # Activated Effect Keywords (require player action)
    ACTIVATE_MAIN = "activate_main"      # 【Activate･Main】 - Activate during main phase
    ACTIVATE_ACTION = "activate_action"  # 【Activate･Action】 - Activate during action step
    
    # Command Card Keywords (timing of card play)
    MAIN = "main"               # 【Main】 - Play during main phase
    ACTION = "action"           # 【Action】 - Play during action step
    
    # Special Trigger Keywords
    BURST = "burst"             # 【Burst】 - Activates when shield is destroyed
    DEPLOY = "deploy"           # 【Deploy】 - Activates when card is deployed
    ATTACK = "attack"           # 【Attack】 - Activates when Unit declares attack
    DESTROYED = "destroyed"     # 【Destroyed】 - Activates when Unit/Base is destroyed
    
    # Pilot Pairing Keywords
    WHEN_PAIRED = "when_paired"  # 【When Paired】 - Activates when Pilot is paired
    DURING_PAIR = "during_pair"  # 【During Pair】 - Active while Pilot is paired
    WHEN_LINKED = "when_linked"  # 【When Linked】 - Activates when Link Pilot is paired
    DURING_LINK = "during_link"  # 【During Link】 - Active while Link Pilot is paired
    
    # Frequency Limiter
    ONCE_PER_TURN = "once_per_turn"  # 【Once per Turn】 - Can only activate once per turn
    
    # ============================================================================
    # Helper Methods
    # ============================================================================
    
    @staticmethod
    def add_keyword(unit, keyword_type, value=None):
        """
        Add a keyword effect to a unit.
        
        Args:
            unit: The unit to add the keyword to
            keyword_type: The type of keyword (use Keywords constants)
            value: The value for additive keywords (REPAIR, BREACH, SUPPORT)
        
        Rules:
            - Additive keywords (REPAIR, BREACH, SUPPORT) sum their values
            - Boolean keywords (BLOCKER, FIRST_STRIKE, etc.) are non-stackable
        """
        if keyword_type in [Keywords.REPAIR, Keywords.BREACH, Keywords.SUPPORT]:
            # Additive: Sum the values (13-1-1-2, 13-1-2-5, 13-1-3-2)
            unit.keywords[keyword_type] = unit.keywords.get(keyword_type, 0) + (value or 0)
        else:
            # Boolean: Set to True (13-1-4-2, 13-1-5-3, 13-1-6-2, 13-1-7-2)
            unit.keywords[keyword_type] = True
    
    @staticmethod
    def remove_keyword(unit, keyword_type):
        """
        Remove a keyword effect from a unit.
        
        Args:
            unit: The unit to remove the keyword from
            keyword_type: The type of keyword to remove
        """
        if keyword_type in unit.keywords:
            del unit.keywords[keyword_type]
    
    @staticmethod
    def has_keyword(unit, keyword_type):
        """
        Check if a unit has a specific keyword.
        
        Args:
            unit: The unit to check
            keyword_type: The type of keyword to check for
            
        Returns:
            bool: True if unit has the keyword, False otherwise
        """
        return keyword_type in unit.keywords and unit.keywords[keyword_type]
    
    @staticmethod
    def get_keyword_value(unit, keyword_type):
        """
        Get the value of a keyword for a unit.
        
        Args:
            unit: The unit to check
            keyword_type: The type of keyword to get value for
            
        Returns:
            int/bool: The value for additive keywords, True/False for boolean keywords
        """
        return unit.keywords.get(keyword_type, 0 if keyword_type in [Keywords.REPAIR, Keywords.BREACH, Keywords.SUPPORT] else False)