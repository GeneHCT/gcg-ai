import json
from types import SimpleNamespace

import pytest

import convert_card_effects
from convert_card_effects import ExBurstEffectConverter
from simulator.action_executor import ActionExecutor
from simulator.effect_discovery import GameEffect, OpenRouterConfig, ParsedCard, parse_normalized_card_offline, parsed_card_to_ir
from simulator.effect_interpreter import ConditionEvaluator, EffectContext, EffectLoader
from simulator.ir_validator import validate_ir_effect_data
from simulator.trigger_manager import TriggerManager
from simulator.unit import Card, PilotInstance, UnitInstance
from tools.audit_exburst_conversion import audit_exburst_outputs


def _raw_card(cardno: str, effectdata: str, *, name: str = "Test Card") -> dict:
    return {
        "cardno": cardno,
        "originalid": cardno,
        "name": name,
        "color": "Blue",
        "level": "1",
        "cost": "1",
        "apdata": "1",
        "hp": "1",
        "trait": "",
        "link": "",
        "effectdata": effectdata,
        "published": True,
    }


def test_offline_discovery_marks_simple_draw_supported():
    card = {
        "ID": "GD99-001",
        "Name": "Training Orders",
        "Type": "COMMAND",
        "Cost": 1,
        "Color": "Blue",
        "Effect": ["【Main】Draw 1."],
    }

    parsed = parse_normalized_card_offline(card)
    effect_data = parsed_card_to_ir(card["ID"], parsed, raw_effects=card["Effect"])
    report = validate_ir_effect_data(effect_data)

    assert parsed.effects[0].is_supported is True
    assert effect_data["effects"][0]["actions"] == [{"type": "DRAW", "target": "SELF", "amount": 1}]
    assert report.is_supported is True


def test_offline_discovery_supports_choices_and_return_to_hand():
    card = {
        "ID": "GD99-002",
        "Name": "Retreat Signal",
        "Type": "COMMAND",
        "Cost": 1,
        "Color": "Blue",
        "Effect": ["【Main】Choose 1 enemy Unit. Return it to its owner's hand."],
    }

    parsed = parse_normalized_card_offline(card)
    effect_data = parsed_card_to_ir(card["ID"], parsed, raw_effects=card["Effect"])
    report = validate_ir_effect_data(effect_data)

    assert parsed.effects[0].is_supported is True
    assert effect_data["effects"][0]["actions"] == [
        {
            "type": "RETURN_TO_HAND",
            "target": {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"},
        }
    ]
    assert report.support_status == "supported"


def test_known_patterns_override_llm_shape_for_gd01_001_style_effects():
    raw_effects = [
        "All your (White Base Team) Units gain <Repair 1>. (At the end of your turn, this Unit recovers the specified number of HP.)",
        "【When Paired】If you have 2 or more other Units in play, draw 1.",
    ]
    card = {
        "ID": "GD01-001",
        "Name": "Gundam",
        "Type": "UNIT",
        "Cost": 2,
        "Color": "Blue",
        "Effect": raw_effects,
    }

    parsed = parse_normalized_card_offline(card)
    effect_data = parsed_card_to_ir(card["ID"], parsed, raw_effects=raw_effects)
    report = validate_ir_effect_data(effect_data)

    assert report.is_supported is True
    assert effect_data["metadata"]["support_status"] == "supported"
    assert effect_data["continuous_effects"] == [
        {
            "effect_id": "GD01-001-E1",
            "effect_type": "CONTINUOUS",
            "description": raw_effects[0],
            "modifiers": [
                {
                    "type": "GRANT_KEYWORD",
                    "target": {
                        "selector": "FRIENDLY_UNIT",
                        "filters": {"traits": ["White Base Team"]},
                    },
                    "keyword": "REPAIR",
                    "value": 1,
                }
            ],
            "is_supported": True,
            "unhandled_explanation": "",
            "metadata": {"raw_text": raw_effects[0], "source": "known_pattern"},
        }
    ]
    assert effect_data["effects"][0]["triggers"] == ["ON_PAIRED"]
    assert effect_data["effects"][0]["conditions"][0]["value"] == 2
    assert effect_data["effects"][0]["actions"] == [{"type": "DRAW", "target": "SELF", "amount": 1}]


def test_exburst_converter_writes_candidate_directory_without_touching_stable_output(tmp_path):
    raw_path = tmp_path / "exburst_cards.json"
    output_dir = tmp_path / "card_effects_exburst"
    raw_path.write_text(
        json.dumps(
            [
                _raw_card("GD99-001", "【Main】Draw 1.<br>", name="Training Orders"),
                _raw_card("GD99-002", "【Main】Choose 1 enemy Unit. Return it to its owner's hand.<br>", name="Retreat Signal"),
            ]
        ),
        encoding="utf-8",
    )

    converter = ExBurstEffectConverter(
        output_dir=str(output_dir),
        card_database_path=str(raw_path),
        log_file=str(tmp_path / "exburst_conversion.log"),
    )
    summary = converter.convert_all()

    assert summary["converted"] == 2
    assert (output_dir / "GD99-001").exists()
    assert (output_dir / "GD99-002").exists()
    assert summary["audit"]["supported"] == 2
    assert summary["audit"]["unsupported"] == 0
    latest_report = tmp_path / "docs" / "exburst_support_latest.json"
    latest_markdown = tmp_path / "docs" / "exburst_support_latest.md"
    history_report = tmp_path / "docs" / "exburst_support_history.jsonl"
    report_data = json.loads(latest_report.read_text(encoding="utf-8"))
    history_lines = history_report.read_text(encoding="utf-8").splitlines()

    assert latest_report.exists()
    assert latest_markdown.exists()
    assert history_report.exists()
    assert summary["support_status_report"]["json"] == str(latest_report)
    assert report_data["counts"]["supported"] == 2
    assert report_data["cards"]["supported"] == [
        {"id": "GD99-001", "name": "Training Orders", "issue_count": 0, "issues": []},
        {"id": "GD99-002", "name": "Retreat Signal", "issue_count": 0, "issues": []},
    ]
    assert "`GD99-001` - Training Orders" in latest_markdown.read_text(encoding="utf-8")
    assert len(history_lines) == 1
    assert json.loads(history_lines[0])["counts"]["supported"] == 2


def test_exburst_converter_skips_existing_outputs_by_default(tmp_path):
    raw_path = tmp_path / "exburst_cards.json"
    output_dir = tmp_path / "card_effects_exburst"
    output_dir.mkdir()
    raw_path.write_text(
        json.dumps(
            [
                _raw_card("GD99-001", "【Main】Draw 1.<br>", name="Training Orders"),
                _raw_card("GD99-002", "【Main】Draw 1.<br>", name="Backup Orders"),
            ]
        ),
        encoding="utf-8",
    )
    existing_output = output_dir / "GD99-001"
    existing_output.write_text("already converted", encoding="utf-8")

    converter = ExBurstEffectConverter(
        output_dir=str(output_dir),
        card_database_path=str(raw_path),
        max_workers=2,
        log_file=str(tmp_path / "exburst_conversion.log"),
    )
    summary = converter.convert_all()

    assert summary["converted"] == 1
    assert summary["skipped"] == 1
    assert existing_output.read_text(encoding="utf-8") == "already converted"
    assert (output_dir / "GD99-002").exists()


def test_exburst_converter_can_force_existing_output_regeneration(tmp_path):
    raw_path = tmp_path / "exburst_cards.json"
    output_dir = tmp_path / "card_effects_exburst"
    output_dir.mkdir()
    raw_path.write_text(
        json.dumps([_raw_card("GD99-001", "【Main】Draw 1.<br>", name="Training Orders")]),
        encoding="utf-8",
    )
    existing_output = output_dir / "GD99-001"
    existing_output.write_text("already converted", encoding="utf-8")

    converter = ExBurstEffectConverter(
        output_dir=str(output_dir),
        card_database_path=str(raw_path),
        skip_existing=False,
        log_file=str(tmp_path / "exburst_conversion.log"),
    )
    summary = converter.convert_all()

    assert summary["converted"] == 1
    assert summary["skipped"] == 0
    assert json.loads(existing_output.read_text(encoding="utf-8"))["card_id"] == "GD99-001"


def test_exburst_converter_ignores_ex_resource_cards_but_keeps_tokens(tmp_path):
    raw_path = tmp_path / "exburst_cards.json"
    output_dir = tmp_path / "card_effects_exburst"
    output_dir.mkdir()
    token_card = _raw_card("T-001", "【Main】Draw 1.<br>", name="Token")
    token_card["Type"] = "UNIT TOKEN"
    raw_path.write_text(
        json.dumps(
            [
                _raw_card("EXB-001", "【Main】Draw 1.<br>", name="EX Base"),
                _raw_card("EXRP-001", "【Main】Draw 1.<br>", name="EX Resource Pilot"),
                _raw_card("EXBP-001", "【Main】Draw 1.<br>", name="EX Base Pilot"),
                _raw_card("EXR-001", "【Main】Draw 1.<br>", name="EX Resource"),
                _raw_card("R-001", "【Main】Draw 1.<br>", name="Resource"),
                _raw_card("RP-001", "【Main】Draw 1.<br>", name="RP - Resource"),
                token_card,
                _raw_card("GD99-001", "【Main】Draw 1.<br>", name="Training Orders"),
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "EXB-001").write_text(
        json.dumps(
            {
                "card_id": "EXB-001",
                "effects": [],
                "continuous_effects": [
                    {
                        "effect_id": "EXB-001-E1",
                        "effect_type": "CONTINUOUS",
                        "is_supported": False,
                        "unhandled_explanation": "old ignored output",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    converter = ExBurstEffectConverter(
        output_dir=str(output_dir),
        card_database_path=str(raw_path),
        log_file=str(tmp_path / "exburst_conversion.log"),
    )
    summary = converter.convert_all()

    assert summary["ignored"] == 6
    assert summary["converted"] == 2
    assert (output_dir / "EXB-001").exists()
    assert not (output_dir / "EXRP-001").exists()
    assert not (output_dir / "EXBP-001").exists()
    assert not (output_dir / "EXR-001").exists()
    assert not (output_dir / "R-001").exists()
    assert not (output_dir / "RP-001").exists()
    assert (output_dir / "T-001").exists()
    assert (output_dir / "GD99-001").exists()
    report_data = json.loads((tmp_path / "docs" / "exburst_support_latest.json").read_text(encoding="utf-8"))
    reported_ids = {
        card["id"]
        for status_cards in report_data["cards"].values()
        for card in status_cards
    }
    assert "EXB-001" not in reported_ids


def test_exburst_converter_records_unsupported_output_when_llm_fails(tmp_path, monkeypatch):
    raw_path = tmp_path / "exburst_cards.json"
    output_dir = tmp_path / "card_effects_exburst"
    raw_path.write_text(
        json.dumps([_raw_card("GD99-003", "【Deploy】Choose 1 enemy Unit. Rest it.<br>")]),
        encoding="utf-8",
    )

    def _raise_llm_error(*args, **kwargs):
        raise AssertionError("Instructor does not support multiple tool calls")

    monkeypatch.setattr(convert_card_effects, "screen_card", _raise_llm_error)
    monkeypatch.setattr(
        convert_card_effects,
        "load_openrouter_config",
        lambda: OpenRouterConfig(api_key="test-key"),
    )
    converter = ExBurstEffectConverter(
        output_dir=str(output_dir),
        card_database_path=str(raw_path),
        use_llm=True,
        log_file=str(tmp_path / "exburst_conversion.log"),
    )

    summary = converter.convert_all()
    output = json.loads((output_dir / "GD99-003").read_text(encoding="utf-8"))

    assert summary["converted"] == 1
    assert summary["audit"]["unsupported"] == 1
    assert output["metadata"]["support_status"] == "unsupported"
    assert "LLM parser failed" in output["continuous_effects"][0]["unhandled_explanation"]


def test_llm_duration_aliases_are_normalized_before_validation():
    assert GameEffect(duration="INSTANT").duration is None
    assert GameEffect(duration="TURN").duration == "THIS_TURN"
    assert GameEffect(duration="END_OF_TURN").duration == "THIS_TURN"
    assert GameEffect(duration="UNTIL_END_OF_TURN").duration == "THIS_TURN"
    assert GameEffect(duration="DURING_BATTLE").duration == "THIS_BATTLE"


def test_llm_action_duration_aliases_are_normalized_before_ir_validation():
    effect = GameEffect(
        raw_text="【Attack】This Unit gets AP+1 during this battle.",
        trigger="ON_ATTACK",
        actions=[
            {
                "type": "MODIFY_STAT",
                "target": {"selector": "SELF"},
                "stat": "AP",
                "amount": 1,
                "duration": "DURING_BATTLE",
            }
        ],
        is_supported=True,
    )

    effect_data = parsed_card_to_ir(
        "GD99-004",
        parsed_card=ParsedCard(
            name="Training Unit",
            card_type="UNIT",
            effects=[effect],
        ),
        raw_effects=[effect.raw_text],
    )

    assert effect_data["effects"][0]["actions"][0]["duration"] == "THIS_BATTLE"
    assert validate_ir_effect_data(effect_data).is_supported is True


def test_llm_action_aliases_are_normalized_to_runtime_shape():
    effect = GameEffect(
        raw_text="【Deploy】Choose 1 of your Units. It gains【Repair 1】during this turn.",
        trigger="ON_DEPLOY",
        actions=[
            {
                "action_type": "MODIFY_STAT",
                "target_selector": "FRIENDLY_UNIT",
                "amount": 1,
                "stat_type": "REPAIR",
                "duration": "TURN",
            }
        ],
        is_supported=True,
    )

    assert effect.actions == [
        {
            "target": {"selector": "FRIENDLY_UNIT"},
            "duration": "THIS_TURN",
            "type": "GRANT_KEYWORD",
            "keyword": "REPAIR",
            "value": 1,
        }
    ]
    assert validate_ir_effect_data(
        {
            "card_id": "GD99-005",
            "effects": [
                {
                    "effect_id": "GD99-005-E1",
                    "effect_type": "TRIGGERED",
                    "triggers": ["ON_DEPLOY"],
                    "actions": effect.actions,
                    "is_supported": True,
                }
            ],
        }
    ).is_supported is True


def test_llm_dual_timing_trigger_strings_are_normalized_to_trigger_list():
    effect = GameEffect(
        raw_text="【Main】/【Action】Choose 1 friendly Link Unit. It recovers 3 HP.",
        trigger="ACTIVATE_MAIN, ACTIVATE_ACTION",
        actions=[
            {
                "type": "RECOVER_HP",
                "target": {"selector": "FRIENDLY_UNIT", "filters": {"text_contains": "Link Unit"}},
                "amount": 3,
            }
        ],
        is_supported=True,
    )

    effect_data = parsed_card_to_ir(
        "GD01-101",
        ParsedCard(name="Deep Devotion", card_type="COMMAND", effects=[effect]),
        raw_effects=[effect.raw_text],
    )

    assert effect.triggers == ["ACTIVATE_MAIN", "ACTIVATE_ACTION"]
    assert effect_data["effects"][0]["triggers"] == ["ACTIVATE_MAIN", "ACTIVATE_ACTION"]
    assert effect_data["effects"][0]["effect_type"] == "ACTIVATED"
    assert validate_ir_effect_data(effect_data).is_supported is True


def test_llm_underscored_main_action_trigger_is_normalized():
    effect = GameEffect(
        raw_text="【Main】/【Action】Choose 1 enemy Unit with 3 or less HP. Rest it.",
        trigger="MAIN_PHASE_ACTION_PHASE",
        actions=[
            {
                "type": "REST_UNIT",
                "target": {"selector": "ENEMY_UNIT", "filters": {"hp": {"operator": "<=", "value": 3}}},
            }
        ],
        is_supported=True,
    )

    assert effect.triggers == ["MAIN_PHASE", "ACTION_PHASE"]


def test_llm_condition_type_alias_replaces_blank_type():
    effect = GameEffect(
        raw_text="【Action】Choose 1 to 2 enemy Units that are Lv.3 or lower. Return them to their owners' hands.",
        trigger="ACTION_PHASE",
        conditions=[
            {
                "condition_type": "CHECK_STAT",
                "target_selector": "ENEMY_UNIT",
                "stat": "LEVEL",
                "operator": "<=",
                "value": 3,
                "type": "",
            }
        ],
        actions=[
            {
                "type": "RETURN_TO_HAND",
                "target": {"selector": "ENEMY_UNIT"},
                "amount": 2,
            }
        ],
        is_supported=True,
    )

    effect_data = parsed_card_to_ir(
        "GD04-117",
        ParsedCard(name="Graceful Demeanor", card_type="COMMAND", effects=[effect]),
        raw_effects=[effect.raw_text],
    )

    condition = effect_data["effects"][0]["conditions"][0]
    assert condition["type"] == "CHECK_STAT"
    assert condition["target"] == {"selector": "ENEMY_UNIT"}
    assert "condition_type" not in condition
    assert validate_ir_effect_data(effect_data).is_supported is True


def test_burst_activate_action_uses_action_timing():
    effect = GameEffect(
        raw_text="【Burst】Activate this card's 【Action】.",
        trigger="BURST",
        actions=[
            {
                "type": "RESOLVE_COMMAND_EFFECT",
                "timing": "MAIN_PHASE",
                "target": {"selector": "SELF"},
            }
        ],
        is_supported=True,
    )

    effect_data = parsed_card_to_ir(
        "GD04-117",
        ParsedCard(name="Graceful Demeanor", card_type="COMMAND", effects=[effect]),
        raw_effects=[effect.raw_text],
    )

    assert effect_data["effects"][0]["actions"][0]["timing"] == "ACTION_PHASE"


def test_top_level_action_phase_duration_is_timing_not_duration():
    effect = GameEffect(
        raw_text="【Action】Choose 1 to 2 enemy Units that are Lv.3 or lower. Return them to their owners' hands.",
        action_type="RETURN_TO_HAND",
        target_selector="ENEMY_UNIT",
        amount=2,
        duration="ACTION_PHASE",
        conditions=[
            {
                "condition_type": "CHECK_STAT",
                "target_selector": "ENEMY_UNIT",
                "stat": "LEVEL",
                "operator": "<=",
                "value": 3,
            }
        ],
        is_supported=True,
    )

    effect_data = parsed_card_to_ir(
        "GD04-117",
        ParsedCard(name="Graceful Demeanor", card_type="COMMAND", effects=[effect]),
        raw_effects=[effect.raw_text],
    )

    assert effect.duration is None
    assert effect_data["effects"][0]["effect_type"] == "TRIGGERED"
    assert effect_data["effects"][0]["triggers"] == ["ACTION_PHASE"]
    assert effect_data["effects"][0]["actions"][0]["type"] == "RETURN_TO_HAND"
    assert "duration" not in effect_data["effects"][0]["actions"][0]
    assert validate_ir_effect_data(effect_data).is_supported is True


def test_burst_activate_action_phase_duration_becomes_command_timing():
    effect = GameEffect(
        raw_text="【Burst】Activate this card's 【Action】.",
        trigger="BURST",
        action_type="RESOLVE_COMMAND_EFFECT",
        target_selector="SELF",
        duration="ACTION_PHASE",
        is_supported=True,
    )

    effect_data = parsed_card_to_ir(
        "GD04-117",
        ParsedCard(name="Graceful Demeanor", card_type="COMMAND", effects=[effect]),
        raw_effects=[effect.raw_text],
    )

    assert effect.duration is None
    assert effect.timing == "ACTION_PHASE"
    assert effect_data["effects"][0]["triggers"] == ["BURST"]
    assert effect_data["effects"][0]["actions"][0]["timing"] == "ACTION_PHASE"
    assert validate_ir_effect_data(effect_data).is_supported is True


def test_pair_from_trash_action_shape_becomes_explicit_runtime_gap():
    effect = GameEffect(
        raw_text=(
            "During your turn, when you play and activate a (Dawn of Fold) Command card "
            "using an EX Resource, you may pair that card from your trash with one of your Units "
            'with "Gundam Lfrith" in its card name.'
        ),
        trigger="ON_PLAY_FROM_HAND",
        action_type="ON_PAIRED",
        is_supported=True,
    )

    effect_data = parsed_card_to_ir(
        "GD04-021",
        ParsedCard(name="Gundam Lfrith Thorn", card_type="UNIT", effects=[effect]),
        raw_effects=[effect.raw_text],
    )

    assert effect.is_supported is False
    assert effect.unhandled_explanation == "Requires an action to pair a card from trash with a Unit."
    assert effect_data["metadata"]["support_status"] == "unsupported"


def test_pilot_text_is_metadata_not_unsupported_runtime_action():
    raw_text = "【Pilot】(Earth Federation) AP+1 HP+1"
    parsed = ParsedCard(
        name="Pilot Command",
        card_type="COMMAND",
        effects=[GameEffect(raw_text=raw_text, is_supported=False, unhandled_explanation="old parser gap")],
    )

    effect_data = parsed_card_to_ir("GD99-007", parsed, raw_effects=[raw_text])

    assert effect_data["metadata"]["support_status"] == "supported"
    assert effect_data["effects"][0]["effect_type"] == "PILOT_ABILITY"
    assert effect_data["effects"][0]["pilot_stats"] == {"ap": 1, "hp": 1, "traits": ["Earth Federation"]}


def test_cost_modifier_changes_effective_play_cost():
    from simulator.resource_manager import ResourceManager

    card = Card(name="Discount Unit", id="U1", type="UNIT", color="Blue", level=1, cost=3, traits=["CB"])
    player = SimpleNamespace(
        player_id=0,
        resource_area=[object(), object()],
        ex_resources=0,
        _rested_resource_indices=set(),
        active_cost_modifiers=[{"modification": "-1", "filters": {"traits": ["CB"]}}],
    )
    game_state = SimpleNamespace(players=[player])

    assert ResourceManager.get_effective_cost(game_state, 0, card) == 2
    assert ResourceManager.can_play_card(game_state, 0, card) is True


def test_top_level_llm_keyword_action_is_normalized_to_runtime_shape():
    raw_text = "▫️Choose a friendly (G Generation) unit. It gains【Breach 1】until the end of this turn."
    parsed = ParsedCard(
        name="Tallgeese",
        card_type="UNIT",
        effects=[
            GameEffect(
                raw_text=raw_text,
                action_type="GRANT_KEYWORD",
                target_selector="FRIENDLY_UNIT",
                amount=1,
                duration="END_OF_TURN",
                is_supported=True,
            )
        ],
    )

    effect_data = parsed_card_to_ir("EB01-027", parsed, raw_effects=[raw_text])

    assert effect_data["continuous_effects"][0]["actions"] == [
        {
            "type": "GRANT_KEYWORD",
            "target": {"selector": "FRIENDLY_UNIT"},
            "duration": "THIS_TURN",
            "keyword": "BREACH",
            "value": 1,
        }
    ]
    assert validate_ir_effect_data(effect_data).is_supported is True


def test_validator_rejects_malformed_runtime_actions():
    report = validate_ir_effect_data(
        {
            "card_id": "GD99-006",
            "effects": [
                {
                    "effect_id": "GD99-006-E1",
                    "effect_type": "TRIGGERED",
                    "triggers": ["ON_ATTACK"],
                    "actions": [{"type": "GRANT_KEYWORD", "target": {"selector": "SELF"}}],
                    "is_supported": True,
                }
            ],
        }
    )

    assert report.support_status == "partial"
    assert report.issues[0].kind == "missing_keyword"


def test_strict_runtime_modes_fail_closed_for_unknown_ir():
    with pytest.raises(ValueError, match="Unknown action type"):
        ActionExecutor.execute(None, {"type": "UNKNOWN_ACTION"}, strict=True)

    with pytest.raises(ValueError, match="Unknown condition type"):
        ConditionEvaluator.evaluate(None, {"type": "UNKNOWN_CONDITION"}, strict=True)

    assert ActionExecutor.execute(None, {"type": "UNKNOWN_ACTION"}) == "Unknown action type: UNKNOWN_ACTION"
    assert ConditionEvaluator.evaluate(None, {"type": "UNKNOWN_CONDITION"}) is True


def test_return_to_hand_moves_unit_and_paired_pilot_to_owner_hand():
    unit_card = Card(name="Enemy Unit", id="U1", type="UNIT", color="Red", level=1, cost=1, ap=2, hp=2)
    pilot_card = Card(name="Enemy Pilot", id="P1", type="PILOT", color="Red", level=1, cost=1, ap=1, hp=1)
    unit = UnitInstance(unit_card, owner_id=1)
    pilot = PilotInstance(pilot_card, owner_id=1, paired_unit=unit)
    unit.paired_pilot = pilot
    player = SimpleNamespace(hand=[], battle_area=[], bases=[], shield_area=[], trash=[], resource_area=[], main_deck=[])
    opponent = SimpleNamespace(hand=[], battle_area=[unit], bases=[], shield_area=[], trash=[], resource_area=[], main_deck=[])
    context = EffectContext(
        game_state=SimpleNamespace(players=[player, opponent]),
        source_card=None,
        source_player_id=0,
        trigger_event="MAIN_PHASE",
        trigger_data={},
    )

    result = ActionExecutor.execute(context, {"type": "RETURN_TO_HAND", "target": {"selector": "ENEMY_UNIT"}})

    assert result == "Returned 1 card(s) to hand"
    assert opponent.battle_area == []
    assert opponent.hand == [unit_card, pilot_card]


def test_pair_status_target_and_paired_pilot_color_conditions():
    pilot_card = Card(name="White Pilot", id="P1", type="PILOT", color="White", level=1, cost=1, ap=1, hp=1)
    unit = UnitInstance(Card(name="Unit", id="U1", type="UNIT", color="Blue", level=1, cost=1, ap=1, hp=1), owner_id=0)
    unit.paired_pilot = PilotInstance(pilot_card, owner_id=0, paired_unit=unit)
    context = EffectContext(
        game_state=SimpleNamespace(players=[]),
        source_card=unit,
        source_player_id=0,
        trigger_event="ON_ATTACK",
        trigger_data={"target": "PLAYER"},
    )

    assert ConditionEvaluator.evaluate(context, {"type": "CHECK_PAIR_STATUS", "target": {"selector": "SELF"}})
    assert ConditionEvaluator.evaluate(context, {"type": "CHECK_PAIRED_PILOT_COLOR", "color": "White"})
    assert ConditionEvaluator.evaluate(context, {"type": "CHECK_TARGET", "target_type": "PLAYER"})


def test_llm_conditions_and_stat_modifiers_normalize_to_supported_runtime_shape():
    effect = GameEffect(
        raw_text="【Action】If a friendly (G Generation) Unit is in play, choose 1 enemy Unit. It gets AP-3 during this battle.",
        trigger="ACTIVATE_ACTION",
        conditions=[
            {
                "type": "CHECK_TRAIT",
                "trait": "G Generation",
                "selector": "FRIENDLY_UNIT",
                "required": True,
            }
        ],
        actions=[
            {
                "type": "MODIFY_STAT",
                "target": {"selector": "ENEMY_UNIT"},
                "duration": "DURING_BATTLE",
                "modification": "-3",
            }
        ],
        is_supported=True,
    )
    effect_data = parsed_card_to_ir(
        "ST10-015",
        ParsedCard(name="Claire Heathrow", card_type="COMMAND", effects=[effect]),
        raw_effects=[effect.raw_text],
    )

    assert effect_data["effects"][0]["conditions"][0]["target"] == {"selector": "FRIENDLY_UNIT"}
    assert effect_data["effects"][0]["conditions"][0]["traits"] == ["G Generation"]
    assert effect_data["effects"][0]["actions"][0]["stat"] == "AP"
    assert validate_ir_effect_data(effect_data).is_supported is True


def test_known_standalone_keywords_are_supported_continuous_modifiers():
    parsed = ParsedCard(
        name="Sword Strike Gundam",
        card_type="UNIT TOKEN",
        effects=[GameEffect(raw_text="<Blocker> (Rest this Unit to change the attack target to it.)", is_supported=False)],
    )

    effect_data = parsed_card_to_ir("T-010", parsed, raw_effects=[parsed.effects[0].raw_text])

    assert effect_data["metadata"]["support_status"] == "supported"
    assert effect_data["continuous_effects"][0]["modifiers"][0]["keyword"] == "BLOCKER"


def test_suppression_keyword_is_supported_as_continuous_keyword():
    raw_text = "[Suppression] (Damage to Shields by an attack is dealt to the first 2 cards simultaneously.)"
    parsed = ParsedCard(
        name="Gundam X",
        card_type="UNIT",
        effects=[GameEffect(raw_text=raw_text, is_supported=False)],
    )

    effect_data = parsed_card_to_ir("GD02-053", parsed, raw_effects=[raw_text])

    assert effect_data["metadata"]["support_status"] == "supported"
    assert effect_data["continuous_effects"][0]["modifiers"][0]["keyword"] == "SUPPRESSION"


def test_hidden_information_deck_actions_execute_deterministically():
    cards = [
        Card(name="AGE Device", id="C1", type="COMMAND", color="Green", level=1, cost=1, effect=[]),
        Card(name="Other Unit", id="C2", type="UNIT", color="Blue", level=1, cost=1, effect=[]),
        Card(name="Earth Unit", id="C3", type="UNIT", color="Green", level=1, cost=1, traits=["Earth Federation"], effect=[]),
    ]
    player = SimpleNamespace(main_deck=cards.copy(), hand=[], trash=[], shield_area=[], battle_area=[], resource_area=[])
    opponent = SimpleNamespace(main_deck=[], hand=[], trash=[], shield_area=[], battle_area=[], resource_area=[])
    context = EffectContext(
        game_state=SimpleNamespace(players=[player, opponent]),
        source_card=None,
        source_player_id=0,
        trigger_event="ON_LINKED",
        trigger_data={},
    )

    results = ActionExecutor.execute_actions(
        context,
        [
            {"type": "LOOK_AT_DECK", "amount": 3},
            {
                "type": "SELECT_LOOKED_AT_CARD",
                "filters": [
                    {"card_type": "UNIT", "color": "Green", "traits": ["Earth Federation"]},
                    {"name_contains": "AGE Device"},
                ],
                "max_select": 1,
            },
            {"type": "ADD_TO_HAND", "source": "SELECTED_CARD"},
            {"type": "RETURN_LOOKED_TO_BOTTOM"},
        ],
    )

    assert results[1] == "Selected 1 looked-at card(s)"
    assert [card.name for card in player.hand] == ["AGE Device"]
    assert [card.name for card in player.main_deck] == ["Other Unit", "Earth Unit"]


def test_continuous_effects_read_modifiers_key_and_exburst_dirs_are_opt_in(tmp_path):
    stable_dir = tmp_path / "stable"
    exburst_dir = tmp_path / "exburst"
    stable_dir.mkdir()
    exburst_dir.mkdir()
    (exburst_dir / "T-010").write_text(
        json.dumps(
            {
                "card_id": "T-010",
                "effects": [],
                "continuous_effects": [
                    {
                        "effect_id": "T-010-E1",
                        "effect_type": "CONTINUOUS",
                        "conditions": [],
                        "modifiers": [
                            {"type": "GRANT_KEYWORD", "target": {"selector": "SELF"}, "keyword": "BLOCKER"}
                        ],
                        "is_supported": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    unit = UnitInstance(Card(name="Sword Strike", id="T-010", type="UNIT", color="White", level=0, cost=0, ap=1, hp=1), owner_id=0)
    game_state = SimpleNamespace(
        players=[
            SimpleNamespace(battle_area=[unit]),
            SimpleNamespace(battle_area=[]),
        ]
    )

    assert EffectLoader.load_all_effects(str(stable_dir)) == {}
    manager = TriggerManager(effects_dirs=[str(stable_dir), str(exburst_dir)])
    manager.load_effects()
    manager.apply_continuous_effects(game_state)

    assert unit.has_keyword("blocker") is True


def test_audit_helper_groups_non_credit_exburst_issues(tmp_path):
    output_dir = tmp_path / "effects"
    output_dir.mkdir()
    (output_dir / "A-001").write_text(
        json.dumps(
            {
                "card_id": "A-001",
                "metadata": {
                    "support_status": "partial",
                    "validation_issues": [
                        {
                            "kind": "unknown_condition",
                            "value": "CHECK_TRAIT",
                            "message": "Condition is not executed by the runtime",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "A-002").write_text(
        json.dumps(
            {
                "card_id": "A-002",
                "metadata": {
                    "support_status": "unsupported",
                    "validation_issues": [
                        {
                            "kind": "unsupported_llm_effect",
                            "value": "A-002-E1",
                            "message": "LLM parser failed: Error code: 402",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    audit = audit_exburst_outputs(output_dir)

    assert audit["non_credit_issue_count"] == 1
    assert audit["affected_cards"] == ["A-001"]
    assert audit["groups"][0]["kind"] == "unknown_condition"
