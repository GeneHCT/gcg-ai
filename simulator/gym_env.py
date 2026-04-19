"""
Gymnasium Environment for Gundam Card Game

Provides a Gym-compatible interface for RL training.
Requires: pip install gymnasium

Usage:
    from simulator.gym_env import GCGEnv, make_gcg_env

    env = make_gcg_env(seed=42)
    obs, info = env.reset()
    action_mask = info["action_mask"]
    action = 0  # Index into legal_actions
    obs, reward, terminated, truncated, info = env.step(action)
"""
import numpy as np
from typing import Optional, Tuple, Any, Dict, List

from simulator.game_manager import (
    GameManager, GameSetup, Phase, GameResult,
    TurnManager, WinConditionChecker, ObservationGenerator
)
from simulator.random_agent import (
    LegalActionGenerator, ActionExecutor, ActionType, Action,
    RandomAgent, PassAgent
)
from simulator.action_space import (
    get_legal_actions, get_action_mask, decode_action,
    get_action_space_size
)
from simulator.battlemanager import BattleManager
from simulator.action_step_manager import ActionStepManager


def _run_until_agent_decision(game_state, agent_player_id: int, opponent_agent,
                              max_iterations: int = 200) -> Tuple[Any, bool]:
    """
    Run game loop until agent (agent_player_id) must act or game ends.
    Uses opponent_agent for opponent decisions.

    Returns:
        (game_state, is_terminal)
    """
    from simulator.effect_integration import EffectIntegration
    if hasattr(EffectIntegration, 'patch_turn_manager'):
        EffectIntegration.patch_turn_manager()

    for _ in range(max_iterations):
        if game_state.is_terminal():
            return game_state, True

        decision_player = LegalActionGenerator._get_decision_player(game_state)
        if decision_player == agent_player_id:
            return game_state, False

        legal_actions = LegalActionGenerator.get_legal_actions(game_state)
        chosen = opponent_agent.choose_action(game_state, legal_actions)

        if chosen.action_type in [ActionType.ATTACK_PLAYER, ActionType.ATTACK_UNIT]:
            target = "PLAYER" if chosen.action_type == ActionType.ATTACK_PLAYER else "UNIT"
            target_unit = chosen.target if target == "UNIT" else None
            game_state, _ = BattleManager.run_complete_battle(
                game_state, chosen.unit, target, target_unit,
                agents=[opponent_agent, opponent_agent]
            )
        else:
            game_state, _ = ActionExecutor.execute_action(game_state, chosen)

        if chosen.action_type == ActionType.END_PHASE:
            game_state = TurnManager.end_phase(game_state)
            game_state = ActionStepManager.enter_action_step(game_state, is_battle=False)
            for _ in range(20):
                if game_state.is_terminal():
                    return game_state, True
                priority = game_state.action_step_priority_player
                legal = ActionStepManager.get_action_step_legal_actions(game_state)
                chosen = opponent_agent.choose_action(game_state, legal)
                if chosen.action_type == ActionType.PASS:
                    game_state, continues = ActionStepManager.handle_action_step_action(
                        game_state, chosen
                    )
                    if not continues:
                        break
                else:
                    game_state, _ = ActionExecutor.execute_action(game_state, chosen)
                    game_state, _ = ActionStepManager.handle_action_step_action(
                        game_state, chosen
                    )
            game_state = ActionStepManager.exit_action_step(game_state)
            KeywordInterpreter = __import__('simulator.keyword_interpreter',
                                           fromlist=['KeywordInterpreter']).KeywordInterpreter
            KeywordInterpreter.resolve_all_repairs(
                game_state.players[game_state.turn_player].battle_area
            )
            player = game_state.players[game_state.turn_player]
            if len(player.hand) > 10:
                num_discard = len(player.hand) - 10
                to_discard = opponent_agent.choose_cards_to_discard(player.hand, num_discard)
                player.discard_to_limit(to_discard)
            game_state.turn_player = 1 - game_state.turn_player
            game_state.turn_number += 1
            game_state = TurnManager.start_phase(game_state)
            game_state = TurnManager.draw_phase(game_state)
            if game_state.is_terminal():
                return game_state, True
            game_state = TurnManager.resource_phase(game_state)
            game_state.current_phase = Phase.MAIN

    return game_state, game_state.is_terminal()


class GCGEnv:
    """
    Gymnasium-style environment for Gundam Card Game.

    The agent controls player 0. Opponent (player 1) uses a random agent.
    Action: Integer index into legal_actions (0 to n_legal-1).
    """

    def __init__(self, deck_p0: Optional[List[Dict]] = None,
                 deck_p1: Optional[List[Dict]] = None,
                 resource_p0: Optional[List[Dict]] = None,
                 resource_p1: Optional[List[Dict]] = None,
                 seed: Optional[int] = None,
                 max_turns: int = 50,
                 max_action_space: int = 512):
        self.max_turns = max_turns
        self.max_action_space = max_action_space

        if deck_p0 is None or deck_p1 is None:
            from simulator.deck_loader import DeckLoader
            deck_p0, resource_p0, _ = DeckLoader.load_deck_with_resource("decks/the-o.txt")
            deck_p1, resource_p1, _ = DeckLoader.load_deck_with_resource("decks/tekkadan.txt")

        self._deck_p0 = deck_p0
        self._deck_p1 = deck_p1
        self._resource_p0 = resource_p0
        self._resource_p1 = resource_p1

        self.manager = GameManager(seed=seed)
        self.opponent_agent = RandomAgent(player_id=1, seed=(seed + 1) if seed else None)

    def reset(self, seed: Optional[int] = None,
              options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        if seed is not None:
            self.manager.seed = seed
        self.manager.setup_game(
            self._deck_p0, self._deck_p1,
            self._resource_p0, self._resource_p1
        )

        game_state = self.manager.game_state
        if game_state.turn_player == 1:
            game_state, _ = _run_until_agent_decision(
                game_state, 0, self.opponent_agent
            )
        self.manager.game_state = game_state

        obs = ObservationGenerator.generate_flat_observation(game_state, 0)
        mask, legal_actions = get_action_mask(game_state, self.max_action_space, 0)
        info = {
            "legal_actions": legal_actions,
            "action_mask": mask,
            "turn_number": game_state.turn_number,
        }
        return obs.astype(np.float32), info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        game_state = self.manager.game_state
        if game_state.is_terminal():
            obs = ObservationGenerator.generate_flat_observation(game_state, 0)
            info = {"legal_actions": [], "action_mask": np.zeros(self.max_action_space),
                    "reward": 0.0}
            return obs.astype(np.float32), 0.0, True, False, info

        mask, legal_actions = get_action_mask(game_state, self.max_action_space, 0)
        if action < 0 or action >= len(legal_actions):
            action = 0
        chosen = decode_action(legal_actions, action)
        if chosen is None:
            chosen = legal_actions[0] if legal_actions else Action(ActionType.PASS)

        if chosen.action_type in [ActionType.ATTACK_PLAYER, ActionType.ATTACK_UNIT]:
            target = "PLAYER" if chosen.action_type == ActionType.ATTACK_PLAYER else "UNIT"
            target_unit = chosen.target if target == "UNIT" else None
            pass_agent = PassAgent(player_id=0)
            game_state, _ = BattleManager.run_complete_battle(
                game_state, chosen.unit, target, target_unit,
                agents=[pass_agent, self.opponent_agent]
            )
        else:
            game_state, _ = ActionExecutor.execute_action(game_state, chosen)

        self.manager.game_state = game_state

        reward = 0.0
        terminated = game_state.is_terminal()
        if terminated:
            reward = 1.0 if game_state.winner == 0 else -1.0

        truncated = (game_state.turn_number >= self.max_turns) and not terminated

        if not terminated and not truncated:
            if chosen.action_type in [ActionType.END_PHASE, ActionType.PASS]:
                game_state = TurnManager.end_phase(game_state)
                game_state = ActionStepManager.enter_action_step(game_state, is_battle=False)
                for _ in range(20):
                    if game_state.is_terminal():
                        break
                    legal = ActionStepManager.get_action_step_legal_actions(game_state)
                    chosen = self.opponent_agent.choose_action(game_state, legal)
                    if chosen.action_type == ActionType.PASS:
                        game_state, continues = ActionStepManager.handle_action_step_action(
                            game_state, chosen
                        )
                        if not continues:
                            break
                    else:
                        game_state, _ = ActionExecutor.execute_action(game_state, chosen)
                        game_state, _ = ActionStepManager.handle_action_step_action(
                            game_state, chosen
                        )
                game_state = ActionStepManager.exit_action_step(game_state)
                KeywordInterpreter = __import__('simulator.keyword_interpreter',
                                               fromlist=['KeywordInterpreter']).KeywordInterpreter
                KeywordInterpreter.resolve_all_repairs(
                    game_state.players[game_state.turn_player].battle_area
                )
                player = game_state.players[game_state.turn_player]
                if len(player.hand) > 10:
                    num_discard = len(player.hand) - 10
                    to_discard = self.opponent_agent.choose_cards_to_discard(
                        player.hand, num_discard
                    )
                    player.discard_to_limit(to_discard)
                game_state.turn_player = 1 - game_state.turn_player
                game_state.turn_number += 1
                game_state = TurnManager.start_phase(game_state)
                game_state = TurnManager.draw_phase(game_state)
                if not game_state.is_terminal():
                    game_state = TurnManager.resource_phase(game_state)
                game_state.current_phase = Phase.MAIN
            self.manager.game_state = game_state
            if not game_state.is_terminal() and game_state.turn_player == 1:
                game_state, _ = _run_until_agent_decision(
                    game_state, 0, self.opponent_agent
                )
            self.manager.game_state = game_state

        obs = ObservationGenerator.generate_flat_observation(
            self.manager.game_state, 0
        )
        mask, legal_actions = get_action_mask(
            self.manager.game_state, self.max_action_space, 0
        )
        info = {
            "legal_actions": legal_actions,
            "action_mask": mask,
            "turn_number": self.manager.game_state.turn_number,
            "reward": reward,
        }
        return obs.astype(np.float32), reward, terminated, truncated, info

    @property
    def observation_space(self):
        try:
            import gymnasium as gym
            obs, _ = self.reset()
            return gym.spaces.Box(
                low=-np.inf, high=np.inf,
                shape=obs.shape, dtype=np.float32
            )
        except ImportError:
            return None

    @property
    def action_space(self):
        try:
            import gymnasium as gym
            return gym.spaces.Discrete(self.max_action_space)
        except ImportError:
            return None


def make_gcg_env(deck_p0: Optional[str] = None,
                 deck_p1: Optional[str] = None,
                 seed: Optional[int] = None,
                 **kwargs) -> GCGEnv:
    """Factory to create GCG environment."""
    from simulator.deck_loader import DeckLoader
    if deck_p0 and deck_p1:
        d0, r0, _ = DeckLoader.load_deck_with_resource(deck_p0)
        d1, r1, _ = DeckLoader.load_deck_with_resource(deck_p1)
    else:
        d0, r0, _ = DeckLoader.load_deck_with_resource("decks/the-o.txt")
        d1, r1, _ = DeckLoader.load_deck_with_resource("decks/tekkadan.txt")
    return GCGEnv(deck_p0=d0, deck_p1=d1, resource_p0=r0, resource_p1=r1,
                  seed=seed, **kwargs)
