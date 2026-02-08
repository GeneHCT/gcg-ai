"""
Global Game Manager for Gundam Card Game

Wraps the entire game into a full match simulation suitable for Reinforcement Learning.
Provides deterministic gameplay with seeded randomness for reproducible debugging.

Features:
- Complete game setup with decks and initial state
- Full turn sequence (Start, Draw, Resource, Main, End)
- Win condition checking
- Observation generation for RL agents
- Deterministic and pickleable state
"""
import random
import copy
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from simulator.unit import UnitInstance, Card, PilotInstance
from simulator.keyword_interpreter import KeywordInterpreter, PlayerState, BattlePhase


class Phase(Enum):
    """Game phases"""
    START = "start"
    DRAW = "draw"
    RESOURCE = "resource"
    MAIN = "main"
    END = "end"


class GameResult(Enum):
    """Game result states"""
    ONGOING = "ongoing"
    PLAYER_0_WIN = "player_0_win"
    PLAYER_1_WIN = "player_1_win"
    DRAW = "draw"


@dataclass
class EXBase:
    """EX Base card (deployed to Shield Area at game start)"""
    name: str = "EX Base"
    ap: int = 0
    hp: int = 3
    current_hp: int = 3
    owner_id: int = 0
    is_rested: bool = False
    
    def __init__(self, owner_id: int = 0):
        """Initialize EX Base"""
        self.owner_id = owner_id
        self.is_rested = False
        self.current_hp = 3
    
    def take_damage(self, amount: int) -> bool:
        """
        Apply damage to base. Returns True if destroyed.
        """
        self.current_hp -= amount
        return self.current_hp <= 0
    
    def rest(self):
        """Rest this base"""
        self.is_rested = True
    
    def set_active(self):
        """Set this base to active"""
        self.is_rested = False
    
    def to_feature_vector(self) -> np.ndarray:
        """Convert to feature vector for RL"""
        return np.array([
            float(self.ap),
            float(self.current_hp),
            float(self.hp),
        ], dtype=np.float32)


@dataclass
class Player:
    """
    Complete player state with all game areas.
    """
    player_id: int
    
    # Decks
    main_deck: List[Card] = field(default_factory=list)
    resource_deck: List[Card] = field(default_factory=list)
    
    # Game areas
    hand: List[Card] = field(default_factory=list)
    battle_area: List[UnitInstance] = field(default_factory=list)
    resource_area: List[Card] = field(default_factory=list)
    shield_area: List[Card] = field(default_factory=list)
    bases: List = field(default_factory=list)  # Can be EXBase or BaseInstance
    trash: List[Card] = field(default_factory=list)
    banished: List[Card] = field(default_factory=list)
    
    # Special resources
    ex_resources: int = 0
    
    # Resource state tracking (for rested/active)
    _rested_resource_indices: set = field(default_factory=set)
    
    # State tracking
    cards_drawn_this_turn: int = 0
    units_deployed_this_turn: int = 0
    
    def get_active_resources(self, game_state: Optional['GameState'] = None) -> int:
        """
        Get count of active (untapped) resources.
        
        Args:
            game_state: Game state (required for accurate count with ResourceManager)
            
        Returns:
            Number of active resources
        """
        if game_state is None:
            # Fallback: assume all resources are active
            return len(self.resource_area)
        
        from simulator.resource_manager import ResourceManager
        return ResourceManager.count_active_resources(game_state, self.player_id)
    
    def get_total_resources(self) -> int:
        """Get total resource count (for Lv condition)"""
        return len(self.resource_area) + self.ex_resources
    
    def has_shields(self) -> bool:
        """Check if player has any shields or bases"""
        return len(self.shield_area) > 0 or len(self.bases) > 0
    
    def has_bases(self) -> bool:
        """Check if player has any bases"""
        return len(self.bases) > 0 and any(base.current_hp > 0 for base in self.bases)
    
    def draw_card(self) -> Optional[Card]:
        """Draw a card from main deck. Returns None if deck is empty."""
        if not self.main_deck:
            return None
        card = self.main_deck.pop(0)
        self.hand.append(card)
        self.cards_drawn_this_turn += 1
        return card
    
    def add_resource(self) -> bool:
        """Move top card from resource deck to resource area. Returns False if deck empty."""
        if not self.resource_deck:
            return False
        card = self.resource_deck.pop(0)
        self.resource_area.append(card)
        return True
    
    def discard_to_limit(self, cards_to_discard: List[Card]):
        """Discard specific cards from hand"""
        for card in cards_to_discard:
            if card in self.hand:
                self.hand.remove(card)
                self.trash.append(card)


@dataclass
class GameState:
    """
    Complete game state for the Gundam Card Game.
    This is the main state object that RL agents will observe and interact with.
    """
    # Players
    players: Dict[int, Player] = field(default_factory=dict)
    
    # Turn tracking
    turn_number: int = 0
    turn_player: int = 0  # 0 or 1
    current_phase: Phase = Phase.START
    
    # Battle tracking
    in_battle: bool = False
    battle_attacker: Optional[UnitInstance] = None
    battle_defender: Optional[UnitInstance] = None
    battle_phase: Optional[BattlePhase] = None
    
    # Action step tracking (NEW)
    in_action_step: bool = False  # True during action steps
    action_step_priority_player: int = 0  # Player with current priority
    action_step_consecutive_passes: int = 0  # Track passes for ending
    
    # Game state
    game_result: GameResult = GameResult.ONGOING
    winner: Optional[int] = None
    
    # Random state (for deterministic gameplay)
    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random)
    
    def __post_init__(self):
        """Initialize RNG if seed is provided"""
        if self.seed is not None:
            self.rng.seed(self.seed)
    
    def get_opponent_id(self, player_id: int) -> int:
        """Get opponent player ID"""
        return 1 - player_id
    
    def is_terminal(self) -> bool:
        """Check if game is over"""
        return self.game_result != GameResult.ONGOING
    
    def deep_copy(self) -> 'GameState':
        """Create a deep copy of the game state for simulation"""
        return copy.deepcopy(self)


class GameSetup:
    """
    Handles game initialization and setup.
    """
    
    @staticmethod
    def create_game(deck_list_p0: List[Dict], deck_list_p1: List[Dict],
                   resource_deck_p0: List[Dict], resource_deck_p1: List[Dict],
                   seed: Optional[int] = None) -> GameState:
        """
        Initialize a complete game with two players.
        
        Args:
            deck_list_p0: Player 0's main deck (50 cards as dicts)
            deck_list_p1: Player 1's main deck (50 cards as dicts)
            resource_deck_p0: Player 0's resource deck (10 cards)
            resource_deck_p1: Player 1's resource deck (10 cards)
            seed: Random seed for deterministic gameplay
            
        Returns:
            Initialized GameState ready to play
        """
        game_state = GameState(seed=seed)
        
        # Create players
        game_state.players[0] = Player(player_id=0)
        game_state.players[1] = Player(player_id=1)
        
        # Load decks
        game_state.players[0].main_deck = GameSetup._convert_deck_list_to_cards(deck_list_p0)
        game_state.players[1].main_deck = GameSetup._convert_deck_list_to_cards(deck_list_p1)
        game_state.players[0].resource_deck = GameSetup._convert_deck_list_to_cards(resource_deck_p0)
        game_state.players[1].resource_deck = GameSetup._convert_deck_list_to_cards(resource_deck_p1)
        
        # Shuffle decks (deterministic if seed provided)
        game_state.rng.shuffle(game_state.players[0].main_deck)
        game_state.rng.shuffle(game_state.players[1].main_deck)
        game_state.rng.shuffle(game_state.players[0].resource_deck)
        game_state.rng.shuffle(game_state.players[1].resource_deck)
        
        # Initial setup for both players
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            
            # Draw 5 cards
            for _ in range(5):
                player.draw_card()
            
            # Place 6 shields from top of main deck
            for _ in range(6):
                if player.main_deck:
                    shield = player.main_deck.pop(0)
                    player.shield_area.append(shield)
            
            # Deploy EX Base (0 AP / 3 HP)
            ex_base = EXBase(owner_id=player_id)
            player.bases.append(ex_base)
        
        # Player 2 (ID=1) starts with 1 EX Resource token
        game_state.players[1].ex_resources = 1
        
        # Player 0 goes first
        game_state.turn_player = 0
        game_state.turn_number = 1
        
        return game_state
    
    @staticmethod
    def _convert_deck_list_to_cards(deck_list: List[Dict]) -> List[Card]:
        """Convert list of card dicts to Card objects"""
        cards = []
        for card_dict in deck_list:
            card = Card(
                name=card_dict.get('Name', ''),
                id=card_dict.get('ID', ''),
                type=card_dict.get('Type', ''),
                color=card_dict.get('Color', ''),
                level=card_dict.get('Level', 0),
                cost=card_dict.get('Cost', 0),
                ap=card_dict.get('Ap', 0),
                hp=card_dict.get('Hp', 0),
                traits=card_dict.get('Traits', []),
                zones=card_dict.get('Zones', []),
                link=card_dict.get('Link', []),
                effect=card_dict.get('Effect', [])
            )
            cards.append(card)
        return cards
    
    @staticmethod
    def create_game_from_card_ids(card_ids_p0: List[str], card_ids_p1: List[str],
                                  resource_ids_p0: List[str], resource_ids_p1: List[str],
                                  card_database_path: str = "card_database/all_cards.json",
                                  seed: Optional[int] = None) -> GameState:
        """
        Create game from card IDs (loads from database).
        
        Args:
            card_ids_p0: List of card IDs for player 0's deck
            card_ids_p1: List of card IDs for player 1's deck
            resource_ids_p0: List of card IDs for player 0's resource deck
            resource_ids_p1: List of card IDs for player 1's resource deck
            card_database_path: Path to card database JSON
            seed: Random seed
            
        Returns:
            Initialized GameState
        """
        import json
        
        # Load card database
        with open(card_database_path, 'r', encoding='utf-8') as f:
            all_cards = json.load(f)
        
        card_dict = {card['ID']: card for card in all_cards}
        
        # Build deck lists
        deck_p0 = [card_dict[cid] for cid in card_ids_p0 if cid in card_dict]
        deck_p1 = [card_dict[cid] for cid in card_ids_p1 if cid in card_dict]
        res_p0 = [card_dict[cid] for cid in resource_ids_p0 if cid in card_dict]
        res_p1 = [card_dict[cid] for cid in resource_ids_p1 if cid in card_dict]
        
        return GameSetup.create_game(deck_p0, deck_p1, res_p0, res_p1, seed)


class TurnManager:
    """
    Manages the turn sequence and phase transitions.
    """
    
    @staticmethod
    def run_phase_sequence(game_state: GameState, 
                          action_callback=None) -> GameState:
        """
        Execute a complete turn sequence.
        
        Args:
            game_state: Current game state
            action_callback: Function to handle Main Phase actions
                           Signature: callback(game_state) -> game_state
                           
        Returns:
            Updated game state after turn completion
        """
        player = game_state.players[game_state.turn_player]
        
        # 1. START PHASE
        game_state = TurnManager.start_phase(game_state)
        
        # 2. DRAW PHASE
        game_state = TurnManager.draw_phase(game_state)
        if game_state.is_terminal():
            return game_state
        
        # 3. RESOURCE PHASE
        game_state = TurnManager.resource_phase(game_state)
        
        # 4. MAIN PHASE (controlled by RL agent)
        game_state.current_phase = Phase.MAIN
        if action_callback:
            game_state = action_callback(game_state)
        
        # 5. END PHASE
        game_state = TurnManager.end_phase(game_state)
        
        # Switch to next player
        game_state.turn_player = game_state.get_opponent_id(game_state.turn_player)
        game_state.turn_number += 1
        
        return game_state
    
    @staticmethod
    def start_phase(game_state: GameState) -> GameState:
        """
        Start Phase: Reset all rested cards to active.
        """
        game_state.current_phase = Phase.START
        player = game_state.players[game_state.turn_player]
        
        # Reset all units, resources, and bases to active using RestManager
        from simulator.rest_mechanics import RestManager
        RestManager.reset_all_cards(game_state, game_state.turn_player)
        
        # Reset all resources to active using ResourceManager
        from simulator.resource_manager import ResourceManager
        ResourceManager.reset_all_resources(game_state, game_state.turn_player)
        
        # Reset per-turn counters
        player.cards_drawn_this_turn = 0
        player.units_deployed_this_turn = 0
        
        return game_state
    
    @staticmethod
    def draw_phase(game_state: GameState) -> GameState:
        """
        Draw Phase: Draw 1 card from Main Deck.
        Trigger loss condition if deck is empty.
        """
        game_state.current_phase = Phase.DRAW
        player = game_state.players[game_state.turn_player]
        
        # Check if deck is empty (loss condition)
        if not player.main_deck:
            game_state.game_result = (GameResult.PLAYER_1_WIN 
                                     if game_state.turn_player == 0 
                                     else GameResult.PLAYER_0_WIN)
            game_state.winner = game_state.get_opponent_id(game_state.turn_player)
            return game_state
        
        # Draw 1 card
        player.draw_card()
        
        return game_state
    
    @staticmethod
    def resource_phase(game_state: GameState) -> GameState:
        """
        Resource Phase: Move top of Resource Deck to Resource Area.
        """
        game_state.current_phase = Phase.RESOURCE
        player = game_state.players[game_state.turn_player]
        
        # Add resource (if resource deck not empty)
        player.add_resource()
        
        return game_state
    
    @staticmethod
    def end_phase(game_state: GameState) -> GameState:
        """
        End Phase:
        - Trigger <Repair> keywords
        - Enforce hand size limit (10 cards)
        """
        game_state.current_phase = Phase.END
        player = game_state.players[game_state.turn_player]
        
        # 1. Resolve Repair for all units
        KeywordInterpreter.resolve_all_repairs(player.battle_area)
        
        # 2. Enforce hand size limit (10 cards)
        # Note: This requires agent decision if hand > 10
        # For now, we just flag it - the action loop should handle discards
        # In a full implementation, this would be part of the action selection
        
        return game_state


class WinConditionChecker:
    """
    Checks win conditions and determines game outcome.
    """
    
    @staticmethod
    def check_win_conditions(game_state: GameState) -> GameState:
        """
        Check all win conditions and update game state.
        
        Win Conditions:
        1. Player takes damage while having 0 Shields and 0 Bases
        2. Player's Main Deck is empty during their Draw Phase
        
        Args:
            game_state: Current game state
            
        Returns:
            Updated game state with result and winner
        """
        # Check both players
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            
            # Condition 1: No shields and no bases (already checked when taking damage)
            if not player.has_shields():
                # Game over - opponent wins
                game_state.game_result = (GameResult.PLAYER_1_WIN 
                                         if player_id == 0 
                                         else GameResult.PLAYER_0_WIN)
                game_state.winner = game_state.get_opponent_id(player_id)
                return game_state
            
            # Condition 2: Deck empty (checked in Draw Phase)
            # This is handled in TurnManager.draw_phase()
        
        return game_state
    
    @staticmethod
    def apply_damage_to_shields(game_state: GameState, player_id: int, 
                               attacker: UnitInstance) -> GameState:
        """
        Apply damage to player's shields/bases.
        Checks win condition after damage.
        
        Args:
            game_state: Current game state
            player_id: ID of player taking damage
            attacker: Unit dealing damage
            
        Returns:
            Updated game state
        """
        player = game_state.players[player_id]
        
        # Use KeywordInterpreter for shield damage
        destroyed_shields = KeywordInterpreter.resolve_shield_damage(
            attacker, player, game_state
        )
        
        # Process Burst triggers
        KeywordInterpreter.process_burst_triggers(
            destroyed_shields, player, game_state
        )
        
        # Check if player has lost (no more shields/bases)
        if not player.has_shields():
            game_state.game_result = (GameResult.PLAYER_1_WIN 
                                     if player_id == 0 
                                     else GameResult.PLAYER_0_WIN)
            game_state.winner = game_state.get_opponent_id(player_id)
        
        return game_state


class ObservationGenerator:
    """
    Generates observations (feature vectors) for RL agents.
    Flattens the entire game state into a structured dictionary/vector.
    """
    
    @staticmethod
    def generate_observation(game_state: GameState, 
                           perspective_player: int) -> Dict[str, np.ndarray]:
        """
        Generate complete observation for RL agent.
        
        The observation is from the perspective of perspective_player,
        so their information comes first.
        
        Args:
            game_state: Current game state
            perspective_player: Player ID whose perspective to use (0 or 1)
            
        Returns:
            Dictionary of feature arrays
        """
        player = game_state.players[perspective_player]
        opponent = game_state.players[game_state.get_opponent_id(perspective_player)]
        
        obs = {}
        
        # ====================================================================
        # GLOBAL STATE (10 features)
        # ====================================================================
        obs['global'] = np.array([
            float(game_state.turn_number),
            float(game_state.turn_player == perspective_player),  # Is my turn?
            float(game_state.current_phase.value == Phase.MAIN.value),
            float(game_state.in_battle),
            float(game_state.game_result != GameResult.ONGOING),
            float(len(player.main_deck)),
            float(len(opponent.main_deck)),
            float(len(player.resource_deck)),
            float(len(opponent.resource_deck)),
            float(player.ex_resources),
        ], dtype=np.float32)
        
        # ====================================================================
        # MY STATE
        # ====================================================================
        
        # Hand (max 15 cards, 10 features per card)
        obs['my_hand'] = ObservationGenerator._encode_card_list(
            player.hand, max_cards=15, features_per_card=10
        )
        
        # Battle Area (max 6 units, 16 features per unit)
        obs['my_battle_area'] = ObservationGenerator._encode_unit_list(
            player.battle_area, max_units=6
        )
        
        # Resources (count and features)
        obs['my_resources'] = np.array([
            float(player.get_total_resources()),
            float(player.get_active_resources(game_state)),
            float(player.ex_resources),
            float(len(player.resource_area)),
        ], dtype=np.float32)
        
        # Shields and Bases
        obs['my_shields'] = np.array([
            float(len(player.shield_area)),
            float(len(player.bases)),
            float(sum(base.current_hp for base in player.bases)),
        ], dtype=np.float32)
        
        # Trash count (for card effects that care)
        obs['my_trash'] = np.array([
            float(len(player.trash)),
        ], dtype=np.float32)
        
        # ====================================================================
        # OPPONENT STATE (partially hidden in real game, but visible for training)
        # ====================================================================
        
        # Opponent hand (only count, not contents - hidden information)
        obs['opp_hand'] = np.array([
            float(len(opponent.hand)),
        ], dtype=np.float32)
        
        # Opponent battle area (visible)
        obs['opp_battle_area'] = ObservationGenerator._encode_unit_list(
            opponent.battle_area, max_units=6
        )
        
        # Opponent resources
        obs['opp_resources'] = np.array([
            float(opponent.get_total_resources()),
            float(opponent.get_active_resources(game_state)),
            float(opponent.ex_resources),
        ], dtype=np.float32)
        
        # Opponent shields and bases
        obs['opp_shields'] = np.array([
            float(len(opponent.shield_area)),
            float(len(opponent.bases)),
            float(sum(base.current_hp for base in opponent.bases)),
        ], dtype=np.float32)
        
        # Opponent trash count
        obs['opp_trash'] = np.array([
            float(len(opponent.trash)),
        ], dtype=np.float32)
        
        return obs
    
    @staticmethod
    def generate_flat_observation(game_state: GameState, 
                                  perspective_player: int) -> np.ndarray:
        """
        Generate a single flattened observation vector.
        
        Args:
            game_state: Current game state
            perspective_player: Player ID whose perspective to use
            
        Returns:
            Flattened numpy array of all features
        """
        obs_dict = ObservationGenerator.generate_observation(game_state, perspective_player)
        
        # Concatenate all arrays
        arrays = [obs_dict[key] for key in sorted(obs_dict.keys())]
        flat_obs = np.concatenate(arrays)
        
        return flat_obs
    
    @staticmethod
    def _encode_card_list(cards: List[Card], max_cards: int, 
                         features_per_card: int) -> np.ndarray:
        """
        Encode a list of cards as a fixed-size array.
        
        Features per card:
        - Level, Cost, AP, HP, Color (one-hot: 5), Type (one-hot: 5)
        """
        features = []
        
        for i in range(max_cards):
            if i < len(cards):
                card = cards[i]
                card_features = [
                    float(card.level),
                    float(card.cost),
                    float(card.ap),
                    float(card.hp),
                    # Color encoding (simplified)
                    float(card.color == 'Blue'),
                    float(card.color == 'Red'),
                    float(card.color == 'Green'),
                    float(card.color == 'Yellow'),
                    float(card.color == 'White'),
                    float(card.type == 'UNIT'),
                ]
            else:
                # Padding
                card_features = [0.0] * features_per_card
            
            features.extend(card_features)
        
        return np.array(features, dtype=np.float32)
    
    @staticmethod
    def _encode_unit_list(units: List[UnitInstance], max_units: int = 6) -> np.ndarray:
        """
        Encode a list of units as a fixed-size array.
        Uses the unit.to_feature_vector() method (16 features per unit).
        """
        features = []
        
        for i in range(max_units):
            if i < len(units):
                unit_features = units[i].to_feature_vector()
            else:
                # Padding
                unit_features = np.zeros(16, dtype=np.float32)
            
            features.append(unit_features)
        
        # Flatten: max_units × 16 features
        return np.concatenate(features)
    
    @staticmethod
    def get_observation_space_size(include_hidden_info: bool = True) -> int:
        """
        Calculate the total size of the observation space.
        
        Args:
            include_hidden_info: If True, includes hidden info (for training)
            
        Returns:
            Total number of features in observation
        """
        size = 0
        size += 10   # global
        size += 15 * 10  # my_hand
        size += 6 * 16   # my_battle_area
        size += 4    # my_resources
        size += 3    # my_shields
        size += 1    # my_trash
        size += 1    # opp_hand (just count)
        size += 6 * 16   # opp_battle_area
        size += 3    # opp_resources
        size += 3    # opp_shields
        size += 1    # opp_trash
        
        return size


class GameManager:
    """
    Main game manager that orchestrates everything.
    Provides high-level interface for RL training.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize game manager.
        
        Args:
            seed: Random seed for deterministic gameplay
        """
        self.seed = seed
        self.game_state: Optional[GameState] = None
    
    def setup_game(self, deck_p0: List[Dict], deck_p1: List[Dict],
                  resource_p0: List[Dict], resource_p1: List[Dict]) -> GameState:
        """
        Set up a new game.
        
        Args:
            deck_p0: Player 0's main deck
            deck_p1: Player 1's main deck
            resource_p0: Player 0's resource deck
            resource_p1: Player 1's resource deck
            
        Returns:
            Initial game state
        """
        self.game_state = GameSetup.create_game(
            deck_p0, deck_p1, resource_p0, resource_p1, self.seed
        )
        return self.game_state
    
    def get_observation(self, player_id: int) -> Dict[str, np.ndarray]:
        """
        Get observation for specified player.
        
        Args:
            player_id: Player to get observation for
            
        Returns:
            Observation dictionary
        """
        if self.game_state is None:
            raise ValueError("Game not set up. Call setup_game() first.")
        
        return ObservationGenerator.generate_observation(self.game_state, player_id)
    
    def check_win_conditions(self) -> bool:
        """
        Check if game is over.
        
        Returns:
            True if game is terminal
        """
        if self.game_state is None:
            return False
        
        self.game_state = WinConditionChecker.check_win_conditions(self.game_state)
        return self.game_state.is_terminal()
    
    def get_winner(self) -> Optional[int]:
        """
        Get winner if game is over.
        
        Returns:
            Winner player ID, or None if game ongoing
        """
        if self.game_state is None or not self.game_state.is_terminal():
            return None
        
        return self.game_state.winner
    
    def save_state(self) -> GameState:
        """
        Save current game state (for rollbacks/simulation).
        
        Returns:
            Deep copy of current state
        """
        if self.game_state is None:
            raise ValueError("Game not set up.")
        
        return self.game_state.deep_copy()
    
    def restore_state(self, saved_state: GameState):
        """
        Restore a previously saved state.
        
        Args:
            saved_state: State to restore
        """
        self.game_state = saved_state.deep_copy()
    
    def is_deterministic(self) -> bool:
        """Check if game is running with deterministic seed"""
        return self.seed is not None
