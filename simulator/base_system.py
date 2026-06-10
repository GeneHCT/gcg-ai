"""
Base System Implementation for Gundam Card Game

Implements:
- BASE card deployment to shield area
- BASE HP tracking
- Damage preferentially to bases
- Base replacement (old base to trash)
- Burst triggers on BASE cards
"""
from typing import Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from simulator.unit import Card
    from simulator.game_manager import GameState, Player


@dataclass
class BaseInstance:
    """
    Instance of a BASE card deployed in the base section.
    Similar to UnitInstance but for BASE cards.
    """
    card_data: 'Card'
    owner_id: int
    is_rested: bool = False
    current_hp: int = 0
    turn_deployed: int = 0
    
    # Keywords for bases (some bases have keywords)
    keywords: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize HP from card data"""
        if self.current_hp == 0:
            self.current_hp = self.card_data.hp
    
    @property
    def ap(self) -> int:
        """Get current AP"""
        return self.card_data.ap
    
    @property
    def hp(self) -> int:
        """Get max HP"""
        return self.card_data.hp
    
    @property
    def is_destroyed(self) -> bool:
        """Check if base is destroyed"""
        return self.current_hp <= 0
    
    def take_damage(self, amount: int) -> int:
        """
        Apply damage to base.
        Returns actual damage dealt.
        """
        actual_damage = min(amount, self.current_hp)
        self.current_hp -= actual_damage
        return actual_damage
    
    def rest(self):
        """Rest this base"""
        self.is_rested = True
    
    def set_active(self):
        """Set this base to active"""
        self.is_rested = False
    
    def has_keyword(self, keyword: str) -> bool:
        """Check if base has a specific keyword"""
        return keyword in self.keywords and self.keywords[keyword]
    
    def get_keyword_value(self, keyword: str):
        """Get keyword value"""
        return self.keywords.get(keyword, 0)


class BaseManager:
    """
    Manages BASE card operations and rules.
    """
    
    @staticmethod
    def can_deploy_base(player: 'Player', base_card: 'Card') -> bool:
        """
        Check if a base can be deployed.
        
        Rules:
        - Must be a BASE type card
        - Player can have at most one base deployed
        - If one exists, it will be replaced
        
        Args:
            player: Player attempting to deploy
            base_card: BASE card to deploy
            
        Returns:
            True if deployment is allowed
        """
        return base_card.type == "BASE"
    
    @staticmethod
    def deploy_base(game_state: 'GameState', player_id: int, 
                   base_card: 'Card', trigger_effects: bool = True) -> Optional[BaseInstance]:
        """
        Deploy a BASE card to the player's base section.
        
        Rules from 4-6-3:
        - You may have up to one Base placed face up in your base section
        - If a base already exists, it goes to trash (NOT destroyed, no effects)
        
        Args:
            game_state: Current game state
            player_id: Player deploying the base
            base_card: BASE card to deploy
            trigger_effects: Whether to trigger Deploy effects
            
        Returns:
            BaseInstance if deployed, None otherwise
        """
        player = game_state.players[player_id]
        
        # Verify it's a BASE card
        if base_card.type != "BASE":
            return None
        
        # Remove card from hand
        if base_card in player.hand:
            player.hand.remove(base_card)
        
        # If a base already exists, send it to trash (NOT destroyed)
        if player.bases:
            old_base = player.bases[0]
            player.bases.clear()
            # Move real BASE cards to trash. The starter EX Base is a token-like
            # object and has no card_data to move.
            old_base_card = getattr(old_base, "card_data", None)
            if old_base_card is not None:
                player.trash.append(old_base_card)
                print(f"  Old base {old_base_card.name} sent to trash (replaced)")
            else:
                print("  EX Base removed (replaced)")
        
        # Create new base instance
        base_instance = BaseInstance(
            card_data=base_card,
            owner_id=player_id,
            turn_deployed=game_state.turn_number
        )
        
        # Add to base section
        player.bases.append(base_instance)
        
        print(f"  Deployed BASE: {base_card.name} (AP={base_instance.ap}, HP={base_instance.hp})")
        
        # Trigger Deploy effects if requested
        if trigger_effects:
            try:
                from simulator.effect_integration import EffectIntegration
                game_state = EffectIntegration.on_base_deployed(game_state, base_instance)
            except Exception as e:
                print(f"  [BASE Deploy Effect Error] {e}")
        
        return base_instance
    
    @staticmethod
    def deal_damage_to_shields(game_state: 'GameState', player_id: int, 
                              damage: int) -> tuple:
        """
        Deal damage to a player's shields/bases.
        
        Rules from 3-5-3:
        - While a Base is present, damage dealt to the shield area is 
          preferentially dealt to that base
        
        Args:
            game_state: Current game state
            player_id: Player receiving damage
            damage: Amount of damage
            
        Returns:
            Tuple of (shields_destroyed, base_destroyed, burst_cards)
        """
        player = game_state.players[player_id]
        shields_destroyed = 0
        base_destroyed = False
        burst_cards = []
        
        # Check if player has a base
        active_base = next((base for base in player.bases if getattr(base, "current_hp", 0) > 0), None)
        if active_base is not None:
            base = active_base
            hp_before = base.current_hp
            
            # Deal damage to base first
            actual_damage = base.take_damage(damage)
            base_name = getattr(getattr(base, "card_data", None), "name", getattr(base, "name", "EX Base"))
            print(f"    Base {base_name} took {actual_damage} damage ({hp_before} -> {base.current_hp} HP)")
            
            # Check if base is destroyed
            if getattr(base, "current_hp", 0) <= 0:
                print(f"    [BASE DESTROYED] {base_name}")
                base_destroyed = True
                
                # Remove base from play and send to trash
                player.bases.remove(base)
                base_card = getattr(base, "card_data", None)
                if base_card is not None:
                    player.trash.append(base_card)
                
                # Trigger BASE destroyed effects
                try:
                    from simulator.effect_integration import EffectIntegration
                    game_state = EffectIntegration.on_base_destroyed(game_state, base)
                except Exception as e:
                    print(f"    [BASE Destroyed Effect Error] {e}")
        else:
            # Damage to a Shield destroys only the first Shield, regardless of excess damage.
            if damage > 0 and player.shield_area:
                shield = player.shield_area.pop(0)
                shields_destroyed += 1
                
                # Check for Burst
                if shield.effect and any("【Burst】" in str(e) for e in shield.effect):
                    burst_cards.append(shield)
                    print(f"    Burst card revealed: {shield.name}")
                else:
                    player.trash.append(shield)
        
        return shields_destroyed, base_destroyed, burst_cards
    
    @staticmethod
    def activate_burst(game_state: 'GameState', player_id: int, 
                      burst_card: 'Card'):
        """
        Activate a Burst effect from a card.
        
        Args:
            game_state: Current game state
            player_id: Player whose burst is activating
            burst_card: Card with Burst effect
        """
        player = game_state.players[player_id]
        
        print(f"    [BURST] Activating {burst_card.name}")
        
        # Trigger Burst effect through effect system
        try:
            from simulator.effect_integration import EffectIntegration
            game_state = EffectIntegration.on_burst_triggered(
                game_state, burst_card, player_id
            )
        except Exception as e:
            print(f"    [BURST Effect Error] {e}")
        
        # After burst resolves, card goes to trash
        player.trash.append(burst_card)
    
    @staticmethod
    def reset_bases(game_state: 'GameState', player_id: int):
        """
        Reset (set active) all bases at start of turn.
        
        Args:
            game_state: Current game state
            player_id: Player whose bases to reset
        """
        player = game_state.players[player_id]
        
        for base in player.bases:
            if base.is_rested:
                base.set_active()
