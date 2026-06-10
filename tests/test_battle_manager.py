"""
Test BattleManager Implementation

Tests the complete 5-step battle sequence according to game rules 8-1 through 8-6
"""
import sys
from simulator.battlemanager import BattleManager, BattleState, BattleStep
from simulator.game_manager import GameManager, GameState
from simulator.unit import UnitInstance, Card
from simulator.random_agent import RandomAgent, Action, ActionType


def create_test_card_dict(name: str, ap: int = 3, hp: int = 3, level: int = 1, has_blocker: bool = False):
    """Create a test card as a dictionary (for deck loading)"""
    effects = []
    if has_blocker:
        effects.append("<Blocker>")
    
    return {
        'Name': name,
        'ID': f"TEST-{name.upper().replace(' ', '_')}",
        'Type': "UNIT",
        'Color': "Blue",
        'Level': level,
        'Cost': level,
        'Ap': ap,
        'Hp': hp,
        'Traits': ["Test"],
        'Zones': ["Space"],
        'Link': [],
        'Effect': effects
    }


def create_test_card(name: str, ap: int = 3, hp: int = 3, level: int = 1, has_blocker: bool = False):
    """Create a test card"""
    effects = []
    if has_blocker:
        effects.append("<Blocker>")
    
    return Card(
        name=name,
        id=f"TEST-{name.upper().replace(' ', '_')}",
        type="UNIT",
        color="Blue",
        level=level,
        cost=level,
        ap=ap,
        hp=hp,
        traits=["Test"],
        zones=["Space"],
        link=[],
        effect=effects
    )


def create_test_unit(card: Card, owner_id: int, turn_deployed: int = 0) -> UnitInstance:
    """Create a test unit instance"""
    unit = UnitInstance(
        card_data=card,
        owner_id=owner_id,
        is_rested=False,
        turn_deployed=turn_deployed,
        current_hp=card.hp
    )
    return unit


def test_battle_steps():
    """Test that all 5 battle steps execute correctly"""
    print("=" * 60)
    print("TEST 1: Complete 5-Step Battle Sequence")
    print("=" * 60)
    
    # Create minimal game state
    manager = GameManager(seed=42)
    
    # Create test decks (as dictionaries)
    test_deck = [create_test_card_dict(f"Unit {i}") for i in range(50)]
    resource_deck = [create_test_card_dict(f"Resource {i}") for i in range(10)]
    
    game_state = manager.setup_game(test_deck, test_deck, resource_deck, resource_deck)
    
    # Create attacker and defender
    attacker_card = create_test_card("Attacker", ap=5, hp=5)
    defender_card = create_test_card("Defender", ap=3, hp=3)
    
    attacker = create_test_unit(attacker_card, owner_id=0, turn_deployed=0)
    defender = create_test_unit(defender_card, owner_id=1, turn_deployed=0)
    
    # Add to battle areas
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(defender)
    
    # Create agents
    agent_0 = RandomAgent(0, seed=42)
    agent_1 = RandomAgent(1, seed=43)
    agents = [agent_0, agent_1]
    
    # Run complete battle
    print("\nRunning unit vs unit battle...")
    game_state, battle_logs = BattleManager.run_complete_battle(
        game_state=game_state,
        attacker=attacker,
        target="UNIT",
        target_unit=defender,
        agents=agents
    )
    
    # Print logs
    for log in battle_logs:
        print(f"  {log}")
    
    # Verify battle steps occurred - check for key phrases in logs
    logs_text = "\n".join(battle_logs)
    assert "BATTLE START" in logs_text, "Battle should start"
    assert "Attack Step" in logs_text, "Attack step should execute"
    assert "Block Step" in logs_text, "Block step should execute"
    assert "Action Step" in logs_text, "Action step should execute"
    assert "Damage Step" in logs_text, "Damage step should execute"
    assert "Battle End Step" in logs_text, "Battle end step should execute"
    assert "BATTLE END" in logs_text, "Battle should end"
    
    print("\n✓ TEST 1 PASSED: All 5 battle steps executed correctly")
    return True


def test_blocker_mechanic():
    """Test <Blocker> keyword functionality"""
    print("\n" + "=" * 60)
    print("TEST 2: Blocker Mechanic")
    print("=" * 60)
    
    # Create game state
    manager = GameManager(seed=42)
    test_deck = [create_test_card_dict(f"Unit {i}") for i in range(50)]
    resource_deck = [create_test_card_dict(f"Resource {i}") for i in range(10)]
    game_state = manager.setup_game(test_deck, test_deck, resource_deck, resource_deck)
    
    # Create attacker and units
    attacker_card = create_test_card("Attacker", ap=5, hp=5)
    target_card = create_test_card("Target", ap=3, hp=3)
    blocker_card = create_test_card("Blocker", ap=4, hp=4, has_blocker=True)
    
    attacker = create_test_unit(attacker_card, owner_id=0, turn_deployed=0)
    target = create_test_unit(target_card, owner_id=1, turn_deployed=0)
    blocker = create_test_unit(blocker_card, owner_id=1, turn_deployed=0)
    
    # Parse blocker keyword
    blocker.add_keyword("blocker", True, "card_text")
    
    # Add to battle areas
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(target)
    game_state.players[1].battle_area.append(blocker)
    
    # Set turn player (attacker is player 0)
    game_state.turn_player = 0
    
    # Start battle
    print("\nStarting battle: Attacker → Target (with Blocker available)")
    game_state, battle_state = BattleManager.start_battle(
        game_state, attacker, "UNIT", target
    )
    
    # Execute attack step
    game_state, log = BattleManager.execute_attack_step(game_state, battle_state)
    print(f"  {log}")
    
    # Get block moves
    legal_moves = BattleManager.get_block_legal_actions(game_state, battle_state)
    print(f"\n  Legal block moves: {len(legal_moves)}")
    
    # Check that blocker can be activated
    block_moves = [move for move in legal_moves if move.action_type == ActionType.BLOCK]
    assert len(block_moves) > 0, "Should have at least one block move available"
    
    # Find the blocker move
    blocker_move = next((move for move in block_moves if move.unit == blocker), None)
    assert blocker_move is not None, "Blocker unit should be in legal moves"
    
    print(f"  ✓ Blocker unit found in legal moves")
    
    # Execute block
    game_state, log = BattleManager.execute_block(game_state, battle_state, blocker)
    print(f"  {log}")
    
    # Verify target changed and blocker rested
    assert battle_state.current_target == blocker, "Attack target should change to blocker"
    assert blocker.is_rested, "Blocker should be rested when blocking"
    print(f"  ✓ Attack target changed from {target_card.name} to {blocker_card.name}")
    
    print("\n✓ TEST 2 PASSED: Blocker mechanic works correctly")
    return True


def test_blocker_can_block_player_attack():
    """Test that Blocker can block attacks declared against the player."""
    game_state = GameState()
    from simulator.game_manager import Player
    game_state.players = {0: Player(0), 1: Player(1)}
    game_state.turn_player = 0

    attacker = create_test_unit(create_test_card("Attacker", ap=3, hp=3), owner_id=0, turn_deployed=0)
    blocker = create_test_unit(create_test_card("Blocker", ap=2, hp=4, has_blocker=True), owner_id=1, turn_deployed=0)
    blocker.add_keyword("blocker", True, "card_text")
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(blocker)

    game_state, battle_state = BattleManager.start_battle(game_state, attacker, "PLAYER")
    battle_state.current_step = BattleStep.BLOCK
    game_state.battle_state = battle_state

    legal_actions = BattleManager.get_block_legal_actions(game_state, battle_state)

    assert any(action.action_type == ActionType.BLOCK and action.unit is blocker for action in legal_actions)


def test_blocked_player_attack_resolves_against_blocker():
    """Test that a blocked player attack deals unit combat damage to the blocker."""
    class BlockAgent:
        def choose_action(self, game_state, legal_actions):
            return next((action for action in legal_actions if action.action_type == ActionType.BLOCK), legal_actions[0])

    class PassAgent:
        def choose_action(self, game_state, legal_actions):
            return next((action for action in legal_actions if action.action_type == ActionType.PASS), legal_actions[0])

    game_state = GameState()
    from simulator.game_manager import Player
    game_state.players = {0: Player(0), 1: Player(1)}
    game_state.turn_player = 0

    attacker = create_test_unit(create_test_card("Attacker", ap=3, hp=3), owner_id=0, turn_deployed=0)
    blocker = create_test_unit(create_test_card("Blocker", ap=2, hp=4, has_blocker=True), owner_id=1, turn_deployed=0)
    blocker.add_keyword("blocker", True, "card_text")
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(blocker)
    game_state.players[1].shield_area = [create_test_card("Shield")]

    game_state, logs = BattleManager.run_complete_battle(
        game_state,
        attacker,
        target="PLAYER",
        target_unit=None,
        agents=[PassAgent(), BlockAgent()],
    )

    assert any("Blocker blocks" in log for log in logs)
    assert blocker.is_rested
    assert blocker.current_hp == 1
    assert len(game_state.players[1].shield_area) == 1


def test_breach_damages_base_instead_of_multiple_shields():
    """Breach X deals X damage to the first shield-area card, preferring the base."""
    from simulator.game_manager import EXBase, Player

    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}

    attacker = create_test_unit(create_test_card("Rick Dom", ap=4, hp=4), owner_id=0)
    attacker.add_keyword("breach", 4, "card_text")
    defender = create_test_unit(create_test_card("Aile Strike Gundam", ap=4, hp=4), owner_id=1)
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(defender)
    game_state.players[1].bases.append(EXBase(owner_id=1))
    game_state.players[1].shield_area = [
        create_test_card("Shield 1"),
        create_test_card("Shield 2"),
    ]

    game_state, logs = BattleManager._resolve_unit_attack(game_state, attacker, defender)

    assert "  BREACH 4: Base HP 3 → 0" in logs
    assert not game_state.players[1].bases
    assert len(game_state.players[1].shield_area) == 2


def test_breach_destroys_only_top_shield_without_base():
    """Breach X destroys only the first Shield when no deployed base exists."""
    from simulator.game_manager import Player

    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}

    attacker = create_test_unit(create_test_card("Rick Dom", ap=4, hp=4), owner_id=0)
    attacker.add_keyword("breach", 4, "card_text")
    defender = create_test_unit(create_test_card("Aile Strike Gundam", ap=4, hp=4), owner_id=1)
    shield_1 = create_test_card("Shield 1")
    shield_2 = create_test_card("Shield 2")
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(defender)
    game_state.players[1].shield_area = [shield_1, shield_2]

    game_state, logs = BattleManager._resolve_unit_attack(game_state, attacker, defender)

    assert "  BREACH 4: Destroyed shield Shield 1" in logs
    assert game_state.players[1].shield_area == [shield_2]
    assert shield_1 in game_state.players[1].trash


def test_player_attack():
    """Test attacking player shields and bases"""
    print("\n" + "=" * 60)
    print("TEST 3: Player Attack (Shields)")
    print("=" * 60)
    
    # Create game state
    manager = GameManager(seed=42)
    test_deck = [create_test_card_dict(f"Unit {i}") for i in range(50)]
    resource_deck = [create_test_card_dict(f"Resource {i}") for i in range(10)]
    game_state = manager.setup_game(test_deck, test_deck, resource_deck, resource_deck)
    
    # Create attacker
    attacker_card = create_test_card("Attacker", ap=5, hp=5)
    attacker = create_test_unit(attacker_card, owner_id=0, turn_deployed=0)
    
    game_state.players[0].battle_area.append(attacker)
    game_state.turn_player = 0
    
    # Check shields before
    shields_before = len(game_state.players[1].shield_area)
    print(f"\n  Opponent shields before: {shields_before}")
    
    # Create agents
    agent_0 = RandomAgent(0, seed=42)
    agent_1 = RandomAgent(1, seed=43)
    agents = [agent_0, agent_1]
    
    # Run complete battle
    print(f"  Attacker AP: {attacker.ap}")
    game_state, battle_logs = BattleManager.run_complete_battle(
        game_state=game_state,
        attacker=attacker,
        target="PLAYER",
        target_unit=None,
        agents=agents
    )
    
    # Print logs
    for log in battle_logs:
        print(f"  {log}")
    
    # Check shields after
    shields_after = len(game_state.players[1].shield_area)
    bases_after = len([b for b in game_state.players[1].bases if b.current_hp > 0])
    print(f"\n  Opponent shields after: {shields_after}")
    print(f"  Opponent bases after: {bases_after}")
    
    # Verify shield or base was destroyed
    # Per rules, if there's a base, it gets attacked first
    assert shields_after < shields_before or bases_after == 0, "Shield or base should be destroyed"
    print(f"  ✓ Attack succeeded - shields: {shields_before}→{shields_after}, bases destroyed: {1 - bases_after}")
    
    print("\n✓ TEST 3 PASSED: Player attack works correctly")
    return True


def test_first_strike():
    """Test <First Strike> keyword"""
    print("\n" + "=" * 60)
    print("TEST 4: First Strike Mechanic")
    print("=" * 60)
    
    # Create game state
    manager = GameManager(seed=42)
    test_deck = [create_test_card_dict(f"Unit {i}") for i in range(50)]
    resource_deck = [create_test_card_dict(f"Resource {i}") for i in range(10)]
    game_state = manager.setup_game(test_deck, test_deck, resource_deck, resource_deck)
    
    # Create units
    attacker_card = create_test_card("First Striker", ap=5, hp=3)
    defender_card = create_test_card("Defender", ap=4, hp=5)
    
    attacker = create_test_unit(attacker_card, owner_id=0, turn_deployed=0)
    defender = create_test_unit(defender_card, owner_id=1, turn_deployed=0)
    
    # Add First Strike keyword
    attacker.add_keyword("first_strike", True, "card_text")
    
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(defender)
    game_state.turn_player = 0
    
    print(f"\n  Attacker: {attacker.card_data.name} (AP{attacker.ap}/HP{attacker.current_hp}) <First Strike>")
    print(f"  Defender: {defender.card_data.name} (AP{defender.ap}/HP{defender.current_hp})")
    
    # Create agents
    agent_0 = RandomAgent(0, seed=42)
    agent_1 = RandomAgent(1, seed=43)
    agents = [agent_0, agent_1]
    
    # Run battle
    game_state, battle_logs = BattleManager.run_complete_battle(
        game_state=game_state,
        attacker=attacker,
        target="UNIT",
        target_unit=defender,
        agents=agents
    )
    
    # Print logs
    for log in battle_logs:
        print(f"  {log}")
    
    # Verify First Strike mentioned in logs
    has_first_strike_log = any("FIRST STRIKE" in log for log in battle_logs)
    assert has_first_strike_log, "First Strike should be mentioned in battle logs"
    print(f"\n  ✓ First Strike keyword detected and applied")
    
    print("\n✓ TEST 4 PASSED: First Strike works correctly")
    return True


def test_early_termination():
    """Test battle early termination when units destroyed"""
    print("\n" + "=" * 60)
    print("TEST 5: Early Battle Termination")
    print("=" * 60)
    
    # Create game state
    manager = GameManager(seed=42)
    test_deck = [create_test_card_dict(f"Unit {i}") for i in range(50)]
    resource_deck = [create_test_card_dict(f"Resource {i}") for i in range(10)]
    game_state = manager.setup_game(test_deck, test_deck, resource_deck, resource_deck)
    
    # Create attacker and already-damaged defender
    attacker_card = create_test_card("Attacker", ap=5, hp=5)
    defender_card = create_test_card("Weak Defender", ap=3, hp=1)  # Very low HP
    
    attacker = create_test_unit(attacker_card, owner_id=0, turn_deployed=0)
    defender = create_test_unit(defender_card, owner_id=1, turn_deployed=0)
    defender.current_hp = 0  # Set HP to 0 (destroyed)
    
    game_state.players[0].battle_area.append(attacker)
    # Don't add defender since it's already destroyed
    
    print(f"\n  Attacker: {attacker.card_data.name}")
    print(f"  Defender: HP = {defender.current_hp} (destroyed: {defender.is_destroyed})")
    
    # Start battle
    game_state, battle_state = BattleManager.start_battle(
        game_state, attacker, "UNIT", defender
    )
    
    # Execute attack step
    game_state, log = BattleManager.execute_attack_step(game_state, battle_state)
    print(f"  {log}")
    
    # Check for early termination
    should_skip = BattleManager.check_units_destroyed_or_moved(battle_state)
    assert should_skip, "Should skip to Battle End when defender destroyed"
    print(f"  ✓ Early termination detected: {should_skip}")
    
    print("\n✓ TEST 5 PASSED: Early termination works correctly")
    return True


def run_all_tests():
    """Run all battle manager tests"""
    print("\n")
    print("=" * 60)
    print("BATTLE MANAGER TEST SUITE")
    print("=" * 60)
    print("\n")
    
    tests = [
        test_battle_steps,
        test_blocker_mechanic,
        test_player_attack,
        test_first_strike,
        test_early_termination,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED: {test.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        return True
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
