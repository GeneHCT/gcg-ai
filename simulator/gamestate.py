# Your agent needs a structured vector. Should implement this using pydantic or dataclasses.

class GameState:
    turn_player: int  # 0 or 1
    phase: Phase      # Enum: START, DRAW, RESOURCE, MAIN, END
    
    # Per-player areas
    hands: List[List[Card]]
    battle_areas: List[List[UnitInstance]] # Max 6
    resource_areas: List[List[ResourceInstance]] # Active/Rested status
    shield_areas: List[List[ShieldInstance]] # Includes Bases
    trash: List[List[Card]]
    banished: List[List[Card]]
    
    # The "Stack" for Rule 7-5-1
    pending_abilities: List[Effect]