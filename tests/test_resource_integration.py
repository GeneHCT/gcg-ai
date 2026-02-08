"""
End-to-End Integration Test for Resource Manager

Demonstrates that the ResourceManager properly integrates with:
- Game state management
- Turn sequence
- Card playing
- Random agent
"""
import sys
from simulator.game_manager import GameState, Player, TurnManager, Phase
from simulator.unit import Card
from simulator.random_agent import LegalActionGenerator, ActionExecutor, Action, ActionType
from simulator.resource_manager import ResourceManager


def test_full_game_integration():
    """Test resource manager in a realistic game scenario"""
    print("=" * 80)
    print("INTEGRATION TEST: Resource Manager in Full Game Scenario")
    print("=" * 80)
    print()
    
    # Setup game state
    game_state = GameState(seed=42)
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    game_state.turn_player = 0
    game_state.current_phase = Phase.MAIN
    
    player = game_state.players[0]
    
    # Setup resource deck
    player.resource_deck = [
        Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE", 
             color="", level=0, cost=0)
        for i in range(10)
    ]
    
    # Add some starting resources
    for i in range(3):
        player.resource_area.append(player.resource_deck.pop(0))
    
    print(f"Turn 1 - Starting resources: {player.get_total_resources()}")
    
    # Add cards to hand
    player.hand = [
        Card(name="Cheap Unit", id="U1", type="UNIT", color="RED",
             level=1, cost=1, ap=2, hp=2),
        Card(name="Mid Unit", id="U2", type="UNIT", color="RED",
             level=2, cost=2, ap=3, hp=3),
        Card(name="Expensive Unit", id="U3", type="UNIT", color="RED",
             level=4, cost=4, ap=5, hp=5),
    ]
    
    # Turn 1: Play Cheap Unit (should succeed)
    print(f"\nAttempting to play Cheap Unit (Lv 1, Cost 1)...")
    action = Action(ActionType.PLAY_UNIT, card=player.hand[0])
    game_state, result = ActionExecutor.execute_action(game_state, action)
    print(f"  Result: {result}")
    assert "Deployed" in result, "Should be able to play cheap unit"
    assert len(player.battle_area) == 1
    
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"  Active resources after: {active} (used 1)")
    assert active == 2
    
    # Turn 2: Start new turn (resources should reset)
    print(f"\n--- Turn 2 ---")
    game_state = TurnManager.start_phase(game_state)
    game_state = TurnManager.resource_phase(game_state)
    game_state.current_phase = Phase.MAIN
    
    total = player.get_total_resources()
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"Resources: {total} total, {active} active")
    assert total == 4, "Should have 4 resources (3 + 1 added)"
    assert active == 4, "All resources should be active after start phase reset"
    
    # Turn 2: Play Mid Unit (should succeed now)
    print(f"\nAttempting to play Mid Unit (Lv 2, Cost 2)...")
    action = Action(ActionType.PLAY_UNIT, card=player.hand[0])  # hand[0] is now Mid Unit after removing first
    game_state, result = ActionExecutor.execute_action(game_state, action)
    print(f"  Result: {result}")
    assert "Deployed" in result, "Should be able to play mid unit"
    assert len(player.battle_area) == 2
    
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"  Active resources after: {active} (used 2)")
    assert active == 2
    
    # Try to play Expensive Unit (should fail - not enough Lv)
    print(f"\nAttempting to play Expensive Unit (Lv 4, Cost 4)...")
    can_play = ResourceManager.can_play_card(game_state, 0, player.hand[0])
    print(f"  Can play? {can_play} (expected: False - Lv 4 > 4 total resources)")
    assert can_play == False
    
    # Turn 3: Add more resources
    print(f"\n--- Turn 3 ---")
    game_state = TurnManager.start_phase(game_state)
    game_state = TurnManager.resource_phase(game_state)
    game_state.current_phase = Phase.MAIN
    
    total = player.get_total_resources()
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"Resources: {total} total, {active} active")
    assert total == 5
    assert active == 5
    
    # Now try expensive unit again (should succeed)
    print(f"\nAttempting to play Expensive Unit (Lv 4, Cost 4)...")
    can_play = ResourceManager.can_play_card(game_state, 0, player.hand[0])
    print(f"  Can play? {can_play} (expected: True - Lv 4 <= 5, Cost 4 <= 5)")
    assert can_play == True
    
    action = Action(ActionType.PLAY_UNIT, card=player.hand[0])
    game_state, result = ActionExecutor.execute_action(game_state, action)
    print(f"  Result: {result}")
    assert "Deployed" in result
    assert len(player.battle_area) == 3
    
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"  Active resources after: {active} (used 4, 1 remaining)")
    assert active == 1
    
    print("\n" + "=" * 80)
    print("✓ FULL INTEGRATION TEST PASSED")
    print("=" * 80)
    print("\nResourceManager successfully integrates with:")
    print("  ✓ Game state management")
    print("  ✓ Turn sequence (start/resource phases)")
    print("  ✓ Card playing mechanics")
    print("  ✓ Action execution")
    print("  ✓ Resource reset between turns")
    print("  ✓ Lv and Cost condition enforcement")


if __name__ == "__main__":
    try:
        test_full_game_integration()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
