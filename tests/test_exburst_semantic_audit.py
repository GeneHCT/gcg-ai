import json

from simulator.game_manager import GameState, Player
from simulator.trigger_manager import TriggerManager
from simulator.unit import Card, UnitInstance
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
