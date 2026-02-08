"""
Test Base System, Link System, and Rest Mechanics

Tests all three new systems independently and integrated.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from simulator.game_manager import GameState, Player, EXBase
from simulator.unit import Card, UnitInstance, PilotInstance
from simulator.base_system import BaseInstance, BaseManager
from simulator.link_system import LinkManager
from simulator.rest_mechanics import RestManager


def test_rest_mechanics():
    """Test Rest/Active mechanics"""
    print("\n" + "="*70)
    print("TEST 1: Rest/Active Mechanics")
    print("="*70)
    
    # Create game state
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    
    # Create a unit
    card = Card("Test Unit", "TEST-001", "UNIT", "Blue", 2, 1, 2, 3, ["Test"], [], [], [])
    unit = UnitInstance(card_data=card, owner_id=0)
    game_state.players[0].battle_area.append(unit)
    
    print(f"Initial state: is_rested = {unit.is_rested}")
    assert not unit.is_rested, "Unit should start active"
    
    # Rest the unit
    result = RestManager.rest_unit(unit)
    print(f"After rest: is_rested = {unit.is_rested}, result = {result}")
    assert unit.is_rested, "Unit should be rested"
    assert result, "Rest should return True"
    
    # Try to rest again (should fail)
    result = RestManager.rest_unit(unit)
    print(f"Try rest again: result = {result}")
    assert not result, "Can't rest an already rested unit"
    
    # Set active
    result = RestManager.set_unit_active(unit)
    print(f"After set active: is_rested = {unit.is_rested}, result = {result}")
    assert not unit.is_rested, "Unit should be active"
    assert result, "Set active should return True"
    
    # Reset all cards
    unit.is_rested = True
    RestManager.reset_all_cards(game_state, 0)
    print(f"After reset_all: is_rested = {unit.is_rested}")
    assert not unit.is_rested, "Unit should be active after reset"
    
    print("✅ TEST 1 PASSED: Rest/Active mechanics working")
    return True


def test_link_system():
    """Test Link System"""
    print("\n" + "="*70)
    print("TEST 2: Link System")
    print("="*70)
    
    # Test 1: Exact name match
    print("\nTest 2.1: Exact name match")
    unit_card = Card("Gundam", "GD01-013", "UNIT", "Blue", 4, 2, 3, 4, 
                    ["Earth Federation"], [], ["Amuro Ray"], [])
    pilot_card = Card("Amuro Ray", "ST01-010", "PILOT", "Blue", 4, 1, 0, 0,
                     ["Earth Federation"], [], [], [])
    
    result = LinkManager.check_link_condition(unit_card, pilot_card)
    print(f"  Unit 'Gundam' with link ['Amuro Ray']")
    print(f"  Pilot 'Amuro Ray'")
    print(f"  Result: {result}")
    assert result, "Exact name should match"
    
    # Test 2: Partial name match [xyz]
    print("\nTest 2.2: Partial name match [Garrod Ran]")
    unit_card2 = Card("Gundam X", "GD02-001", "UNIT", "Blue", 5, 3, 4, 5,
                     ["Earth Federation"], [], ["[Garrod Ran]"], [])
    pilot_card2 = Card("Garrod Ran & Tiffa Adill", "GD02-010", "PILOT", "Blue", 5, 2, 0, 0,
                      ["Earth Federation"], [], [], [])
    
    result = LinkManager.check_link_condition(unit_card2, pilot_card2)
    print(f"  Unit 'Gundam X' with link ['[Garrod Ran]']")
    print(f"  Pilot 'Garrod Ran & Tiffa Adill'")
    print(f"  Result: {result}")
    assert result, "Partial name [Garrod Ran] should match"
    
    # Test 3: Trait match (Tekkadan)
    print("\nTest 2.3: Trait match (Tekkadan)")
    unit_card3 = Card("Gundam Barbatos", "GD03-056", "UNIT", "Red", 4, 2, 2, 4,
                     ["Tekkadan"], [], ["(Tekkadan)"], [])
    pilot_card3 = Card("Mikazuki Augus", "ST05-010", "PILOT", "Red", 4, 1, 0, 0,
                      ["Tekkadan"], [], [], [])
    
    result = LinkManager.check_link_condition(unit_card3, pilot_card3)
    print(f"  Unit 'Gundam Barbatos' with link ['(Tekkadan)']")
    print(f"  Pilot 'Mikazuki Augus' with trait 'Tekkadan'")
    print(f"  Result: {result}")
    assert result, "Trait (Tekkadan) should match"
    
    # Test 4: No match
    print("\nTest 2.4: No match")
    result = LinkManager.check_link_condition(unit_card, pilot_card2)
    print(f"  Unit 'Gundam' requires 'Amuro Ray'")
    print(f"  Pilot 'Garrod Ran & Tiffa Adill'")
    print(f"  Result: {result}")
    assert not result, "Should not match wrong pilot"
    
    # Test 5: Pairing (any pilot can pair)
    print("\nTest 2.5: Pairing pilot with unit (ANY pilot can pair)")
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[0].hand.append(pilot_card)
    
    unit = UnitInstance(card_data=unit_card, owner_id=0, turn_deployed=1)
    game_state.players[0].battle_area.append(unit)
    game_state.turn_number = 1
    
    result = LinkManager.pair_pilot(game_state, unit, pilot_card, trigger_effects=False)
    print(f"  Pairing result: {result}")
    print(f"  Unit has pilot: {unit.paired_pilot is not None}")
    print(f"  Is linked: {unit.is_linked}")
    assert result, "Pairing should succeed"
    assert unit.paired_pilot is not None, "Unit should have pilot"
    assert unit.is_linked, "Unit should be linked (pilot matches link condition)"
    
    # Test 5b: Pairing with non-matching pilot (should still pair, but not link)
    print("\nTest 2.5b: Pairing with non-matching pilot (pairs but doesn't link)")
    unit2 = UnitInstance(card_data=unit_card, owner_id=0, turn_deployed=1)
    game_state.players[0].battle_area.append(unit2)
    game_state.players[0].hand.append(pilot_card2)  # Wrong pilot
    
    result = LinkManager.pair_pilot(game_state, unit2, pilot_card2, trigger_effects=False)
    print(f"  Unit 'Gundam' requires 'Amuro Ray'")
    print(f"  Pairing with 'Garrod Ran & Tiffa Adill'")
    print(f"  Pairing result: {result}")
    print(f"  Unit has pilot: {unit2.paired_pilot is not None}")
    print(f"  Is linked: {unit2.is_linked}")
    assert result, "Pairing should succeed (any pilot can pair)"
    assert unit2.paired_pilot is not None, "Unit should have pilot"
    assert not unit2.is_linked, "Unit should NOT be linked (pilot doesn't match)"
    
    # Test 6: Only Link Units can attack immediately
    print("\nTest 2.6: Link Units can attack immediately, paired units can't")
    
    # Linked unit (Test 5)
    can_attack_linked = LinkManager.can_link_unit_attack(unit, game_state.turn_number)
    print(f"  Linked unit (turn 1, deployed turn 1)")
    print(f"  Is linked: {unit.is_linked}")
    print(f"  Can attack: {can_attack_linked}")
    assert can_attack_linked, "Linked Unit should be able to attack immediately"
    
    # Paired but not linked unit (Test 5b)
    can_attack_paired = LinkManager.can_link_unit_attack(unit2, game_state.turn_number)
    print(f"  Paired unit (turn 1, deployed turn 1)")
    print(f"  Is linked: {unit2.is_linked}")
    print(f"  Can attack: {can_attack_paired}")
    assert not can_attack_paired, "Paired (not linked) Unit should NOT attack immediately"
    
    print("✅ TEST 2 PASSED: Link System working")
    return True


def test_base_system():
    """Test BASE System"""
    print("\n" + "="*70)
    print("TEST 3: BASE System")
    print("="*70)
    
    # Create game state
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[0].shield_area = [
        Card("Shield", "S1", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
        Card("Shield", "S2", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
        Card("Shield", "S3", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], []),
    ]
    game_state.turn_number = 1
    
    # Test 1: Deploy BASE card
    print("\nTest 3.1: Deploy BASE card")
    base_card = Card("Nahel Argama", "GD01-123", "BASE", "Blue", 5, 3, 2, 5,
                    ["Londo Bell"], [], [], 
                    ["【Burst】Deploy this card.", "【Deploy】Add 1 of your Shields to your hand."])
    game_state.players[0].hand.append(base_card)
    
    base = BaseManager.deploy_base(game_state, 0, base_card, trigger_effects=False)
    print(f"  Base deployed: {base is not None}")
    print(f"  Base name: {base.card_data.name if base else 'None'}")
    print(f"  Base HP: {base.current_hp}/{base.hp if base else 'None'}")
    print(f"  Bases in play: {len(game_state.players[0].bases)}")
    assert base is not None, "Base should be deployed"
    assert len(game_state.players[0].bases) == 1, "Should have 1 base"
    assert base.current_hp == 5, "Base should have 5 HP"
    
    # Test 2: Replace existing BASE
    print("\nTest 3.2: Replace existing BASE (old goes to trash)")
    base_card2 = Card("Archangel", "ST01-015", "BASE", "Blue", 4, 2, 2, 4,
                     ["Earth Federation"], [], [],
                     ["【Burst】Deploy this card.", "【Deploy】Draw 1."])
    game_state.players[0].hand.append(base_card2)
    
    trash_before = len(game_state.players[0].trash)
    base2 = BaseManager.deploy_base(game_state, 0, base_card2, trigger_effects=False)
    trash_after = len(game_state.players[0].trash)
    
    print(f"  Old base sent to trash: {trash_after > trash_before}")
    print(f"  New base deployed: {base2 is not None}")
    print(f"  Bases in play: {len(game_state.players[0].bases)}")
    assert len(game_state.players[0].bases) == 1, "Should still have 1 base"
    assert trash_after == trash_before + 1, "Old base should be in trash"
    assert base2.card_data.name == "Archangel", "New base should be Archangel"
    
    # Test 3: Damage preferentially to BASE
    print("\nTest 3.3: Damage preferentially to BASE")
    shields_before = len(game_state.players[0].shield_area)
    base_hp_before = base2.current_hp
    
    shields_destroyed, base_destroyed, burst = BaseManager.deal_damage_to_shields(
        game_state, 0, 2
    )
    
    print(f"  Damage dealt: 2")
    print(f"  Base HP: {base_hp_before} -> {base2.current_hp}")
    print(f"  Shields destroyed: {shields_destroyed}")
    print(f"  Base destroyed: {base_destroyed}")
    assert base2.current_hp == base_hp_before - 2, "Base should take 2 damage"
    assert shields_destroyed == 0, "No shields should be destroyed"
    assert not base_destroyed, "Base should not be destroyed"
    
    # Test 4: Destroy BASE
    print("\nTest 3.4: Destroy BASE (4 damage to remaining 2 HP)")
    shields_destroyed, base_destroyed, burst = BaseManager.deal_damage_to_shields(
        game_state, 0, 4
    )
    
    print(f"  Damage dealt: 4")
    print(f"  Base destroyed: {base_destroyed}")
    print(f"  Bases remaining: {len(game_state.players[0].bases)}")
    assert base_destroyed, "Base should be destroyed"
    assert len(game_state.players[0].bases) == 0, "No bases should remain"
    
    # Test 5: Damage to shields after BASE is destroyed
    print("\nTest 3.5: Damage to shields after BASE destroyed")
    shields_before = len(game_state.players[0].shield_area)
    shields_destroyed, base_destroyed, burst = BaseManager.deal_damage_to_shields(
        game_state, 0, 2
    )
    shields_after = len(game_state.players[0].shield_area)
    
    print(f"  Damage dealt: 2")
    print(f"  Shields: {shields_before} -> {shields_after}")
    print(f"  Shields destroyed: {shields_destroyed}")
    assert shields_destroyed == 2, "Should destroy 2 shields"
    assert shields_after == shields_before - 2, "Shield count should decrease"
    
    print("✅ TEST 3 PASSED: BASE System working")
    return True


if __name__ == "__main__":
    print("="*70)
    print("TESTING BASE, LINK, AND REST SYSTEMS")
    print("="*70)
    
    try:
        test1 = test_rest_mechanics()
        test2 = test_link_system()
        test3 = test_base_system()
        
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Test 1 (Rest/Active mechanics): {'✅ PASS' if test1 else '❌ FAIL'}")
        print(f"Test 2 (Link System): {'✅ PASS' if test2 else '❌ FAIL'}")
        print(f"Test 3 (BASE System): {'✅ PASS' if test3 else '❌ FAIL'}")
        
        total = sum([test1, test2, test3])
        print(f"\nTotal: {total}/3 tests passed")
        
        if total == 3:
            print("\n✅ ALL TESTS PASSED! All three systems working correctly.")
        else:
            print(f"\n⚠️  {3 - total} test(s) failed. Review output above.")
    
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
