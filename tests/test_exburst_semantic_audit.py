import json

from simulator.action_executor import ActionExecutor
from simulator.effect_interpreter import EffectContext, TargetResolver
from simulator.game_manager import GameState, Player
from simulator.resource_manager import ResourceManager
from simulator.trigger_manager import TriggerManager
from simulator.unit import Card, PilotInstance, UnitInstance
from tools.semantic_exburst_audit import (
    audit_card_semantics,
    audit_exburst_semantics,
    build_llm_test_generation_prompt,
    normalize_effect_data,
    validate_llm_test_spec,
)


def test_semantic_audit_flags_legacy_state_condition_without_action_filter():
    card = {
        "card_id": "GD01-008",
        "effects": [
            {
                "effect_id": "GD01-008-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [
                    {
                        "type": "CHECK_CARD_STATE",
                        "target": "ENEMY_UNIT",
                        "value": "RESTED",
                        "operator": "==",
                    }
                ],
                "actions": [
                    {
                        "type": "DAMAGE_UNIT",
                        "amount": 1,
                        "target": {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"},
                    }
                ],
                "metadata": {"raw_text": "【Deploy】Choose 1 rested enemy Unit. Deal 1 damage to it."},
            }
        ],
    }

    issues = audit_card_semantics(card)
    kinds = {issue.kind for issue in issues}

    assert "legacy_check_card_state_value" in kinds
    assert "condition_target_filter_mismatch" in kinds
    assert "target_filter_mismatch" in kinds


def test_normalizer_updates_legacy_state_and_matching_action_filter():
    card = {
        "card_id": "GD01-008",
        "effects": [
            {
                "effect_id": "GD01-008-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [
                    {
                        "type": "CHECK_CARD_STATE",
                        "target": "ENEMY_UNIT",
                        "value": "RESTED",
                        "operator": "==",
                    }
                ],
                "actions": [
                    {
                        "type": "DAMAGE_UNIT",
                        "amount": 1,
                        "target": {"selector": "ENEMY_UNIT"},
                    }
                ],
                "metadata": {"raw_text": "【Deploy】Choose 1 rested enemy Unit. Deal 1 damage to it."},
            }
        ],
    }

    normalized, changes = normalize_effect_data(card)

    assert normalized["effects"][0]["conditions"] == []
    assert normalized["effects"][0]["actions"][0]["target"]["filters"]["state"] == "RESTED"
    assert {change.kind for change in changes} >= {
        "normalized_legacy_card_state",
        "normalized_missing_state_filter",
        "removed_target_qualification_condition",
    }


def test_normalized_qualified_target_ir_resolves_only_valid_runtime_target(tmp_path):
    stale_card = {
        "card_id": "GD01-008",
        "effects": [
            {
                "effect_id": "GD01-008-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [
                    {
                        "type": "CHECK_CARD_STATE",
                        "target": "ENEMY_UNIT",
                        "value": "RESTED",
                        "operator": "==",
                    }
                ],
                "actions": [
                    {
                        "type": "DAMAGE_UNIT",
                        "amount": 1,
                        "target": {"selector": "ENEMY_UNIT"},
                        "damage_type": "EFFECT",
                    }
                ],
                "metadata": {"raw_text": "【Deploy】Choose 1 rested enemy Unit. Deal 1 damage to it."},
            }
        ],
        "continuous_effects": [],
        "metadata": {"support_status": "supported"},
    }
    normalized, _changes = normalize_effect_data(stale_card)
    effects_dir = tmp_path / "effects"
    effects_dir.mkdir()
    (effects_dir / "GD01-008").write_text(json.dumps(normalized), encoding="utf-8")

    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    guntank = UnitInstance(Card("Guntank", "GD01-008", "UNIT", "Blue", 2, 1, 1, 2), owner_id=0)
    active_enemy = UnitInstance(Card("Active Enemy", "ENEMY-A", "UNIT", "Red", 1, 1, 1, 4), owner_id=1)
    rested_enemy = UnitInstance(
        Card("Rested Enemy", "ENEMY-R", "UNIT", "Red", 1, 1, 1, 4),
        owner_id=1,
        is_rested=True,
    )
    game_state.players[1].battle_area = [active_enemy, rested_enemy]

    manager = TriggerManager(effects_dirs=[str(effects_dir)])
    manager.load_effects()
    manager.trigger_event("ON_DEPLOY", game_state, guntank, 0)

    assert active_enemy.current_hp == 4
    assert rested_enemy.current_hp == 3


def test_semantic_audit_checks_target_qualifiers_counts_and_amounts():
    card = {
        "card_id": "GD04-117",
        "effects": [
            {
                "effect_id": "GD04-117-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ACTION_PHASE"],
                "conditions": [],
                "actions": [
                    {
                        "type": "RETURN_TO_HAND",
                        "target": {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"},
                    }
                ],
                "metadata": {
                    "raw_text": "【Action】Choose 1 to 2 enemy Units that are Lv.3 or lower. Return them to their owners' hands."
                },
            }
        ],
    }

    issues = audit_card_semantics(card)
    by_kind = {issue.kind for issue in issues}

    assert "target_filter_mismatch" in by_kind
    assert "target_variable_count_mismatch" in by_kind


def test_normalizer_canonicalizes_legacy_action_shape_and_stat_modifier():
    card = {
        "card_id": "EB01-043",
        "effects": [
            {
                "effect_id": "EB01-043-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_ATTACK"],
                "conditions": [],
                "actions": [
                    {
                        "type": "MODIFY_STAT",
                        "selector": "ENEMY_UNIT",
                        "filters": [{"stat": "LEVEL", "operator": "<=", "value": 5}],
                        "stat": "AP",
                        "modification": -2,
                        "duration": "THIS_BATTLE",
                    }
                ],
                "metadata": {
                    "raw_text": "【Attack】Choose 1 enemy Unit that is Lv.5 or lower. It gets AP-2 during this battle."
                },
            }
        ],
    }

    normalized, changes = normalize_effect_data(card)
    action = normalized["effects"][0]["actions"][1]

    assert normalized["effects"][0]["actions"][0]["type"] == "SELECT_TARGET"
    assert action["target"] == {"selector": "SELECTED_CARD"}
    assert action["modification"] == "-2"
    assert {change.kind for change in changes} >= {
        "normalized_action_shape",
        "normalized_selected_target_workflow",
    }


def test_normalizer_rewrites_invalid_damage_state_and_timing_gate():
    card = {
        "card_id": "GD02-036",
        "effects": [
            {
                "effect_id": "GD02-036-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["WHILE_LINKED"],
                "conditions": [
                    {"type": "CHECK_CARD_STATE", "state": "DAMAGED", "target": {"selector": "SELF"}},
                ],
                "actions": [{"type": "DRAW", "amount": 1}],
                "metadata": {"raw_text": "【During Link】【Attack】If this Unit is damaged, draw 1."},
            }
        ],
    }

    normalized, changes = normalize_effect_data(card)
    effect = normalized["effects"][0]

    assert effect["triggers"] == ["ON_ATTACK"]
    assert {"type": "CHECK_DAMAGE", "target": {"selector": "SELF"}, "operator": ">", "value": 0} in effect["conditions"]
    assert {"type": "CHECK_LINK_STATUS", "target": {"selector": "SELF"}, "is_linked": True} in effect["conditions"]
    assert {change.kind for change in changes} >= {
        "normalized_invalid_card_state",
        "normalized_timing_triggers",
    }


def test_normalizer_wraps_optional_and_success_gated_clauses():
    optional_card = {
        "card_id": "GD99-001",
        "effects": [
            {
                "effect_id": "GD99-001-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [],
                "actions": [{"type": "DRAW", "amount": 1}],
                "metadata": {"raw_text": "【Deploy】You may draw 1."},
            }
        ],
    }
    gated_card = {
        "card_id": "GD99-002",
        "effects": [
            {
                "effect_id": "GD99-002-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [],
                "actions": [{"type": "DRAW", "amount": 1}, {"type": "DISCARD", "amount": 1}],
                "metadata": {"raw_text": "【Deploy】Draw 1. If you do, discard 1."},
            }
        ],
    }

    optional, _ = normalize_effect_data(optional_card)
    gated, _ = normalize_effect_data(gated_card)

    assert optional["effects"][0]["actions"][0]["type"] == "OPTIONAL_ACTION"
    assert gated["effects"][0]["actions"][0]["next_if_success"] == [{"type": "DISCARD", "amount": 1}]


def test_semantic_audit_uses_clause_local_choice_targets():
    card = {
        "card_id": "GD99-010",
        "effects": [
            {
                "effect_id": "GD99-010-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [],
                "actions": [
                    {
                        "type": "SELECT_TARGET",
                        "target": {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"},
                    },
                    {"type": "DAMAGE_UNIT", "target": {"selector": "SELECTED_CARD"}, "amount": 1},
                    {"type": "GRANT_KEYWORD", "target": {"selector": "SELF"}, "keyword": "BLOCKER"},
                ],
                "metadata": {"raw_text": "【Deploy】Choose 1 enemy Unit. Deal 1 damage to it. This Unit gains <Blocker>."},
            }
        ],
    }

    kinds = {issue.kind for issue in audit_card_semantics(card)}

    assert "selected_target_selector_mismatch" not in kinds


def test_normalizer_infers_missing_selected_target_consumers():
    card = {
        "card_id": "EB01-045",
        "effects": [
            {
                "effect_id": "EB01-045-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_PAIRED"],
                "conditions": [],
                "actions": [],
                "metadata": {"raw_text": "【When Paired】Choose 1 enemy Unit with【Repair】. Return it to its owner's hand."},
            }
        ],
    }

    normalized, changes = normalize_effect_data(card)
    actions = normalized["effects"][0]["actions"]

    assert actions == [
        {
            "type": "SELECT_TARGET",
            "target": {
                "selector": "ENEMY_UNIT",
                "selection_method": "CHOOSE",
                "count": 1,
                "filters": {"has_keyword": "repair"},
            },
        },
        {"type": "RETURN_TO_HAND", "target": {"selector": "SELECTED_CARD"}},
    ]
    assert "normalized_selected_target_workflow" in {change.kind for change in changes}


def test_normalizer_rewrites_multi_choice_rest_them_to_selected_cards():
    card = {
        "card_id": "EB01-072",
        "effects": [
            {
                "effect_id": "EB01-072-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_PAIRED"],
                "conditions": [],
                "actions": [{"type": "REST_UNIT", "target": {"selector": "FRIENDLY_UNIT"}}],
                "metadata": {
                    "raw_text": "【When Paired】Choose 1 active friendly Unit with【Blocker】and 1 enemy Unit that is Lv.4 or lower. Rest them."
                },
            }
        ],
    }

    normalized, _changes = normalize_effect_data(card)
    actions = normalized["effects"][0]["actions"]

    assert actions[0]["target"] == {
        "selector": "FRIENDLY_UNIT",
        "selection_method": "CHOOSE",
        "count": 1,
        "filters": {"state": "ACTIVE", "has_keyword": "blocker"},
    }
    assert actions[1]["append"] is True
    assert actions[1]["target"] == {
        "selector": "ENEMY_UNIT",
        "selection_method": "CHOOSE",
        "count": 1,
        "filters": {"level": {"operator": "<=", "value": 4}},
    }
    assert actions[2] == {"type": "REST_UNIT", "target": {"selector": "SELECTED_CARD"}}


def test_target_filters_cover_damaged_link_and_paired_pilot_traits():
    damaged = UnitInstance(Card("Damaged", "U-1", "UNIT", "Blue", 1, 1, 1, 4), owner_id=0, current_hp=2)
    healthy = UnitInstance(Card("Healthy", "U-2", "UNIT", "Blue", 1, 1, 1, 4), owner_id=0)
    linked_card = Card("Linked", "U-3", "UNIT", "Blue", 1, 1, 1, 4, link=["Test Pilot"])
    linked = UnitInstance(linked_card, owner_id=0)
    linked.paired_pilot = PilotInstance(Card("Test Pilot", "P-1", "PILOT", "Blue", 1, 1, 0, 0), owner_id=0)
    trait_paired = UnitInstance(Card("Trait Paired", "U-4", "UNIT", "Blue", 1, 1, 1, 4), owner_id=0)
    trait_paired.paired_pilot = PilotInstance(
        Card("Coordinator", "P-2", "PILOT", "Blue", 1, 1, 0, 0, traits=["ZAFT"]),
        owner_id=0,
    )
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    game_state.players[0].battle_area = [damaged, healthy, linked, trait_paired]
    context = EffectContext(game_state, damaged, 0, "ON_DEPLOY", {})

    assert TargetResolver.resolve_target(context, {"selector": "FRIENDLY_UNIT", "filters": {"damaged": True}}) == [damaged]
    assert TargetResolver.resolve_target(context, {"selector": "FRIENDLY_UNIT", "filters": {"is_linked": True}}) == [linked]
    assert TargetResolver.resolve_target(
        context,
        {"selector": "FRIENDLY_UNIT", "filters": {"paired_pilot_traits": ["ZAFT"]}},
    ) == [trait_paired]


def test_action_executor_runs_next_if_success_and_appends_selected_targets():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    friendly = UnitInstance(Card("Friendly", "U-1", "UNIT", "Blue", 1, 1, 1, 4), owner_id=0)
    enemy = UnitInstance(Card("Enemy", "E-1", "UNIT", "Red", 1, 1, 1, 4), owner_id=1)
    game_state.players[0].battle_area = [friendly]
    game_state.players[1].battle_area = [enemy]
    game_state.players[0].main_deck = [Card("Drawn", "D-1", "COMMAND", "Blue", 1, 1)]
    context = EffectContext(game_state, friendly, 0, "ON_DEPLOY", {})

    results = ActionExecutor.execute_actions(
        context,
        [
            {"type": "DRAW", "amount": 1, "next_if_success": [{"type": "DISCARD", "amount": 1}]},
            {"type": "SELECT_TARGET", "target": {"selector": "FRIENDLY_UNIT"}},
            {"type": "SELECT_TARGET", "target": {"selector": "ENEMY_UNIT"}, "append": True},
            {"type": "REST_UNIT", "target": {"selector": "SELECTED_CARD"}},
        ],
    )

    assert "Player 0 discarded 1 card(s)" in results
    assert friendly.is_rested is True
    assert enemy.is_rested is True


def test_semantic_audit_does_not_require_keyword_grant_for_references():
    card = {
        "card_id": "GD99-011",
        "effects": [
            {
                "effect_id": "GD99-011-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [{"type": "CHECK_KEYWORD", "target": {"selector": "SELECTED_CARD"}, "keyword": "REPAIR"}],
                "actions": [
                    {"type": "SELECT_TARGET", "target": {"selector": "ENEMY_UNIT", "count": 1}},
                    {"type": "DAMAGE_UNIT", "target": {"selector": "SELECTED_CARD"}, "amount": 3},
                ],
                "metadata": {"raw_text": "【Deploy】Choose 1 enemy Unit. If it has <Repair>, deal 3 damage instead."},
            }
        ],
    }

    kinds = {issue.kind for issue in audit_card_semantics(card)}

    assert "keyword_missing_from_ir" not in kinds
    assert "stacking_keyword_missing_value" not in kinds


def test_normalizer_repairs_strict_validation_shapes():
    card = {
        "card_id": "GD99-012",
        "effects": [
            {
                "effect_id": "GD99-012-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "conditions": [{"type": "ON_UNIT_DESTROYED_BY_DAMAGE"}],
                "actions": [
                    {
                        "type": "OPTIONAL_ACTION",
                        "optional_actions": [
                            {
                                "type": "ON_PAIR_PILOT",
                                "target": {"selector": "SELF_HAND", "filters": {"text_contains": "Test Pilot"}},
                                "paired_with": "FRIENDLY_UNIT",
                            }
                        ],
                        "next_if_success": [{"type": "MODIFY_COST", "cost": 0, "target": {"selector": "SELF"}}],
                    }
                ],
                "metadata": {"raw_text": "【Deploy】You may pair 1 Pilot card with \"Test Pilot\" in its card name from your hand with this Unit."},
            }
        ],
        "continuous_effects": [
            {
                "effect_id": "GD99-012-E2",
                "effect_type": "CONTINUOUS",
                "actions": [{"type": "GRANT_KEYWORD", "target": {"selector": "SELF"}, "keyword": None}],
                "metadata": {"raw_text": "【Blocker】(Rest this Unit to change the attack target to it.)"},
            }
        ],
    }

    normalized, changes = normalize_effect_data(card)
    optional = normalized["effects"][0]["actions"][0]

    assert "ON_UNIT_DESTROYED_BY_DAMAGE" in normalized["effects"][0]["triggers"]
    assert normalized["effects"][0]["conditions"] == []
    assert optional["optional_actions"][0]["type"] == "PAIR_PILOT"
    assert optional["next_if_success"][0]["modification"] == "=0"
    assert normalized["continuous_effects"][0]["actions"][0]["keyword"] == "BLOCKER"
    assert {change.kind for change in changes} >= {"normalized_action_shape", "normalized_event_condition"}


def test_pair_pilot_action_pairs_card_from_hand():
    from simulator.action_executor import ActionExecutor
    from simulator.effect_interpreter import EffectContext

    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    unit = UnitInstance(Card("Test Unit", "U-1", "UNIT", "Blue", 1, 1, 2, 3), owner_id=0)
    pilot = Card("Test Pilot", "P-1", "PILOT", "Blue", 1, 1, 1, 1)
    game_state.players[0].battle_area = [unit]
    game_state.players[0].hand = [pilot]
    context = EffectContext(game_state, unit, 0, "ON_DEPLOY", {})

    result = ActionExecutor.execute(
        context,
        {
            "type": "PAIR_PILOT",
            "target": {"selector": "SELF_HAND", "filters": {"card_type": "PILOT", "name_contains": "Test Pilot"}},
            "paired_with": {"selector": "SELF"},
        },
    )

    assert result == "Paired Test Pilot with Test Unit"
    assert unit.paired_pilot is not None
    assert unit.ap == 3
    assert game_state.players[0].hand == []


def test_prevent_set_active_blocks_follow_up_set_active():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    source = UnitInstance(Card("Source", "SRC", "UNIT", "Blue", 1, 1, 1, 3), owner_id=0)
    enemy = UnitInstance(Card("Rested Enemy", "E-1", "UNIT", "Red", 1, 1, 1, 3), owner_id=1, is_rested=True)
    game_state.players[1].battle_area = [enemy]
    context = EffectContext(game_state, source, 0, "ON_PAIRED", {})

    prevent_result = ActionExecutor.execute(
        context,
        {
            "type": "PREVENT_SET_ACTIVE",
            "target": {"selector": "ENEMY_UNIT", "filters": {"state": "RESTED"}},
            "duration": "NEXT_OPPONENT_START_PHASE",
        },
        strict=True,
    )
    set_active_result = ActionExecutor.execute(
        context,
        {"type": "SET_ACTIVE", "target": {"selector": "ENEMY_UNIT"}},
        strict=True,
    )

    assert prevent_result == "Prevented 1 target(s) from being set active"
    assert set_active_result == "Rested Enemy cannot be set active"
    assert enemy.is_rested is True


def test_semantic_audit_accepts_executable_support_keyword_pattern():
    card = {
        "card_id": "GD99-020",
        "effects": [
            {
                "effect_id": "GD99-020-E1",
                "effect_type": "ACTIVATED",
                "triggers": ["ACTIVATE_MAIN"],
                "actions": [
                    {"type": "REST_UNIT", "target": {"selector": "SELF"}},
                    {
                        "type": "MODIFY_STAT",
                        "target": {"selector": "OTHER_FRIENDLY_UNIT"},
                        "stat": "AP",
                        "modification": "+2",
                        "duration": "THIS_TURN",
                    },
                ],
                "metadata": {
                    "raw_text": "【Activate･Main】<Support 2> (Rest this Unit. 1 other friendly Unit gets AP+(specified amount) during this turn.)"
                },
            }
        ],
    }

    kinds = {issue.kind for issue in audit_card_semantics(card)}

    assert "keyword_missing_from_ir" not in kinds


def test_semantic_audit_finds_nested_success_gated_action():
    card = {
        "card_id": "GD99-021",
        "effects": [
            {
                "effect_id": "GD99-021-E1",
                "effect_type": "TRIGGERED",
                "triggers": ["ON_DEPLOY"],
                "actions": [
                    {
                        "type": "OPTIONAL_ACTION",
                        "optional_actions": [
                            {"type": "SELECT_TARGET", "target": {"selector": "SELF_TRASH", "count": 2}},
                            {
                                "type": "EXILE_CARDS",
                                "target": {"selector": "SELECTED_CARD"},
                                "next_if_success": [{"type": "DRAW", "amount": 1}],
                            },
                        ],
                    }
                ],
                "metadata": {
                    "raw_text": "【Deploy】You may choose 2 cards from your trash. Exile them from the game. If you do, draw 1."
                },
            }
        ],
    }

    kinds = {issue.kind for issue in audit_card_semantics(card)}

    assert "if_you_do_not_success_gated" not in kinds


def test_name_alias_from_static_ir_matches_name_filter():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    quattro = Card("Quattro Bajeena", "GD02-098", "PILOT", "Blue", 1, 1)
    game_state.players[0].hand = [quattro]
    context = EffectContext(game_state, quattro, 0, "TEST", {})

    targets = TargetResolver.resolve_target(
        context,
        {"selector": "SELF_HAND", "filters": {"name_contains": "Char Aznable"}},
    )

    assert targets == [quattro]


def test_intrinsic_trash_count_cost_reduction_from_static_ir():
    game_state = GameState()
    game_state.players = {0: Player(0), 1: Player(1)}
    gnx = Card("GN-X", "GD04-075", "UNIT", "Green", 3, 5)
    player = game_state.players[0]
    player.trash = [
        Card("UN Command", "C-1", "COMMAND", "Green", 1, 1, traits=["UN"]),
        Card("Bloc Command", "C-2", "COMMAND", "Green", 1, 1, traits=["Superpower Bloc"]),
        Card("Wrong Type", "C-3", "UNIT", "Green", 1, 1, traits=["UN"]),
    ]

    assert ResourceManager.get_effective_cost(game_state, 0, gnx, zone="HAND") == 3


def test_directory_semantic_audit_includes_baseline_and_grouped_findings(tmp_path):
    effects_dir = tmp_path / "effects"
    effects_dir.mkdir()
    (effects_dir / "GD01-008").write_text(
        json.dumps(
            {
                "card_id": "GD01-008",
                "effects": [
                    {
                        "effect_id": "GD01-008-E1",
                        "effect_type": "TRIGGERED",
                        "triggers": ["ON_DEPLOY"],
                        "conditions": [{"type": "CHECK_CARD_STATE", "target": "ENEMY_UNIT", "value": "RESTED"}],
                        "actions": [{"type": "DAMAGE_UNIT", "amount": 1, "target": {"selector": "ENEMY_UNIT"}}],
                        "metadata": {"raw_text": "【Deploy】Choose 1 rested enemy Unit. Deal 1 damage to it."},
                    }
                ],
                "continuous_effects": [],
                "metadata": {"support_status": "supported"},
            }
        ),
        encoding="utf-8",
    )

    audit = audit_exburst_semantics(effects_dir, normalized_cards_path=None, card_database_dir=None)

    assert audit["total_cards"] == 1
    assert audit["strict_validation"]["supported"] == 1
    assert audit["semantic_issue_count"] >= 2
    assert "GD01-008" in audit["affected_cards"]
    assert audit["groups"]


def test_llm_test_spec_prompt_and_schema_gate():
    prompt = build_llm_test_generation_prompt(
        {"ID": "GD01-008", "Effect": ["【Deploy】Choose 1 rested enemy Unit. Deal 1 damage to it."]},
        {"card_id": "GD01-008", "effects": []},
    )
    assert "Return JSON only" in prompt
    assert "expected_legal_targets" in prompt

    valid_spec = {
        "test_cases": [
            {
                "name": "rested target only",
                "cited_text": "Choose 1 rested enemy Unit.",
                "initial_state": {},
                "action": {},
                "expected_legal_targets": [],
                "expected_state_delta": {},
                "rules_references": ["10-2-2"],
                "unsupported_mechanics": [],
            }
        ]
    }
    invalid_spec = {"test_cases": [{"name": "missing fields", "unsupported_mechanics": ["hidden info"]}]}

    assert validate_llm_test_spec(valid_spec) == []
    assert validate_llm_test_spec(invalid_spec)


def test_essential_cosmetic_cards_are_skipped_by_semantic_audit(tmp_path):
    output_dir = tmp_path / "card_effects_exburst"
    output_dir.mkdir()
    for card_id in ("R-039", "EXB-001", "GD01-008"):
        (output_dir / card_id).write_text(
            json.dumps(
                {
                    "card_id": card_id,
                    "effects": [] if card_id != "GD01-008" else [{"effect_id": f"{card_id}-E1"}],
                    "metadata": {"support_status": "supported" if card_id != "GD01-008" else "partial"},
                }
            ),
            encoding="utf-8",
        )

    audit = audit_exburst_semantics(output_dir, normalized_cards_path=None, card_database_dir=None)

    assert audit["essential_cosmetic_card_count"] == 2
    assert "R-039" not in audit["affected_cards"]
    assert "EXB-001" not in audit["affected_cards"]


def test_build_essential_cosmetic_effect_data_marks_supported():
    from simulator.exburst_essential_cards import (
        build_essential_cosmetic_effect_data,
        is_essential_cosmetic_card_id,
    )

    assert is_essential_cosmetic_card_id("R-039")
    assert is_essential_cosmetic_card_id("R-001-ALT4")
    assert is_essential_cosmetic_card_id("EXBP-003")
    assert not is_essential_cosmetic_card_id("GD01-008")

    effect_data = build_essential_cosmetic_effect_data("RP-001", original_text="(Rest a Resource when paying a cost.)")
    assert effect_data["metadata"]["support_status"] == "supported"
    assert effect_data["metadata"]["essential_cosmetic"] is True
    assert effect_data["effects"] == []
    assert effect_data["continuous_effects"] == []
