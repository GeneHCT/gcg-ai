"""
Test effect system independently
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.game_manager import GameManager, GameState, Player
from simulator.unit import Card, UnitInstance
from simulator.effect_interpreter import EffectContext, EffectLoader
from simulator.action_executor import ActionExecutor
from simulator.trigger_manager import TriggerManager, get_trigger_manager


def test_simple_deploy_effect():
    """Test GD01-007: Deploy effect with condition"""
    print("\n" + "="*60)
    print("TEST 1: GD01-007 (Noin's Aries)")
    print("Effect: 【Destroyed】If you have another (OZ) Unit, draw 1")
    print("="*60)
    
    # Create minimal game state
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    
    # Add some cards to deck
    for i in range(10):
        game_state.players[0].main_deck.append(
            Card("Test Card", f"TEST-{i}", "UNIT", "Blue", 1, 1, 1, 1, ["Test"], [], [], [])
        )
    
    initial_hand_size = len(game_state.players[0].hand)
    
    # Create Noin's Aries unit
    noins_aries = Card("Noin's Aries", "GD01-007", "UNIT", "Blue", 3, 3, 2, 3, ["OZ"], [], [], [])
    unit = UnitInstance(card_data=noins_aries, owner_id=0)
    game_state.players[0].battle_area.append(unit)
    
    # Create another OZ unit
    oz_unit = Card("Other OZ Unit", "TEST-OZ", "UNIT", "Blue", 2, 2, 1, 1, ["OZ"], [], [], [])
    other_unit = UnitInstance(card_data=oz_unit, owner_id=0)
    game_state.players[0].battle_area.append(other_unit)
    
    print(f"Setup: Hand size = {initial_hand_size}, Units = {len(game_state.players[0].battle_area)}")
    print(f"  Unit 1: {unit.card_data.name} (OZ)")
    print(f"  Unit 2: {other_unit.card_data.name} (OZ)")
    
    # Trigger destroyed effect
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event(
        event_type="ON_DESTROYED",
        game_state=game_state,
        source_card=unit,
        source_player_id=0
    )
    
    final_hand_size = len(game_state.players[0].hand)
    
    print(f"\nResults: {results}")
    print(f"Hand size: {initial_hand_size} → {final_hand_size}")
    
    if final_hand_size == initial_hand_size + 1:
        print("✅ TEST PASSED: Drew 1 card as expected")
    else:
        print("❌ TEST FAILED: Hand size did not increase")
    
    return final_hand_size == initial_hand_size + 1


def test_deploy_damage_effect():
    """Test GD01-008: Deploy damage to rested unit"""
    print("\n" + "="*60)
    print("TEST 2: GD01-008 (Guntank)")
    print("Effect: 【Deploy】Choose 1 rested enemy Unit. Deal 1 damage")
    print("="*60)
    
    # Create game state
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    
    # Create guntank
    guntank = Card("Guntank", "GD01-008", "UNIT", "Blue", 2, 1, 1, 2, ["Earth Federation", "White Base Team"], [], [], [])
    unit = UnitInstance(card_data=guntank, owner_id=0)
    
    # Create enemy rested unit
    enemy = Card("Enemy Unit", "TEST-ENEMY", "UNIT", "Red", 2, 2, 2, 3, ["Zeon"], [], [], [])
    enemy_unit = UnitInstance(card_data=enemy, owner_id=1, is_rested=True)
    enemy_unit.current_hp = 3
    game_state.players[1].battle_area.append(enemy_unit)
    
    print(f"Setup: Enemy Unit HP = {enemy_unit.current_hp}, Rested = {enemy_unit.is_rested}")
    
    # Trigger deploy effect
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event(
        event_type="ON_DEPLOY",
        game_state=game_state,
        source_card=unit,
        source_player_id=0
    )
    
    print(f"\nResults: {results}")
    print(f"Enemy Unit HP: 3 → {enemy_unit.current_hp}")
    
    if enemy_unit.current_hp == 2:
        print("✅ TEST PASSED: Enemy took 1 damage")
    else:
        print(f"❌ TEST FAILED: Expected HP=2, got HP={enemy_unit.current_hp}")
    
    return enemy_unit.current_hp == 2


def test_grant_keyword_effect():
    """Test GD01-009: Deploy grant keyword"""
    print("\n" + "="*60)
    print("TEST 3: GD01-009 (G-Fighter)")
    print("Effect: 【Deploy】Grant <High-Maneuver> to (White Base Team) Unit")
    print("="*60)
    
    # Create game state
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    
    # Create G-Fighter
    g_fighter = Card("G-Fighter", "GD01-009", "UNIT", "Blue", 3, 2, 3, 2, ["Earth Federation", "White Base Team"], [], [], [])
    unit = UnitInstance(card_data=g_fighter, owner_id=0)
    
    # Create target unit
    target_unit_card = Card("Gundam", "GD01-013", "UNIT", "Blue", 4, 2, 3, 4, ["Earth Federation", "White Base Team"], [], [], [])
    target_unit = UnitInstance(card_data=target_unit_card, owner_id=0)
    game_state.players[0].battle_area.append(target_unit)
    
    print(f"Setup: Target has 'high_maneuver' keyword = {target_unit.has_keyword('high_maneuver')}")
    
    # Trigger deploy effect
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event(
        event_type="ON_DEPLOY",
        game_state=game_state,
        source_card=unit,
        source_player_id=0
    )
    
    print(f"\nResults: {results}")
    print(f"Target has 'high_maneuver' keyword = {target_unit.has_keyword('high_maneuver')}")
    
    if target_unit.has_keyword('high_maneuver'):
        print("✅ TEST PASSED: Keyword granted successfully")
    else:
        print("❌ TEST FAILED: Keyword not granted")
    
    return target_unit.has_keyword('high_maneuver')


if __name__ == "__main__":
    print("Testing Effect System")
    print("=" * 60)
    
    # Initialize trigger manager
    trigger_manager = get_trigger_manager()
    print(f"Loaded {len(trigger_manager.effects_cache)} card effects\n")
    
    # Run tests
    test1_passed = test_simple_deploy_effect()
    test2_passed = test_deploy_damage_effect()
    test3_passed = test_grant_keyword_effect()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Test 1 (Destroyed with condition): {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Test 2 (Deploy damage): {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"Test 3 (Deploy grant keyword): {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    total_passed = sum([test1_passed, test2_passed, test3_passed])
    print(f"\nTotal: {total_passed}/3 tests passed")
    
    if total_passed == 3:
        print("\n✅ ALL TESTS PASSED! Effect system is working correctly.")
    else:
        print(f"\n⚠️  {3 - total_passed} test(s) failed. Review output above.")
