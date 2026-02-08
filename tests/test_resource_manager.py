"""
Test Resource Manager Implementation

Tests the new ResourceManager system to ensure:
1. Lv condition checking works
2. Cost payment by resting resources works
3. Resources reset at start of turn
4. Resource limits are enforced
"""
import sys
from simulator.game_manager import GameState, Player
from simulator.unit import Card
from simulator.resource_manager import ResourceManager


def test_basic_resource_operations():
    """Test basic resource operations"""
    print("=" * 80)
    print("TEST 1: Basic Resource Operations")
    print("=" * 80)
    
    # Create a simple game state
    game_state = GameState(seed=42)
    game_state.players[0] = Player(player_id=0)
    
    # Add some resources
    for i in range(5):
        game_state.players[0].resource_area.append(
            Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE", 
                 color="", level=0, cost=0)
        )
    
    # Add EX resources
    game_state.players[0].ex_resources = 2
    
    # Test total resource count
    total = ResourceManager.count_total_resources(game_state, 0)
    print(f"Total resources: {total} (expected: 7)")
    assert total == 7, f"Expected 7 total resources, got {total}"
    
    # Test active resource count (all should be active initially)
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"Active resources: {active} (expected: 5)")
    assert active == 5, f"Expected 5 active resources, got {active}"
    
    print("✓ Basic resource operations work correctly\n")


def test_lv_condition():
    """Test Lv condition checking"""
    print("=" * 80)
    print("TEST 2: Lv Condition Checking")
    print("=" * 80)
    
    # Create game state with 3 resources
    game_state = GameState(seed=42)
    game_state.players[0] = Player(player_id=0)
    
    for i in range(3):
        game_state.players[0].resource_area.append(
            Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE",
                 color="", level=0, cost=0)
        )
    
    # Test Lv 1 card (should pass)
    assert ResourceManager.check_lv_condition(game_state, 0, 1) == True
    print("✓ Can play Lv 1 card with 3 resources")
    
    # Test Lv 3 card (should pass)
    assert ResourceManager.check_lv_condition(game_state, 0, 3) == True
    print("✓ Can play Lv 3 card with 3 resources")
    
    # Test Lv 4 card (should fail)
    assert ResourceManager.check_lv_condition(game_state, 0, 4) == False
    print("✓ Cannot play Lv 4 card with 3 resources")
    
    # Add EX resource and test Lv 4 again
    game_state.players[0].ex_resources = 1
    assert ResourceManager.check_lv_condition(game_state, 0, 4) == True
    print("✓ Can play Lv 4 card with 3 resources + 1 EX\n")


def test_cost_payment():
    """Test cost payment by resting resources"""
    print("=" * 80)
    print("TEST 3: Cost Payment by Resting Resources")
    print("=" * 80)
    
    # Create game state with 5 resources
    game_state = GameState(seed=42)
    game_state.players[0] = Player(player_id=0)
    
    for i in range(5):
        game_state.players[0].resource_area.append(
            Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE",
                 color="", level=0, cost=0)
        )
    
    # Check we can pay cost of 3
    can_pay = ResourceManager.can_pay_cost(game_state, 0, 3)
    print(f"Can pay cost of 3: {can_pay} (expected: True)")
    assert can_pay == True
    
    # Pay cost of 3
    success = ResourceManager.pay_cost(game_state, 0, 3)
    print(f"Paid cost of 3: {success}")
    assert success == True
    
    # Check active resources now (should be 2)
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"Active resources after paying 3: {active} (expected: 2)")
    assert active == 2
    
    # Try to pay cost of 3 again (should fail)
    can_pay = ResourceManager.can_pay_cost(game_state, 0, 3)
    print(f"Can pay cost of 3 again: {can_pay} (expected: False)")
    assert can_pay == False
    
    # Pay cost of 2 (should succeed)
    success = ResourceManager.pay_cost(game_state, 0, 2)
    print(f"Paid cost of 2: {success}")
    assert success == True
    
    # Check active resources now (should be 0)
    active = ResourceManager.count_active_resources(game_state, 0)
    print(f"Active resources after paying 2 more: {active} (expected: 0)")
    assert active == 0
    
    print("✓ Cost payment works correctly\n")


def test_resource_reset():
    """Test resource reset at start of turn"""
    print("=" * 80)
    print("TEST 4: Resource Reset at Start of Turn")
    print("=" * 80)
    
    # Create game state with 5 resources
    game_state = GameState(seed=42)
    game_state.players[0] = Player(player_id=0)
    
    for i in range(5):
        game_state.players[0].resource_area.append(
            Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE",
                 color="", level=0, cost=0)
        )
    
    # Pay cost of 3
    ResourceManager.pay_cost(game_state, 0, 3)
    active_before = ResourceManager.count_active_resources(game_state, 0)
    print(f"Active resources after spending: {active_before} (expected: 2)")
    assert active_before == 2
    
    # Reset resources
    ResourceManager.reset_all_resources(game_state, 0)
    active_after = ResourceManager.count_active_resources(game_state, 0)
    print(f"Active resources after reset: {active_after} (expected: 5)")
    assert active_after == 5
    
    print("✓ Resource reset works correctly\n")


def test_can_play_card():
    """Test can_play_card integration"""
    print("=" * 80)
    print("TEST 5: Can Play Card Integration")
    print("=" * 80)
    
    # Create game state with 4 resources
    game_state = GameState(seed=42)
    game_state.players[0] = Player(player_id=0)
    
    for i in range(4):
        game_state.players[0].resource_area.append(
            Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE",
                 color="", level=0, cost=0)
        )
    
    # Create a Lv 3, Cost 2 card
    card1 = Card(name="Unit A", id="U1", type="UNIT", color="RED",
                 level=3, cost=2, ap=3, hp=3)
    
    # Should be able to play (Lv 3 ≤ 4, Cost 2 ≤ 4)
    can_play = ResourceManager.can_play_card(game_state, 0, card1)
    print(f"Can play Lv 3 Cost 2 with 4 resources: {can_play} (expected: True)")
    assert can_play == True
    
    # Create a Lv 5 card
    card2 = Card(name="Unit B", id="U2", type="UNIT", color="RED",
                 level=5, cost=2, ap=5, hp=5)
    
    # Should NOT be able to play (Lv 5 > 4)
    can_play = ResourceManager.can_play_card(game_state, 0, card2)
    print(f"Can play Lv 5 Cost 2 with 4 resources: {can_play} (expected: False)")
    assert can_play == False
    
    # Create a Cost 5 card
    card3 = Card(name="Unit C", id="U3", type="UNIT", color="RED",
                 level=3, cost=5, ap=5, hp=3)
    
    # Should NOT be able to play (Cost 5 > 4)
    can_play = ResourceManager.can_play_card(game_state, 0, card3)
    print(f"Can play Lv 3 Cost 5 with 4 resources: {can_play} (expected: False)")
    assert can_play == False
    
    # Pay cost of 2
    ResourceManager.pay_cost(game_state, 0, 2)
    
    # Now we have 2 active resources left, so we CAN still play card1 (Cost 2)
    can_play = ResourceManager.can_play_card(game_state, 0, card1)
    print(f"Can play Lv 3 Cost 2 after spending 2: {can_play} (expected: True)")
    assert can_play == True
    
    # But if we pay 1 more, we can't play card1 anymore
    ResourceManager.pay_cost(game_state, 0, 1)
    can_play = ResourceManager.can_play_card(game_state, 0, card1)
    print(f"Can play Lv 3 Cost 2 after spending 3 total: {can_play} (expected: False)")
    assert can_play == False
    
    print("✓ Can play card integration works correctly\n")


def test_resource_limits():
    """Test resource area limits"""
    print("=" * 80)
    print("TEST 6: Resource Area Limits")
    print("=" * 80)
    
    # Create game state
    game_state = GameState(seed=42)
    game_state.players[0] = Player(player_id=0)
    
    # Add 15 resources (max limit)
    for i in range(15):
        game_state.players[0].resource_area.append(
            Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE",
                 color="", level=0, cost=0)
        )
    
    # Should not be able to add more
    can_add = ResourceManager.can_add_resource(game_state, 0, is_ex=False)
    print(f"Can add 16th resource: {can_add} (expected: False)")
    assert can_add == False
    
    # Add 5 EX resources
    game_state.players[0].ex_resources = 5
    
    # Should not be able to add more EX resources
    can_add = ResourceManager.can_add_resource(game_state, 0, is_ex=True)
    print(f"Can add 6th EX resource: {can_add} (expected: False)")
    assert can_add == False
    
    # Create new game state with 10 resources
    game_state2 = GameState(seed=42)
    game_state2.players[0] = Player(player_id=0)
    
    for i in range(10):
        game_state2.players[0].resource_area.append(
            Card(name=f"Resource {i}", id=f"R{i}", type="RESOURCE",
                 color="", level=0, cost=0)
        )
    
    # Should be able to add more
    can_add = ResourceManager.can_add_resource(game_state2, 0, is_ex=False)
    print(f"Can add 11th resource: {can_add} (expected: True)")
    assert can_add == True
    
    print("✓ Resource limits work correctly\n")


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "RESOURCE MANAGER TEST SUITE" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    try:
        test_basic_resource_operations()
        test_lv_condition()
        test_cost_payment()
        test_resource_reset()
        test_can_play_card()
        test_resource_limits()
        
        print("=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        print("\nResourceManager is working correctly!")
        print("The system now properly implements:")
        print("  • Rule 2-9: Lv (Level) condition checking")
        print("  • Rule 2-10: Cost payment by resting resources")
        print("  • Rule 4-4: Resource area limits (15 max, 5 EX max)")
        print("  • Rule 5-4: Active/Rested resource state")
        print("  • Rule 7-5-2-2: Playing cards from hand")
        
    except AssertionError as e:
        print("\n" + "=" * 80)
        print("✗ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 80)
        print("✗ TEST ERROR")
        print("=" * 80)
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
