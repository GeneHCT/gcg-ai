"""
Unit class for Gundam Card Game simulator.
Stores keywords in a dictionary and provides methods for keyword management.
"""
from typing import Dict, Any, Optional
import numpy as np
from dataclasses import dataclass, field


@dataclass
class Card:
    """Card data from card_database"""
    name: str
    id: str
    type: str
    color: str
    level: int
    cost: int
    ap: int = 0
    hp: int = 0
    traits: list = field(default_factory=list)
    zones: list = field(default_factory=list)
    link: list = field(default_factory=list)
    effect: list = field(default_factory=list)


@dataclass
class UnitInstance:
    """
    Unit instance in play with keyword tracking.
    Keywords are stored in a dictionary for easy access and modification.
    """
    card_data: Card
    owner_id: int  # Player 0 or 1
    is_rested: bool = False
    turn_deployed: int = 0
    current_hp: int = 0
    paired_pilot: Optional['PilotInstance'] = None
    
    # Keyword dictionary: stores both boolean and additive keywords
    # Boolean keywords: "blocker" -> True/False
    # Additive keywords: "repair" -> int value
    keywords: Dict[str, Any] = field(default_factory=dict)
    
    # Track keyword sources for debugging/undo
    keyword_sources: Dict[str, list] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize HP and parse base keywords from card"""
        if self.current_hp == 0:
            self.current_hp = self.card_data.hp
            
    @property
    def ap(self) -> int:
        """Get current AP (can be modified by Support, effects, etc.)"""
        base_ap = self.card_data.ap
        # Add support bonus if applicable
        support_bonus = self.keywords.get("support", 0)
        return base_ap + support_bonus
    
    @property
    def hp(self) -> int:
        """Get max HP"""
        return self.card_data.hp
    
    @property
    def is_destroyed(self) -> bool:
        """Check if unit is destroyed"""
        return self.current_hp <= 0
    
    @property
    def can_attack(self) -> bool:
        """Check if unit can attack (considering Link mechanic)"""
        if self.is_rested:
            return False
        # Base rule: Can't attack turn deployed unless linked
        # This will be checked by the game state
        return True
    
    @property
    def is_linked(self) -> bool:
        """
        Check if unit is linked with appropriate pilot.
        
        A unit is LINKED when:
        1. It has a paired pilot, AND
        2. The pilot satisfies the unit's link conditions
        
        Linking is separate from pairing - any pilot can pair,
        but only pilots meeting link conditions create a Link Unit.
        """
        if not self.paired_pilot:
            return False
        
        # Use LinkManager to check if pilot satisfies link conditions
        from simulator.link_system import LinkManager
        return LinkManager.check_link_condition(self.card_data, self.paired_pilot.card_data)
    
    def has_keyword(self, keyword: str) -> bool:
        """Check if unit has a specific keyword"""
        if keyword not in self.keywords:
            return False
        value = self.keywords[keyword]
        # Boolean keywords: check if True
        if isinstance(value, bool):
            return value
        # Additive keywords: check if > 0
        return value > 0
    
    def get_keyword_value(self, keyword: str) -> Any:
        """Get the value of a keyword"""
        return self.keywords.get(keyword, 0)
    
    def add_keyword(self, keyword: str, value: Any = True, source: str = ""):
        """
        Add a keyword to the unit.
        Handles additive stacking for Repair, Breach, Support.
        
        Args:
            keyword: The keyword name
            value: The value (int for additive, bool for others)
            source: Description of the source (for tracking)
        """
        # Additive keywords sum their values
        if keyword in ["repair", "breach", "support"]:
            self.keywords[keyword] = self.keywords.get(keyword, 0) + value
        else:
            # Boolean keywords are just set to True
            self.keywords[keyword] = True
        
        # Track source
        if keyword not in self.keyword_sources:
            self.keyword_sources[keyword] = []
        self.keyword_sources[keyword].append(source)
    
    def remove_keyword(self, keyword: str, value: Any = None):
        """
        Remove a keyword from the unit.
        For additive keywords, subtracts the value.
        
        Args:
            keyword: The keyword name
            value: The value to subtract (for additive keywords)
        """
        if keyword in ["repair", "breach", "support"] and value is not None:
            current = self.keywords.get(keyword, 0)
            new_value = max(0, current - value)
            if new_value == 0:
                del self.keywords[keyword]
            else:
                self.keywords[keyword] = new_value
        else:
            if keyword in self.keywords:
                del self.keywords[keyword]
    
    def clear_temporary_keywords(self):
        """Clear keywords that last only for this turn/battle"""
        # This should be called at appropriate timing windows
        # Implementation depends on game flow
        pass
    
    def to_feature_vector(self) -> np.ndarray:
        """
        Convert unit state to feature vector for RL agent.
        
        Returns:
            NumPy array with unit features including all keywords
        """
        features = [
            # Basic stats
            float(self.card_data.ap),
            float(self.current_hp),
            float(self.hp),
            float(self.card_data.level),
            float(self.card_data.cost),
            
            # Status
            float(self.is_rested),
            float(self.is_destroyed),
            float(self.paired_pilot is not None),
            float(self.is_linked),
            
            # Additive keywords
            float(self.keywords.get("repair", 0)),
            float(self.keywords.get("breach", 0)),
            float(self.keywords.get("support", 0)),
            
            # Boolean keywords
            float(self.has_keyword("blocker")),
            float(self.has_keyword("first_strike")),
            float(self.has_keyword("high_maneuver")),
            float(self.has_keyword("suppression")),
        ]
        
        return np.array(features, dtype=np.float32)


@dataclass
class PilotInstance:
    """Pilot card instance"""
    card_data: Card
    owner_id: int
    paired_unit: Optional[UnitInstance] = None
    
    def to_feature_vector(self) -> np.ndarray:
        """Convert pilot state to feature vector"""
        features = [
            float(self.paired_unit is not None),
            float(self.card_data.level),
            float(self.card_data.cost),
        ]
        return np.array(features, dtype=np.float32)
