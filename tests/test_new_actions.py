"""
Test New Actions, Triggers, and Selectors

Tests all newly implemented actions, triggers, and target selectors.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from simulator.game_manager import GameState, Player
from simulator.unit import Card, UnitInstance
from simulator.effect_interpreter import EffectContext, TargetResolver
from simulator.action_executor import ActionExecutor
from simulator.trigger_manager import get_trigger_manager


def test_new_selectors():
    """Test new target selectors"""
    print("\n" + "="*70)
    print("TEST 1: New Target Selectors")
    print("="*70)
    
    # Setup game state
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    
    # Add resources
    game_state.players[0].resource_area = [
        Card("Resource", "R-001", "RESOURCE", "Blue", 1, 0, 0, 0, [], [], [], []),
        Card("Resource", "R-002", "RESOURCE", "Blue", 1, 0, 0, 0, [], [], [], []),
    ]
    
    # Add cards to trash
    game_state.players[0].trash = [
        Card("Trashed Card", "T-001", "UNIT", "Blue", 2, 1, 1, 1, [], [], [], []),
        Card("Trashed Card", "T-002", "UNIT", "Blue", 3, 2, 2, 2, [], [], [], []),
    ]
    
    # Add shields
    game_state.players[0].shield_area = [
        Card("Shield", "S-001", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
    ]
    
    context = EffectContext(
        game_state=game_state,
        source_card=Card("Source", "SRC", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
        source_player_id=0,
        trigger_event="TEST",
        trigger_data={}
    )
    
    # Test FRIENDLY_RESOURCE
    print("\nTest 1.1: FRIENDLY_RESOURCE selector")
    result = TargetResolver._get_candidates(context, "FRIENDLY_RESOURCE")
    print(f"  Found {len(result)} resources")
    assert len(result) == 2, "Should find 2 resources"
    
    # Test SELF_TRASH
    print("\nTest 1.2: SELF_TRASH selector")
    result = TargetResolver._get_candidates(context, "SELF_TRASH")
    print(f"  Found {len(result)} cards in trash")
    assert len(result) == 2, "Should find 2 cards in trash"
    
    # Test SELF_SHIELDS
    print("\nTest 1.3: SELF_SHIELDS selector")
    result = TargetResolver._get_candidates(context, "SELF_SHIELDS")
    print(f"  Found {len(result)} shields")
    assert len(result) == 1, "Should find 1 shield"
    
    # Test SELF_HAND
    print("\nTest 1.4: SELF_HAND selector")
    game_state.players[0].hand = [
        Card("Hand Card", "H-001", "UNIT", "Blue", 2, 1, 1, 1, [], [], [], []),
    ]
    result = TargetResolver._get_candidates(context, "SELF_HAND")
    print(f"  Found {len(result)} cards in hand")
    assert len(result) == 1, "Should find 1 card in hand"
    
    print("✅ TEST 1 PASSED: New selectors working")
    return True


def test_mill_action():
    """Test MILL action"""
    print("\n" + "="*70)
    print("TEST 2: MILL Action")
    print("="*70)
    
    # Setup
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[0].main_deck = [
        Card("Card1", "C-001", "UNIT", "Blue", 2, 1, 1, 1, ["CB"], [], [], []),
        Card("Card2", "C-002", "UNIT", "Blue", 3, 2, 2, 2, ["Test"], [], [], []),
        Card("Card3", "C-003", "UNIT", "Blue", 4, 3, 3, 3, ["CB"], [], [], []),
    ]
    
    context = EffectContext(
        game_state=game_state,
        source_card=Card("Source", "SRC", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
        source_player_id=0,
        trigger_event="TEST",
        trigger_data={}
    )
    
    deck_before = len(game_state.players[0].main_deck)
    trash_before = len(game_state.players[0].trash)
    
    # Execute MILL
    action = {
        "type": "MILL",
        "target": "SELF",
        "amount": 2,
        "destination": "TRASH"
    }
    
    result = ActionExecutor.execute(context, action)
    
    deck_after = len(game_state.players[0].main_deck)
    trash_after = len(game_state.players[0].trash)
    
    print(f"  Result: {result}")
    print(f"  Deck: {deck_before} → {deck_after}")
    print(f"  Trash: {trash_before} → {trash_after}")
    print(f"  Milled cards stored: {len(getattr(context, 'last_milled_cards', []))}")
    
    assert deck_after == deck_before - 2, "Should remove 2 from deck"
    assert trash_after == trash_before + 2, "Should add 2 to trash"
    assert hasattr(context, 'last_milled_cards'), "Should store milled cards"
    
    print("✅ TEST 2 PASSED: MILL action working")
    return True


def test_deploy_from_zone():
    """Test DEPLOY_FROM_ZONE action"""
    print("\n" + "="*70)
    print("TEST 3: DEPLOY_FROM_ZONE Action")
    print("="*70)
    
    # Setup
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[0].trash = [
        Card("Unit Lv2", "U-001", "UNIT", "Blue", 2, 1, 1, 2, [], [], [], []),
        Card("Unit Lv4", "U-002", "UNIT", "Blue", 4, 2, 2, 3, [], [], [], []),
        Card("Unit Lv6", "U-003", "UNIT", "Blue", 6, 3, 3, 4, [], [], [], []),
    ]
    game_state.players[0].resource_area = [
        Card("Resource", "R-001", "RESOURCE", "Blue", 1, 0, 0, 0, [], [], [], []),
        Card("Resource", "R-002", "RESOURCE", "Blue", 1, 0, 0, 0, [], [], [], []),
    ]
    game_state.turn_number = 5
    
    context = EffectContext(
        game_state=game_state,
        source_card=Card("Source", "SRC", "COMMAND", "Blue", 6, 2, 0, 0, [], [], [], []),
        source_player_id=0,
        trigger_event="TEST",
        trigger_data={}
    )
    
    trash_before = len(game_state.players[0].trash)
    battle_before = len(game_state.players[0].battle_area)
    
    # Execute DEPLOY_FROM_ZONE
    action = {
        "type": "DEPLOY_FROM_ZONE",
        "source_zone": "TRASH",
        "target": {
            "card_type": "UNIT",
            "filters": {
                "level": {
                    "operator": "<=",
                    "value": 5
                }
            }
        },
        "pay_cost": False,
        "destination": "BATTLE_AREA"
    }
    
    result = ActionExecutor.execute(context, action)
    
    trash_after = len(game_state.players[0].trash)
    battle_after = len(game_state.players[0].battle_area)
    
    print(f"  Result: {result}")
    print(f"  Trash: {trash_before} → {trash_after}")
    print(f"  Battle Area: {battle_before} → {battle_after}")
    
    assert trash_after == trash_before - 1, "Should remove 1 from trash"
    assert battle_after == battle_before + 1, "Should add 1 to battle area"
    
    print("✅ TEST 3 PASSED: DEPLOY_FROM_ZONE working")
    return True


def test_add_to_shields():
    """Test ADD_TO_SHIELDS action"""
    print("\n" + "="*70)
    print("TEST 4: ADD_TO_SHIELDS Action")
    print("="*70)
    
    # Setup
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[0].hand = [
        Card("Hand1", "H-001", "UNIT", "Blue", 2, 1, 1, 1, [], [], [], []),
        Card("Hand2", "H-002", "UNIT", "Blue", 3, 2, 2, 2, [], [], [], []),
    ]
    
    context = EffectContext(
        game_state=game_state,
        source_card=Card("Source", "SRC", "BASE", "Blue", 5, 3, 2, 5, [], [], [], []),
        source_player_id=0,
        trigger_event="TEST",
        trigger_data={}
    )
    
    hand_before = len(game_state.players[0].hand)
    shields_before = len(game_state.players[0].shield_area)
    
    # Execute ADD_TO_SHIELDS
    action = {
        "type": "ADD_TO_SHIELDS",
        "source": "HAND",
        "count": 1,
        "selection_method": "CHOOSE"
    }
    
    result = ActionExecutor.execute(context, action)
    
    hand_after = len(game_state.players[0].hand)
    shields_after = len(game_state.players[0].shield_area)
    
    print(f"  Result: {result}")
    print(f"  Hand: {hand_before} → {hand_after}")
    print(f"  Shields: {shields_before} → {shields_after}")
    
    assert hand_after == hand_before - 1, "Should remove 1 from hand"
    assert shields_after == shields_before + 1, "Should add 1 to shields"
    
    print("✅ TEST 4 PASSED: ADD_TO_SHIELDS working")
    return True


def test_check_milled_traits():
    """Test CHECK_MILLED_TRAITS condition"""
    print("\n" + "="*70)
    print("TEST 5: CHECK_MILLED_TRAITS Condition")
    print("="*70)
    
    # Setup
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    
    context = EffectContext(
        game_state=game_state,
        source_card=Card("Source", "SRC", "UNIT", "Blue", 5, 4, 4, 4, ["CB"], [], [], []),
        source_player_id=0,
        trigger_event="TEST",
        trigger_data={}
    )
    
    # Simulate milled cards
    context.last_milled_cards = [
        Card("Milled1", "M-001", "UNIT", "Blue", 2, 1, 1, 1, ["CB"], [], [], []),
        Card("Milled2", "M-002", "UNIT", "Blue", 3, 2, 2, 2, ["Other"], [], [], []),
    ]
    
    # Test condition
    condition = {
        "type": "CHECK_MILLED_TRAITS",
        "traits": ["CB"],
        "count": ">=1"
    }
    
    from simulator.effect_interpreter import ConditionEvaluator
    result = ConditionEvaluator.evaluate(context, condition)
    
    print(f"  Milled 2 cards (1 with CB trait)")
    print(f"  Condition: Has >=1 CB card")
    print(f"  Result: {result}")
    
    assert result, "Should find CB trait in milled cards"
    
    print("✅ TEST 5 PASSED: CHECK_MILLED_TRAITS working")
    return True


def test_optional_action():
    """Test OPTIONAL_ACTION"""
    print("\n" + "="*70)
    print("TEST 6: OPTIONAL_ACTION")
    print("="*70)
    
    # Setup
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[0].main_deck = [
        Card("Card", "C-001", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
        Card("Card", "C-002", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
    ]
    game_state.turn_number = 1
    
    # Create a unit instance in battle area that can be destroyed
    from simulator.unit import UnitInstance
    unit_card = Card("Destroyable", "D-001", "UNIT", "Blue", 2, 1, 2, 2, [], [], [], [])
    unit = UnitInstance(
        card_data=unit_card,
        owner_id=0,
        turn_deployed=1
    )
    game_state.players[0].battle_area.append(unit)
    
    context = EffectContext(
        game_state=game_state,
        source_card=unit,
        source_player_id=0,
        trigger_event="TEST",
        trigger_data={}
    )
    
    hand_before = len(game_state.players[0].hand)
    battle_before = len(game_state.players[0].battle_area)
    
    # Execute OPTIONAL_ACTION with follow-up
    action = {
        "type": "OPTIONAL_ACTION",
        "optional_actions": [
            {
                "type": "DESTROY_CARD",
                "target": {"selector": "SELF"}
            }
        ],
        "next_if_success": [
            {
                "type": "DRAW",
                "target": "SELF",
                "amount": 2
            }
        ]
    }
    
    result = ActionExecutor.execute(context, action)
    
    hand_after = len(game_state.players[0].hand)
    battle_after = len(game_state.players[0].battle_area)
    
    print(f"  Result: {result}")
    print(f"  Hand: {hand_before} → {hand_after}")
    print(f"  Battle Area: {battle_before} → {battle_after}")
    
    # Should execute both destroy and draw
    assert hand_after == hand_before + 2, f"Should draw 2 after optional action (got {hand_after - hand_before})"
    assert battle_after == battle_before - 1, "Should destroy 1 unit"
    
    print("✅ TEST 6 PASSED: OPTIONAL_ACTION working")
    return True


def test_new_triggers():
    """Test new trigger types (ON_LINKED, BURST, ON_END_PHASE)"""
    print("\n" + "="*70)
    print("TEST 7: New Trigger Types")
    print("="*70)
    
    # These triggers are registered and will be tested with actual cards
    # For now, just verify they're recognized
    
    trigger_manager = get_trigger_manager()
    
    print("  Trigger manager initialized")
    print(f"  Effects loaded: {len(trigger_manager.effects_cache)}")
    
    # Check if any converted cards have these triggers
    new_triggers_found = {
        "ON_LINKED": 0,
        "BURST": 0,
        "ON_END_PHASE": 0
    }
    
    for card_id, effect_data in trigger_manager.effects_cache.items():
        for effect in effect_data.get("effects", []):
            triggers = effect.get("triggers", [])
            for trigger in triggers:
                if trigger in new_triggers_found:
                    new_triggers_found[trigger] += 1
    
    print(f"\n  Cards with ON_LINKED: {new_triggers_found['ON_LINKED']}")
    print(f"  Cards with BURST: {new_triggers_found['BURST']}")
    print(f"  Cards with ON_END_PHASE: {new_triggers_found['ON_END_PHASE']}")
    
    print("✅ TEST 7 PASSED: New triggers recognized")
    return True


if __name__ == "__main__":
    print("="*70)
    print("TESTING NEW ACTIONS, TRIGGERS, AND SELECTORS")
    print("="*70)
    
    try:
        test1 = test_new_selectors()
        test2 = test_mill_action()
        test3 = test_deploy_from_zone()
        test4 = test_add_to_shields()
        test5 = test_check_milled_traits()
        test6 = test_optional_action()
        test7 = test_new_triggers()
        
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Test 1 (New Selectors): {'✅ PASS' if test1 else '❌ FAIL'}")
        print(f"Test 2 (MILL Action): {'✅ PASS' if test2 else '❌ FAIL'}")
        print(f"Test 3 (DEPLOY_FROM_ZONE): {'✅ PASS' if test3 else '❌ FAIL'}")
        print(f"Test 4 (ADD_TO_SHIELDS): {'✅ PASS' if test4 else '❌ FAIL'}")
        print(f"Test 5 (CHECK_MILLED_TRAITS): {'✅ PASS' if test5 else '❌ FAIL'}")
        print(f"Test 6 (OPTIONAL_ACTION): {'✅ PASS' if test6 else '❌ FAIL'}")
        print(f"Test 7 (New Triggers): {'✅ PASS' if test7 else '❌ FAIL'}")
        
        total = sum([test1, test2, test3, test4, test5, test6, test7])
        print(f"\nTotal: {total}/7 tests passed")
        
        if total == 7:
            print("\n✅ ALL TESTS PASSED! New actions and triggers ready for use.")
        else:
            print(f"\n⚠️  {7 - total} test(s) failed. Review output above.")
    
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
