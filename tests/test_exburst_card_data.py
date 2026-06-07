import json

from simulator.card_data import (
    load_card_lookup,
    normalize_exburst_cards,
    write_normalized_card_database,
)
from simulator.deck_loader import DeckLoader
from simulator.game_manager import GameSetup


def _raw_card(
    cardno: str,
    originalid: str,
    name: str,
    effectdata: str | None,
    *,
    color: str | None = "Blue",
    level: str = "1",
    cost: str = "1",
    apdata: str = "1",
    hp: str = "1",
    trait: str = "",
    link: str = "",
) -> dict:
    return {
        "cardno": cardno,
        "name": name,
        "color": color,
        "level": level,
        "cost": cost,
        "apdata": apdata,
        "hp": hp,
        "effectdata": effectdata,
        "trait": trait,
        "link": link,
        "originalid": originalid,
        "published": True,
    }


def test_normalize_exburst_cards_cleans_fields_and_collapses_alt_printings():
    raw_cards = [
        _raw_card(
            "GD01-111-ALT1",
            "GD01-111",
            "Battle of Aces",
            "【Burst】Draw 1.<br>【Main】Choose 1 enemy Unit. Deal 3 damage to it.<br>",
            color="Red",
            level="3",
            cost="2",
            apdata="",
            hp="",
        ),
        _raw_card(
            "GD01-111",
            "GD01-111",
            "Battle of Aces",
            "【Burst】Draw 1.<br>【Main】Choose 1 enemy Unit. Deal 3 damage to it.<br>",
            color="Red",
            level="3",
            cost="2",
            apdata="",
            hp="",
        ),
        _raw_card(
            "GD04-037",
            "GD04-037",
            "Gundam Kyrios (Trans-Am)",
            "While you have a red Pilot in play, this Unit gains &lt;First Strike&gt;.<br>",
            level="6",
            cost="5",
            apdata="5",
            hp="4",
            trait="CB / GN Drive",
            link="[Allelujah Haptism] / [Hallelujah Haptism]",
        ),
    ]

    cards = normalize_exburst_cards(raw_cards)
    cards_by_id = {card["ID"]: card for card in cards}

    command = cards_by_id["GD01-111"]
    assert command["CardNo"] == "GD01-111"
    assert command["AlternateCardNos"] == ["GD01-111", "GD01-111-ALT1"]
    assert command["Type"] == "COMMAND"
    assert command["Effect"] == [
        "【Burst】Draw 1.",
        "【Main】Choose 1 enemy Unit. Deal 3 damage to it.",
    ]
    assert command["Ap"] is None
    assert command["Hp"] is None

    unit = cards_by_id["GD04-037"]
    assert unit["Type"] == "UNIT"
    assert unit["Effect"] == [
        "While you have a red Pilot in play, this Unit gains <First Strike>."
    ]
    assert unit["Traits"] == ["CB", "GN Drive"]
    assert unit["Link"] == ["Allelujah Haptism", "Hallelujah Haptism"]
    assert unit["Level"] == 6


def test_normalize_exburst_cards_preserves_angle_keyword_and_joins_reminder_text():
    raw_cards = [
        _raw_card(
            "GD01-001",
            "GD01-001",
            "Gundam",
            "All your (White Base Team) Units gain <Repair 1>.<br>"
            "(At the end of your turn, this Unit recovers the specified number of HP.)<br>"
            "【When Paired】If you have 2 or more other Units in play, draw 1.<br>",
            trait="Earth Federation / White Base Team",
        )
    ]

    cards = normalize_exburst_cards(raw_cards)

    assert cards[0]["Effect"] == [
        "All your (White Base Team) Units gain <Repair 1>. (At the end of your turn, this Unit recovers the specified number of HP.)",
        "【When Paired】If you have 2 or more other Units in play, draw 1.",
    ]


def test_type_classification_for_resource_token_base_pilot_and_command():
    raw_cards = [
        _raw_card("R-003", "R-003", "Resource", "(Rest a Resource when paying a cost.)<br>", color=None, level="", cost="", apdata="", hp=""),
        _raw_card("T-015", "T-015", "CGS Mobile Worker", None, color=None, level="", cost="", apdata="1", hp="1", trait="Tekkadan"),
        _raw_card("ST01-015", "ST01-015", "White Base", "【Burst】Deploy this card.<br>【Deploy】Add 1 of your Shields to your hand.<br>", hp="5", trait="Earth Federation / Warship"),
        _raw_card("GD01-087", "GD01-087", "Sayla Mass", "【Burst】Add this card to your hand.<br>While this Unit is blue, it gains <Repair 1>.<br>", level="3", cost="1"),
        _raw_card("GD01-119", "GD01-119", "Iron-Fisted Discipline", "【Main】/【Action】Choose 1 enemy Unit.<br>【Pilot】[Chuatury Panlunch]<br>"),
    ]

    cards_by_id = {card["ID"]: card for card in normalize_exburst_cards(raw_cards)}

    assert cards_by_id["R-003"]["Type"] == "RESOURCE"
    assert cards_by_id["T-015"]["Type"] == "UNIT TOKEN"
    assert cards_by_id["ST01-015"]["Type"] == "BASE"
    assert cards_by_id["GD01-087"]["Type"] == "PILOT"
    assert cards_by_id["GD01-119"]["Type"] == "COMMAND"


def test_loader_resolves_deck_ids_by_canonical_originalid(tmp_path):
    raw_path = tmp_path / "exburst_cards.json"
    raw_path.write_text(
        json.dumps(
            [
                _raw_card(
                    "GD01-111-ALT1",
                    "GD01-111",
                    "Battle of Aces",
                    "【Main】Choose 1 enemy Unit. Deal 3 damage to it.<br>",
                    color="Red",
                    level="3",
                    cost="2",
                    apdata="",
                    hp="",
                )
            ]
        ),
        encoding="utf-8",
    )
    deck_path = tmp_path / "deck.txt"
    deck_path.write_text("// Main Deck\n50x GD01-111\n", encoding="utf-8")

    deck, is_valid = DeckLoader.load_deck(str(deck_path), str(raw_path))

    assert is_valid is True
    assert len(deck) == 50
    assert {card["ID"] for card in deck} == {"GD01-111"}
    assert {card["CardNo"] for card in deck} == {"GD01-111-ALT1"}


def test_write_normalized_cache_and_game_setup_smoke(tmp_path):
    raw_path = tmp_path / "exburst_cards.json"
    normalized_path = tmp_path / "exburst_cards_normalized.json"
    raw_path.write_text(
        json.dumps(
            [
                _raw_card(
                    "GD04-037",
                    "GD04-037",
                    "Gundam Kyrios (Trans-Am)",
                    "While you have a red Pilot in play, this Unit gains <First Strike>.<br>",
                    level="6",
                    cost="5",
                    apdata="5",
                    hp="4",
                    trait="CB / GN Drive",
                    link="[Allelujah Haptism]",
                ),
                _raw_card("R-003", "R-003", "Resource", "(Rest a Resource when paying a cost.)<br>", color=None, level="", cost="", apdata="", hp=""),
            ]
        ),
        encoding="utf-8",
    )

    normalized = write_normalized_card_database(raw_path, normalized_path)
    lookup = load_card_lookup(str(normalized_path))
    game_state = GameSetup.create_game_from_card_ids(
        ["GD04-037"] * 50,
        ["GD04-037"] * 50,
        ["R-003"] * 10,
        ["R-003"] * 10,
        card_database_path=str(normalized_path),
        seed=42,
    )

    assert len(normalized) == 2
    assert lookup["GD04-037"]["Type"] == "UNIT"
    assert len(game_state.players[0].hand) == 5
    assert len(game_state.players[0].shield_area) == 6
    assert len(game_state.players[0].resource_deck) == 10
