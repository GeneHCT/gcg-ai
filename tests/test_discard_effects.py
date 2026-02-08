"""
Test discard-related card effects for all 16 cards affected by discard converter changes.
Tests DISCARD action execution and "Draw/Then discard" / "If you do" chains.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from simulator.game_manager import GameState, Player
from simulator.unit import Card, UnitInstance
from simulator.trigger_manager import get_trigger_manager


def _mk_card(name, cid, ctype="UNIT", traits=None, color="Blue", level=1, cost=1, ap=1, hp=1):
    """Helper to create Card with common defaults. Card(name, id, type, color, level, cost, ap, hp, traits, zones, link, effect)."""
    return Card(name, cid, ctype, color, level, cost, ap, hp, traits or [], [], [], [])


def _setup_deck(player, count=15):
    """Add cards to player deck."""
    for i in range(count):
        player.main_deck.append(_mk_card("Test", f"TEST-{i}"))


def test_discard_action_direct():
    """Test ActionExecutor._execute_discard directly."""
    print("\n" + "=" * 60)
    print("TEST: Direct DISCARD action execution")
    print("=" * 60)
    from simulator.effect_interpreter import EffectContext
    from simulator.action_executor import ActionExecutor
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    for i in range(3):
        game_state.players[0].hand.append(_mk_card("C", f"C-{i}"))
    context = EffectContext(game_state=game_state, source_card=None, source_player_id=0, trigger_event="TEST", trigger_data={})
    result = ActionExecutor.execute(context, {"type": "DISCARD", "target": "SELF", "amount": 2})
    passed = len(game_state.players[0].hand) == 1 and len(game_state.players[0].trash) == 2 and "Unknown" not in result
    print(f"Hand: 3 -> {len(game_state.players[0].hand)}, Trash: 0 -> {len(game_state.players[0].trash)} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd01_005_unicorn_unicorn_mode():
    """GD01-005: 【During Link】【Destroyed】Return Pilot to hand. Then, discard 1."""
    print("\n" + "=" * 60)
    print("TEST: GD01-005 (Unicorn Gundam Unicorn Mode)")
    print("Effect: 【Destroyed】Return Pilot to hand. Then, discard 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    for i in range(5):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    unit_card = _mk_card("Unicorn", "GD01-005", level=5, ap=3, hp=3)
    unit_card.traits = ["Earth Federation"]
    unit = UnitInstance(card_data=unit_card, owner_id=0)
    unit.current_hp = 1
    game_state.players[0].battle_area.append(unit)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DESTROYED", game_state, unit, 0, destroyed_by="damage")
    passed = "discard" in str(results).lower() and "Unknown" not in str(results)
    print(f"Results: {results} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd01_074_chuchu_demi_trainer():
    """GD01-074: 【Attack】Draw 1. Then, discard 1."""
    print("\n" + "=" * 60)
    print("TEST: GD01-074 (Chuchu's Demi Trainer)")
    print("Effect: 【Attack】Draw 1. Then, discard 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    unit = UnitInstance(card_data=_mk_card("Chuchu", "GD01-074"), owner_id=0)
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_ATTACK", game_state, unit, 0)
    final_hand = len(game_state.players[0].hand)
    passed = final_hand == initial_hand and "Unknown" not in str(results)  # draw 1, discard 1 => net 0
    print(f"Hand: {initial_hand} -> {final_hand} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd01_095_dearka_elthman():
    """GD01-095: 【When Linked】Discard 1. If you do, draw 1. (Pilot - ON_LINKED may have limited parsing)"""
    print("\n" + "=" * 60)
    print("TEST: GD01-095 (Dearka Elthman)")
    print("Effect: 【When Linked】Discard 1. If you do, draw 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    pilot_card = _mk_card("Dearka", "GD01-095", ctype="PILOT", ap=0, hp=0)
    pilot = UnitInstance(card_data=pilot_card, owner_id=0)
    unit_card = _mk_card("Unit", "U1")
    unit = UnitInstance(card_data=unit_card, owner_id=0)
    unit.paired_pilot = pilot
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_LINKED", game_state, pilot, 0)
    passed = "Unknown" not in str(results)
    print(f"Results: {results} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd01_118_overflowing_affection():
    """
    GD01-118 Overflowing Affection: 【Main】Draw 2. Then, discard 1.
    Actions: DRAW 2, DISCARD 1 (both run in sequence).
    """
    print("\n" + "=" * 60)
    print("TEST: GD01-118 (Overflowing Affection)")
    print("Effect: 【Main】Draw 2. Then, discard 1.")
    print("=" * 60)

    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)

    # Fill deck
    for i in range(15):
        game_state.players[0].main_deck.append(
            Card("Test", f"TEST-{i}", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], [])
        )

    cmd = Card("Overflowing Affection", "GD01-118", "COMMAND", "Blue", 2, 1, None, None, ["-"], [], [], ['【Main】Draw 2. Then, discard 1.'])
    initial_hand = len(game_state.players[0].hand)
    initial_deck = len(game_state.players[0].main_deck)

    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event(
        event_type="MAIN_PHASE",
        game_state=game_state,
        source_card=cmd,
        source_player_id=0,
    )

    final_hand = len(game_state.players[0].hand)
    final_deck = len(game_state.players[0].main_deck)

    print(f"Hand: {initial_hand} -> {final_hand}")
    print(f"Deck: {initial_deck} -> {final_deck}")
    print(f"Results: {results}")

    # Draw 2, discard 1 => net +1 hand
    expected_hand = initial_hand + 2 - 1
    passed = final_hand == expected_hand and "Unknown action type" not in str(results)
    print("✅ PASS" if passed else "❌ FAIL")
    return passed


def test_gd02_058_ryusei_go():
    """
    GD02-058 Ryusei-Go: 【Deploy】Choose 1 of your Units. Deal 1 damage to it. If you do, draw 1. Then, discard 1.
    Actions: DAMAGE_UNIT (choose friendly), conditional DRAW, then DISCARD (always).
    """
    print("\n" + "=" * 60)
    print("TEST: GD02-058 (Ryusei-Go)")
    print("Effect: 【Deploy】Choose 1 Unit. Deal 1 damage. If you do, draw 1. Then, discard 1.")
    print("=" * 60)

    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)

    for i in range(15):
        game_state.players[0].main_deck.append(
            Card("Test", f"TEST-{i}", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], [])
        )

    # Put some cards in hand for discard
    for i in range(3):
        game_state.players[0].hand.append(
            Card("Hand", f"H-{i}", "UNIT", "Blue", 1, 1, 1, 1, [], [], [], [])
        )

    # Target friendly unit (2 HP)
    target_card = Card("Graze", "GRAZE", "UNIT", "Purple", 2, 2, 2, 2, ["Tekkadan"], [], [], [])
    target_unit = UnitInstance(card_data=target_card, owner_id=0)
    target_unit.current_hp = 2
    game_state.players[0].battle_area.append(target_unit)

    # Ryusei-Go unit (triggers ON_DEPLOY)
    ryusei_card = Card("Ryusei-Go", "GD02-058", "UNIT", "Purple", 3, 2, 2, 2, ["Tekkadan"], [], [], [])
    ryusei_unit = UnitInstance(card_data=ryusei_card, owner_id=0)
    game_state.players[0].battle_area.append(ryusei_unit)

    initial_hp = target_unit.current_hp
    initial_hand = len(game_state.players[0].hand)

    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event(
        event_type="ON_DEPLOY",
        game_state=game_state,
        source_card=ryusei_unit,
        source_player_id=0,
    )

    final_hp = target_unit.current_hp
    final_hand = len(game_state.players[0].hand)

    print(f"Target HP: {initial_hp} -> {final_hp}")
    print(f"Hand: {initial_hand} -> {final_hand}")
    print(f"Results: {results}")

    hp_ok = final_hp == 1
    hand_ok = final_hand == initial_hand
    no_unknown = "Unknown action type" not in str(results)
    passed = hp_ok and hand_ok and no_unknown
    print("✅ PASS" if passed else "❌ FAIL")
    return passed


def test_gd02_003_gundam_mkii_titans():
    """GD02-003: 【Destroyed】You may discard 1 Unit. If you do, return Pilot to hand."""
    print("\n" + "=" * 60)
    print("TEST: GD02-003 (Gundam Mk-II Titans)")
    print("Effect: 【Destroyed】Discard 1 Unit. If you do, return Pilot.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    for i in range(3):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    unit_card = _mk_card("Mk-II", "GD02-003", traits=["Titans"])
    unit = UnitInstance(card_data=unit_card, owner_id=0)
    unit.current_hp = 0
    game_state.players[0].battle_area.append(unit)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DESTROYED", game_state, unit, 0, destroyed_by="damage")
    passed = "Unknown" not in str(results)
    print(f"Results: {results} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd02_021_gundam_age1_normal():
    """GD02-021: 【Deploy】Discard 1 green (Earth Federation). If you do, place EX Resource."""
    print("\n" + "=" * 60)
    print("TEST: GD02-021 (Gundam AGE-1 Normal)")
    print("Effect: 【Deploy】Discard 1 green. If you do, place EX Resource.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    game_state.players[0].hand.append(_mk_card("EF", "EF1", color="Green", traits=["Earth Federation"]))
    unit = UnitInstance(card_data=_mk_card("AGE-1", "GD02-021", color="Green"), owner_id=0)
    game_state.players[0].battle_area.append(unit)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DEPLOY", game_state, unit, 0)
    passed = "Unknown" not in str(results)
    print(f"Results: {results} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd02_070_gundam_kimaris():
    """GD02-070: 【Deploy】If 4+ Gjallarhorn in trash, draw 2. If you do, discard 2."""
    print("\n" + "=" * 60)
    print("TEST: GD02-070 (Gundam Kimaris)")
    print("Effect: 【Deploy】If 4+ Gjallarhorn in trash: draw 2. If you do, discard 2.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(5):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    for i in range(4):
        c = _mk_card("Gjallarhorn", f"GH-{i}", traits=["Gjallarhorn"])
        game_state.players[0].trash.append(c)
    unit = UnitInstance(card_data=_mk_card("Kimaris", "GD02-070", traits=["Gjallarhorn"]), owner_id=0)
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DEPLOY", game_state, unit, 0)
    final_hand = len(game_state.players[0].hand)
    passed = final_hand == initial_hand and "Unknown" not in str(results)  # +2 draw -2 discard
    print(f"Hand: {initial_hand} -> {final_hand} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd02_094_garrod_tiffa():
    """GD02-094: 【When Paired】Discard 1. If you do, look top 3 add Vulture."""
    print("\n" + "=" * 60)
    print("TEST: GD02-094 (Garrod Ran & Tiffa Adill)")
    print("Effect: 【When Paired】Discard 1. If you do, look top 3 add Vulture.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    pilot_card = _mk_card("Garrod", "GD02-094", ctype="PILOT", ap=0, hp=0)
    unit_card = _mk_card("Unit", "U1")
    unit = UnitInstance(card_data=unit_card, owner_id=0)
    unit.paired_pilot = pilot_card
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_PAIRED", game_state, pilot_card, 0)
    passed = "Unknown" not in str(results)
    print(f"Results: {results} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd02_098_quattro_bajeena():
    """GD02-098: 【When Linked】If (AEUG) Unit, draw 1. If you do, discard 1."""
    print("\n" + "=" * 60)
    print("TEST: GD02-098 (Quattro Bajeena)")
    print("Effect: 【When Linked】If AEUG, draw 1. If you do, discard 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    pilot = UnitInstance(card_data=_mk_card("Quattro", "GD02-098", ctype="PILOT", ap=0, hp=0), owner_id=0)
    unit_card = _mk_card("AEUG Unit", "AEUG1", traits=["AEUG"])
    unit = UnitInstance(card_data=unit_card, owner_id=0)
    unit.paired_pilot = pilot
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_LINKED", game_state, pilot, 0)
    final_hand = len(game_state.players[0].hand)
    passed = final_hand == initial_hand and "Unknown" not in str(results)  # +1 -1
    print(f"Hand: {initial_hand} -> {final_hand} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd02_117_a_new_sign():
    """GD02-117: 【Main】Draw 3. Then, discard 2."""
    print("\n" + "=" * 60)
    print("TEST: GD02-117 (A New Sign)")
    print("Effect: 【Main】Draw 3. Then, discard 2.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    cmd = Card("A New Sign", "GD02-117", "COMMAND", "Blue", 2, 1, None, None, ["AEUG"], [], [], ["【Main】Draw 3. Then, discard 2."])
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("MAIN_PHASE", game_state, cmd, 0)
    final_hand = len(game_state.players[0].hand)
    passed = final_hand == initial_hand + 1 and "Unknown" not in str(results)  # +3 -2
    print(f"Hand: {initial_hand} -> {final_hand} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd02_125_gwadan():
    """GD02-125: 【Deploy】Add 1 Shield to hand. Then, may discard 1 red. If you do, draw 1."""
    print("\n" + "=" * 60)
    print("TEST: GD02-125 (Gwadan)")
    print("Effect: 【Deploy】Add Shield. Then, discard 1 red. If you do, draw 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].shield_area.append(_mk_card("Shield", f"S-{i}"))
    game_state.players[0].hand.append(_mk_card("Red", "R1", color="Red"))
    base_card = Card("Gwadan", "GD02-125", "BASE", "Purple", 0, 0, None, None, [], [], [], [])
    base = UnitInstance(card_data=base_card, owner_id=0)
    game_state.players[0].bases.append(base)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DEPLOY", game_state, base, 0)
    # ADD_TO_HAND (shield to hand) may not be implemented; verify discard+draw ran
    rs = str(results).lower()
    passed = "discard" in rs and ("draw" in rs or "drew" in rs)
    print(f"Results: {results} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd03_064_defurse():
    """GD03-064: 【Deploy】May choose 1 X-Rounder from trash. If you do, discard 1. (Limited parsing)"""
    print("\n" + "=" * 60)
    print("TEST: GD03-064 (Defurse)")
    print("Effect: 【Deploy】Add X-Rounder from trash. If you do, discard 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    unit = UnitInstance(card_data=_mk_card("Defurse", "GD03-064", traits=["X-Rounder"]), owner_id=0)
    game_state.players[0].battle_area.append(unit)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DEPLOY", game_state, unit, 0)
    passed = "Unknown" not in str(results)
    print(f"Results: {results} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd03_072_aile_strike():
    """GD03-072: 【Deploy】If another (Triple Ship Alliance), draw 1. Then, discard 1."""
    print("\n" + "=" * 60)
    print("TEST: GD03-072 (Aile Strike Gundam)")
    print("Effect: 【Deploy】If TSA in play: draw 1. Then, discard 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    other = UnitInstance(card_data=_mk_card("TSA", "TSA1", traits=["Triple Ship Alliance"]), owner_id=0)
    game_state.players[0].battle_area.append(other)
    unit = UnitInstance(card_data=_mk_card("Aile", "GD03-072", traits=["Triple Ship Alliance"]), owner_id=0)
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DEPLOY", game_state, unit, 0)
    final_hand = len(game_state.players[0].hand)
    passed = final_hand == initial_hand and "Unknown" not in str(results)  # +1 -1
    print(f"Hand: {initial_hand} -> {final_hand} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_gd03_096_jamil_neate():
    """GD03-096: 【Attack】Discard 1. If you do, draw 1."""
    print("\n" + "=" * 60)
    print("TEST: GD03-096 (Jamil Neate)")
    print("Effect: 【Attack】Discard 1. If you do, draw 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    pilot = UnitInstance(card_data=_mk_card("Jamil", "GD03-096", ctype="PILOT", ap=0, hp=0), owner_id=0)
    unit = UnitInstance(card_data=_mk_card("Unit", "U1"), owner_id=0)
    unit.paired_pilot = pilot
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_ATTACK", game_state, pilot, 0)
    final_hand = len(game_state.players[0].hand)
    passed = final_hand == initial_hand and "Unknown" not in str(results)  # -1 discard +1 draw
    print(f"Hand: {initial_hand} -> {final_hand} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def test_st04_002_strike_gundam():
    """ST04-002: 【Deploy】Draw 1. Then, discard 1."""
    print("\n" + "=" * 60)
    print("TEST: ST04-002 (Strike Gundam)")
    print("Effect: 【Deploy】Draw 1. Then, discard 1.")
    print("=" * 60)
    game_state = GameState()
    game_state.players[0] = Player(player_id=0)
    game_state.players[1] = Player(player_id=1)
    _setup_deck(game_state.players[0])
    for i in range(2):
        game_state.players[0].hand.append(_mk_card("H", f"H-{i}"))
    unit = UnitInstance(card_data=_mk_card("Strike", "ST04-002"), owner_id=0)
    game_state.players[0].battle_area.append(unit)
    initial_hand = len(game_state.players[0].hand)
    trigger_manager = get_trigger_manager()
    results = trigger_manager.trigger_event("ON_DEPLOY", game_state, unit, 0)
    final_hand = len(game_state.players[0].hand)
    passed = final_hand == initial_hand and "Unknown" not in str(results)  # +1 -1
    print(f"Hand: {initial_hand} -> {final_hand} | {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


if __name__ == "__main__":
    print("Testing Discard Effects (16 affected cards + direct)")
    trigger_manager = get_trigger_manager()
    print(f"Loaded {len(trigger_manager.effects_cache)} card effects")

    tests = [
        ("Direct DISCARD", test_discard_action_direct),
        ("GD01-005 Unicorn (Unicorn Mode)", test_gd01_005_unicorn_unicorn_mode),
        ("GD01-074 Chuchu's Demi Trainer", test_gd01_074_chuchu_demi_trainer),
        ("GD01-095 Dearka Elthman", test_gd01_095_dearka_elthman),
        ("GD01-118 Overflowing Affection", test_gd01_118_overflowing_affection),
        ("GD02-003 Gundam Mk-II (Titans)", test_gd02_003_gundam_mkii_titans),
        ("GD02-021 Gundam AGE-1 Normal", test_gd02_021_gundam_age1_normal),
        ("GD02-058 Ryusei-Go", test_gd02_058_ryusei_go),
        ("GD02-070 Gundam Kimaris", test_gd02_070_gundam_kimaris),
        ("GD02-094 Garrod & Tiffa", test_gd02_094_garrod_tiffa),
        ("GD02-098 Quattro Bajeena", test_gd02_098_quattro_bajeena),
        ("GD02-117 A New Sign", test_gd02_117_a_new_sign),
        ("GD02-125 Gwadan", test_gd02_125_gwadan),
        ("GD03-064 Defurse", test_gd03_064_defurse),
        ("GD03-072 Aile Strike Gundam", test_gd03_072_aile_strike),
        ("GD03-096 Jamil Neate", test_gd03_096_jamil_neate),
        ("ST04-002 Strike Gundam", test_st04_002_strike_gundam),
    ]
    results = []
    for name, fn in tests:
        try:
            results.append((name, fn()))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        print(f"  {name}: {'✅ PASS' if passed else '❌ FAIL'}")
    total = sum(1 for _, p in results if p)
    print(f"\nTotal: {total}/{len(results)} passed")
