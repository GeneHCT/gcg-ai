"""
Test suite for Command Card Action Timing Implementation
Tests trigger extraction, legal actions, and action step flow
"""
import json
from pathlib import Path
from convert_card_effects import CardEffectConverter
from simulator.game_manager import GameState, GameManager, Phase
from simulator.random_agent import LegalActionGenerator, ActionType, Action
from simulator.action_step_manager import ActionStepManager
from simulator.unit import Card


def test_trigger_extraction():
    """Test 1: Verify 【Main】/【Action】 cards get both triggers"""
    print("Test 1: Trigger Extraction")
    print("-" * 60)
    
    converter = CardEffectConverter()
    
    # Test dual-timing command cards
    test_cards = {
        'GD01-101': ('Deep Devotion - dual timing', True),
        'GD01-115': ('Zeon Remnant Forces - dual timing', True),
        'ST01-014': ('Burst + Main (not dual timing)', False)
    }
    
    results = []
    for card_id, (description, should_be_dual) in test_cards.items():
        effect_data = converter.convert_card(card_id)
        if effect_data:
            triggers = effect_data['effects'][0].get('triggers', [])
            
            # For dual-timing cards (Main/Action), expect both triggers
            if should_be_dual:
                has_both = 'MAIN_PHASE' in triggers and 'ACTION_PHASE' in triggers
                status = "✓ PASS" if has_both else "✗ FAIL"
                results.append((status, card_id, description, triggers))
            else:
                # For non-dual timing, check it does NOT have both
                has_both = 'MAIN_PHASE' in triggers and 'ACTION_PHASE' in triggers
                status = "✓ PASS" if not has_both else "✗ FAIL"
                results.append((status, card_id, description, triggers))
    
    for status, card_id, desc, triggers in results:
        print(f"{status}: {card_id} ({desc})")
        print(f"  Triggers: {triggers}")
    
    # Check if all tests passed
    all_passed = all(r[0] == "✓ PASS" for r in results)
    print(f"\nTest 1 Result: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 60)
    return all_passed


def test_legal_actions_main_phase():
    """Test 2: Verify command cards appear in legal actions during Main Phase"""
    print("\nTest 2: Legal Actions - Main Phase")
    print("-" * 60)
    
    # Create a simple game state
    try:
        from simulator.trigger_manager import get_trigger_manager
        trigger_manager = get_trigger_manager()
        
        # Mock a game state with a player having a command card in hand
        game_state = GameState()
        
        # Create mock players
        from simulator.game_manager import Player
        game_state.players = [Player(0), Player(1)]
        game_state.turn_player = 0
        game_state.current_phase = Phase.MAIN
        game_state.in_battle = False
        
        # Add a dual-timing command card to player's hand
        command_card = Card(
            name="Test Command",
            id="GD01-101",
            type="COMMAND",
            color="Blue",
            level=2,
            cost=1,
            ap=0,
            hp=0,
            traits=[],
            zones=[],
            link=[],
            effect=["【Main】/【Action】Test effect"]
        )
        
        game_state.players[0].hand = [command_card]
        game_state.players[0].resource_area = [Card(name="Resource", id="R1", type="UNIT", color="Blue", level=1, cost=0, ap=0, hp=0)]
        game_state.players[0].resource_area.append(Card(name="Resource", id="R2", type="UNIT", color="Blue", level=1, cost=0, ap=0, hp=0))
        
        # Get legal actions
        legal_actions = LegalActionGenerator.get_legal_actions(game_state)
        
        # Check if PLAY_COMMAND action exists
        command_actions = [a for a in legal_actions if a.action_type == ActionType.PLAY_COMMAND]
        
        if command_actions:
            print("✓ PASS: Command card appears in legal actions")
            print(f"  Found {len(command_actions)} PLAY_COMMAND action(s)")
            for action in command_actions:
                print(f"  - {action}")
        else:
            print("✗ FAIL: No PLAY_COMMAND actions found")
            print(f"  Available actions: {[str(a) for a in legal_actions]}")
        
        print(f"\nTest 2 Result: {'PASS' if command_actions else 'FAIL'}")
        print("=" * 60)
        return bool(command_actions)
        
    except Exception as e:
        print(f"✗ FAIL: Exception during test: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


def test_action_step_priority():
    """Test 3: Verify standby player gets priority first in action step"""
    print("\nTest 3: Action Step Priority")
    print("-" * 60)
    
    try:
        # Create game state
        game_state = GameState()
        from simulator.game_manager import Player
        game_state.players = [Player(0), Player(1)]
        game_state.turn_player = 0  # Player 0 is active
        
        # Enter action step
        game_state = ActionStepManager.enter_action_step(game_state, is_battle=False)
        
        # Check that standby player (Player 1) has priority
        expected_priority = 1  # Standby player
        actual_priority = game_state.action_step_priority_player
        
        if actual_priority == expected_priority:
            print(f"✓ PASS: Standby player (Player {expected_priority}) has priority")
            print(f"  Turn player: {game_state.turn_player}")
            print(f"  Priority player: {actual_priority}")
        else:
            print(f"✗ FAIL: Wrong priority player")
            print(f"  Expected: Player {expected_priority} (standby)")
            print(f"  Actual: Player {actual_priority}")
        
        # Check action step state
        if game_state.in_action_step:
            print("✓ in_action_step flag is True")
        else:
            print("✗ in_action_step flag is False")
        
        if game_state.action_step_consecutive_passes == 0:
            print("✓ consecutive_passes initialized to 0")
        else:
            print(f"✗ consecutive_passes is {game_state.action_step_consecutive_passes}")
        
        passed = (actual_priority == expected_priority and 
                 game_state.in_action_step and 
                 game_state.action_step_consecutive_passes == 0)
        
        print(f"\nTest 3 Result: {'PASS' if passed else 'FAIL'}")
        print("=" * 60)
        return passed
        
    except Exception as e:
        print(f"✗ FAIL: Exception during test: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


def test_action_step_pass_handling():
    """Test 4: Verify action step ends when both players pass consecutively"""
    print("\nTest 4: Action Step Pass Handling")
    print("-" * 60)
    
    try:
        # Create game state
        game_state = GameState()
        from simulator.game_manager import Player
        game_state.players = [Player(0), Player(1)]
        game_state.turn_player = 0
        
        # Enter action step
        game_state = ActionStepManager.enter_action_step(game_state, is_battle=False)
        initial_priority = game_state.action_step_priority_player
        
        print(f"Initial priority: Player {initial_priority}")
        
        # First pass
        pass_action = Action(ActionType.PASS)
        game_state, continues = ActionStepManager.handle_action_step_action(game_state, pass_action)
        
        print(f"After first pass:")
        print(f"  Consecutive passes: {game_state.action_step_consecutive_passes}")
        print(f"  Priority player: {game_state.action_step_priority_player}")
        print(f"  Action step continues: {continues}")
        
        if game_state.action_step_consecutive_passes != 1:
            print("✗ FAIL: Consecutive passes should be 1 after first pass")
            return False
        
        if game_state.action_step_priority_player == initial_priority:
            print("✗ FAIL: Priority should have switched after first pass")
            return False
        
        if not continues:
            print("✗ FAIL: Action step should continue after first pass")
            return False
        
        # Second pass
        game_state, continues = ActionStepManager.handle_action_step_action(game_state, pass_action)
        
        print(f"\nAfter second pass:")
        print(f"  Consecutive passes: {game_state.action_step_consecutive_passes}")
        print(f"  Action step continues: {continues}")
        
        if game_state.action_step_consecutive_passes != 2:
            print("✗ FAIL: Consecutive passes should be 2 after second pass")
            return False
        
        if continues:
            print("✗ FAIL: Action step should END after both players pass")
            return False
        
        print("\n✓ PASS: Action step correctly ends after both players pass")
        print(f"\nTest 4 Result: PASS")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Exception during test: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


def test_action_step_priority_alternation():
    """Test 5: Verify priority alternates correctly"""
    print("\nTest 5: Action Step Priority Alternation")
    print("-" * 60)
    
    try:
        # Create game state
        game_state = GameState()
        from simulator.game_manager import Player
        game_state.players = [Player(0), Player(1)]
        game_state.turn_player = 0
        
        # Enter action step
        game_state = ActionStepManager.enter_action_step(game_state, is_battle=False)
        
        priorities = [game_state.action_step_priority_player]
        print(f"Initial priority: Player {priorities[0]}")
        
        # Simulate several passes to test alternation
        for i in range(4):
            pass_action = Action(ActionType.PASS)
            game_state, continues = ActionStepManager.handle_action_step_action(game_state, pass_action)
            
            if not continues:
                print(f"  Action step ended after {i+1} passes")
                break
            
            priorities.append(game_state.action_step_priority_player)
            print(f"  After pass {i+1}: Player {priorities[-1]} has priority")
        
        # Check alternation pattern
        expected_pattern = [1, 0, 1, 0]  # Standby first, then alternates
        actual_pattern = priorities[:len(expected_pattern)]
        
        if actual_pattern == expected_pattern[:len(actual_pattern)]:
            print(f"\n✓ PASS: Priority alternates correctly: {actual_pattern}")
        else:
            print(f"\n✗ FAIL: Priority pattern incorrect")
            print(f"  Expected: {expected_pattern}")
            print(f"  Actual: {actual_pattern}")
            return False
        
        print(f"\nTest 5 Result: PASS")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Exception during test: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("COMMAND CARD ACTION TIMING TEST SUITE")
    print("=" * 60)
    
    results = {
        "Test 1: Trigger Extraction": test_trigger_extraction(),
        "Test 2: Legal Actions (Main Phase)": test_legal_actions_main_phase(),
        "Test 3: Action Step Priority": test_action_step_priority(),
        "Test 4: Action Step Pass Handling": test_action_step_pass_handling(),
        "Test 5: Action Step Priority Alternation": test_action_step_priority_alternation(),
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed_count = sum(results.values())
    
    print("=" * 60)
    print(f"Results: {passed_count}/{total} tests passed")
    print("=" * 60)
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
