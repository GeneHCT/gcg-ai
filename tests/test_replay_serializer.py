from datetime import datetime

from simulator.base_system import BaseInstance
from simulator.game_manager import EXBase, GameState, Player
from simulator.random_agent import Action, ActionType
from simulator.random_agent import Action, ActionType
from simulator.replay_serializer import ReplayRecorder, compute_frame_highlights, serialize_game_state
import pytest

from simulator.run_simulation import assert_safe_output_path, default_log_filename
from simulator.unit import Card, PilotInstance, UnitInstance


def make_card(
    name: str,
    card_id: str,
    card_type: str = "UNIT",
    color: str = "Blue",
    ap: int = 2,
    hp: int = 3,
) -> Card:
    return Card(
        name=name,
        id=card_id,
        type=card_type,
        color=color,
        level=1,
        cost=1,
        ap=ap,
        hp=hp,
        traits=["Test"],
        zones=[],
        link=[],
        effect=[],
    )


def test_assert_safe_output_path_rejects_decks_directory():
    with pytest.raises(ValueError, match="cannot be written under decks/"):
        assert_safe_output_path("decks/bg-haste.txt", "Log file")


def test_default_log_filename_uses_timestamp_and_deck_slugs():
    when = datetime(2026, 6, 10, 14, 30)
    assert (
        default_log_filename("decks/bg-haste.txt", "decks/rw-justice.txt", when=when)
        == "20260610-1430-bg-haste-vs-rw-justice.log"
    )
    assert default_log_filename(None, None, when=when) == "20260610-1430-p0-vs-p1.log"


def test_replay_serializer_includes_requested_player_zones():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}

    player = game_state.players[0]
    player.hand.append(make_card("Hand Card", "HAND-001"))
    player.main_deck.append(make_card("Deck Card", "DECK-001"))
    player.trash.append(make_card("Trash Card", "TRASH-001"))
    player.shield_area.append(make_card("Shield Card", "SHIELD-001"))
    player.resource_area.append(make_card("Resource Card", "RES-001", "RESOURCE"))
    player.banished.append(make_card("Exiled Card", "EXILE-001"))
    player.battle_area.append(UnitInstance(make_card("Field Unit", "FIELD-001"), owner_id=0))

    serialized = serialize_game_state(game_state)
    zones = serialized["players"]["0"]

    assert zones["hand"][0]["cardId"] == "HAND-001"
    assert zones["deck"]["count"] == 1
    assert zones["trash"][0]["cardId"] == "TRASH-001"
    assert zones["shields"][0]["cardId"] == "SHIELD-001"
    assert zones["bases"] == []
    assert zones["resourceArea"][0]["cardId"] == "RES-001"
    assert zones["field"][0]["cardId"] == "FIELD-001"
    assert zones["exiled"][0]["cardId"] == "EXILE-001"


def test_replay_serializer_includes_attached_pilot_and_action_metadata():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    unit = UnitInstance(make_card("Test Unit", "UNIT-001"), owner_id=0)
    pilot = PilotInstance(make_card("Test Pilot", "PILOT-001", "PILOT"), owner_id=0)
    unit.paired_pilot = pilot
    pilot.paired_unit = unit
    game_state.players[0].battle_area.append(unit)

    recorder = ReplayRecorder(seed=123)
    action = Action(ActionType.ATTACK_PLAYER, unit=unit)
    recorder.record(
        game_state,
        label="Attack",
        cause_type="move",
        summary=str(action),
        action=action,
        result="Attack resolved",
    )

    frame = recorder.to_dict()["frames"][0]
    serialized_unit = frame["players"]["0"]["field"][0]

    assert serialized_unit["attachedPilot"]["cardId"] == "PILOT-001"
    assert serialized_unit["attachedPilot"]["pairedUnit"]["cardId"] == "UNIT-001"
    assert frame["cause"]["move"]["type"] == "attack_player"
    assert frame["cause"]["action"]["type"] == "attack_player"
    assert frame["cause"]["result"] == "Attack resolved"


def test_replay_serializer_distinguishes_ex_base_and_real_base():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    game_state.players[0].bases.append(EXBase(owner_id=0))

    base_card = make_card("Real Base", "BASE-001", "BASE", "White", ap=1, hp=5)
    base = BaseInstance(base_card, owner_id=1, current_hp=4)
    game_state.players[1].bases.append(base)

    serialized = serialize_game_state(game_state)
    p0 = serialized["players"]["0"]
    p1 = serialized["players"]["1"]
    p0_base = p0["bases"][0]
    p1_base = p1["bases"][0]

    assert p0["shields"] == []
    assert p1["shields"] == []

    assert p0_base["cardId"] == "EX_BASE"
    assert p0_base["isExBase"] is True
    assert p0_base["ap"] == 0
    assert p0_base["currentHp"] == 3

    assert p1_base["cardId"] == "BASE-001"
    assert p1_base["name"] == "Real Base"
    assert p1_base["color"] == "White"
    assert p1_base["ap"] == 1
    assert p1_base["currentHp"] == 4
    assert p1_base["maxHp"] == 5
    assert p1_base["isExBase"] is False


def test_compute_frame_highlights_for_attack_and_block():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    attacker = UnitInstance(make_card("Attacker", "ATK-001"), owner_id=0)
    defender = UnitInstance(make_card("Blocker", "BLK-001"), owner_id=1)
    game_state.players[0].battle_area.append(attacker)
    game_state.players[1].battle_area.append(defender)
    game_state.in_battle = True
    game_state.battle_attacker = attacker
    game_state.battle_defender = defender

    attack_highlights = compute_frame_highlights(
        game_state,
        summary="Attack Step: Attacker attacks Blocker",
    )
    block_highlights = compute_frame_highlights(
        game_state,
        summary="Block Step: Blocker blocks!",
    )

    assert {"role": "attacking", "instanceId": "p0:field:0:ATK-001", "cardId": "ATK-001", "ownerId": 0} in attack_highlights
    assert {"role": "defending", "instanceId": "p1:field:0:BLK-001", "cardId": "BLK-001", "ownerId": 1} in attack_highlights
    assert {"role": "blocking", "instanceId": "p1:field:0:BLK-001", "cardId": "BLK-001", "ownerId": 1} in block_highlights

    command_action = Action(ActionType.PLAY_COMMAND, card=make_card("Intercept Orders", "CMD-001", "COMMAND"))
    command_highlights = compute_frame_highlights(game_state, action=command_action)
    assert {"role": "deploying", "cardId": "CMD-001", "ownerId": game_state.turn_player} in command_highlights


def test_compute_frame_highlights_disambiguates_same_card_copies():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    first_copy = UnitInstance(make_card("Rick Dom", "GD01-030"), owner_id=0)
    second_copy = UnitInstance(make_card("Rick Dom", "GD01-030"), owner_id=0)
    target = UnitInstance(make_card("Target", "TGT-001"), owner_id=1)
    game_state.players[0].battle_area = [first_copy, second_copy]
    game_state.players[1].battle_area = [target]

    highlights = compute_frame_highlights(
        game_state,
        action=Action(ActionType.ATTACK_UNIT, unit=second_copy, target=target),
    )

    assert {"role": "attacking", "instanceId": "p0:field:1:GD01-030", "cardId": "GD01-030", "ownerId": 0} in highlights
    assert {"role": "attacking", "instanceId": "p0:field:0:GD01-030", "cardId": "GD01-030", "ownerId": 0} not in highlights


def test_replay_serializer_normalizes_unknown_color_marker():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    game_state.players[0].hand.append(make_card("Colorless", "COLORLESS-001", color="-"))

    serialized = serialize_game_state(game_state)

    assert serialized["players"]["0"]["hand"][0]["color"] == "Neutral"
