"""
Action Space for RL Policy Masking

Provides encode/decode of game actions to integer indices for use with
Gym/PettingZoo and policy networks. Supports variable-size legal action sets
with optional fixed-size masking.
"""
import numpy as np
from typing import List, Optional, Tuple, Any

from simulator.random_agent import Action, ActionType, LegalActionGenerator
from simulator.game_manager import GameState


def get_legal_actions(game_state: GameState, player_id: Optional[int] = None) -> List[Action]:
    """Get legal actions for the current decision point. Wrapper for LegalActionGenerator."""
    return LegalActionGenerator.get_legal_actions(game_state, player_id)


def encode_action(legal_actions: List[Action], action: Action) -> int:
    """
    Encode an Action to its index in the legal_actions list.
    
    Args:
        legal_actions: List of legal actions for current state
        action: The action to encode
        
    Returns:
        Index in [0, len(legal_actions)-1], or -1 if action not in list
    """
    for i, a in enumerate(legal_actions):
        if _actions_equal(a, action):
            return i
    return -1


def decode_action(legal_actions: List[Action], action_idx: int) -> Optional[Action]:
    """
    Decode an integer index to an Action.
    
    Args:
        legal_actions: List of legal actions for current state
        action_idx: Integer index in [0, len(legal_actions)-1]
        
    Returns:
        The Action at that index, or None if invalid
    """
    if 0 <= action_idx < len(legal_actions):
        return legal_actions[action_idx]
    return None


def get_action_mask(game_state: GameState, max_actions: int = 512,
                    player_id: Optional[int] = None) -> Tuple[np.ndarray, List[Action]]:
    """
    Get action mask for RL policy (1 = legal, 0 = illegal).
    
    Args:
        game_state: Current game state
        max_actions: Maximum action space size (mask will be this long)
        player_id: Optional player ID for decision context
        
    Returns:
        Tuple of (mask, legal_actions). Mask is np.ndarray of shape (max_actions,)
        with 1.0 for legal action indices and 0.0 for illegal/padding.
        legal_actions may have fewer than max_actions elements.
    """
    legal_actions = get_legal_actions(game_state, player_id)
    n_legal = len(legal_actions)
    
    mask = np.zeros(max_actions, dtype=np.float32)
    mask[:min(n_legal, max_actions)] = 1.0
    
    # If we have more legal actions than max_actions, all are "legal" (overflow)
    if n_legal > max_actions:
        mask[:] = 1.0
    
    return mask, legal_actions


def _actions_equal(a: Action, b: Action) -> bool:
    """Check if two actions are equal (for encoding lookup)."""
    if a.action_type != b.action_type:
        return False
    if (a.card is None) != (b.card is None):
        return False
    if a.card is not None and b.card is not None and a.card.id != b.card.id:
        return False
    if (a.unit is None) != (b.unit is None):
        return False
    if a.unit is not None and b.unit is not None:
        if a.unit.card_data.id != b.unit.card_data.id:
            return False
    if (a.target is None) != (b.target is None):
        return False
    if a.target is not None and b.target is not None:
        if a.target.card_data.id != b.target.card_data.id:
            return False
    if (a.cards_to_discard is None) != (b.cards_to_discard is None):
        return False
    if a.cards_to_discard is not None and b.cards_to_discard is not None:
        a_ids = {c.id for c in a.cards_to_discard}
        b_ids = {c.id for c in b.cards_to_discard}
        if a_ids != b_ids:
            return False
    return True


def get_action_space_size() -> int:
    """
    Get the default maximum action space size for the environment.
    Used by Gym wrapper for action_space definition.
    """
    return 512
