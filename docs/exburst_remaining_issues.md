# ExBurst Remaining Audit Issues

This handoff summarizes the remaining findings after the ExBurst semantic audit and fix passes. The latest machine-readable source is `docs/exburst_semantic_audit_latest.json`; the rendered report is `docs/exburst_semantic_audit_latest.md`.

## Current Snapshot

- Total ExBurst IR files audited: 733
- Strict validation status: 622 supported, 7 partial, 104 unsupported
- Strict validation issues: 125
- Remaining semantic issues: 383
- Affected cards: 269
- `card_effects_exburst/` is intended to be git-tracked going forward.

## What Was Fixed

- Removed the `.gitignore` rule that ignored `card_effects_exburst/`.
- Added and ran `tools/semantic_exburst_audit.py` for deterministic semantic auditing.
- Added and used `tools/llm_fix_exburst_ir.py` for grouped OpenRouter-assisted IR fixes.
- Applied deterministic fixes for clear target filters, including state, traits, level, HP, AP, keyword requirements, and `Choose 1 to N` target ranges.
- Applied guarded LLM fixes where output passed IR validation and semantic re-audit gates.
- Rejected LLM proposals that invented unsupported runtime vocabulary such as unsupported filters or condition types.

## Remaining Issue Groups

### `unsupported_llm_effect` - 116

Examples: `EB01-044`, `EXB-001`, `EXB-001-ALT5`, `EXBP-001`, `EXBP-002`, `EXBP-003`, `EXBP-004`, `EXBP-005`.

These are cards or effects marked unsupported by the parser. Many are likely token/resource or mechanics that need either runtime support or explicit unsupported classification cleanup.

Recommended next step: split by card type and mechanic, then decide whether each group should become runtime support, known-pattern parser support, or remain unsupported.

### `timing_trigger_mismatch` - 84

Examples: `EB01-046`, `EB01-070`, `EB01-075`, `EB01-076`, `EB01-084`, `GD01-003`, `GD01-026`, `GD01-066`.

These usually involve printed timing such as `【Main】/【Action】`, `【During Pair】`, `【During Link】`, or static text being represented with incomplete or mismatched triggers.

Recommended next step: define canonical IR for dual timing, continuous gained abilities, and during-pair/link effects before broad auto-fixing.

### `missing_target_action_for_choice` - 83

Examples: `EB01-043`, `EB01-044`, `EB01-045`, `EB01-050`, `EB01-052`, `EB01-065`, `EB01-090`, `GD01-009`.

The printed text has `Choose ...`, but the IR has no target-bearing action that clearly consumes that choice. Some cases are genuine missing actions; others are parser/audit limitations around delayed effects or protection grants.

Recommended next step: add selected-target modeling to the runtime or standardize how chosen cards are stored and referenced across chained actions.

### `selected_target_selector_mismatch` - 64

Examples: `EB01-006`, `EB01-072`, `GD01-015`, `GD01-049`, `GD01-112`, `GD01-124`, `GD01-130`, `GD02-011`.

These are likely cases where later actions broaden from a chosen target to a selector such as `ENEMY_UNIT`, or multi-target choices are represented as separate broad actions.

Recommended next step: introduce a reliable `SELECTED_CARD` workflow or action-local selected target binding before auto-fixing all carry-through cases.

### `invalid_card_state` - 30

Examples: `EB01-017`, `EB01-021`, `EB01-022`, `GD02-002`, `GD02-036`, `GD02-045`, `GD02-046`, `GD02-071`.

These use `CHECK_CARD_STATE` for unsupported values such as destroyed, damaged, shield, trash, or destroyed-by-battle concepts. `ConditionEvaluator` currently supports only active/rested/paired/linked style states.

Recommended next step: model these with supported condition types or add explicit runtime vocabulary for zone, damage, and destruction-cause conditions.

### `keyword_missing_from_ir` - 30

Examples: `GD01-027`, `GD01-046`, `GD01-048`, `GD01-055`, `GD01-066`, `GD01-089`, `GD01-091`, `GD01-108`.

Some are true missing printed keyword grants. Others are token text or choice filters where the keyword is not being granted to the source card.

Recommended next step: separate standalone printed keywords from token-definition keywords and target-filter keywords.

### `stat_modifier_mismatch` - 25

Examples: `GD01-076`, `GD02-014`, `GD02-016`, `GD02-026`, `GD02-031`, `GD02-053`, `GD02-086`, `GD02-090`.

Printed AP/HP changes do not match the action shape or modifier value in IR.

Recommended next step: add deterministic normalization for `gets AP+N`, `gets AP-N`, `gets HP+N`, and pilot stat text, then re-audit.

### Clause Semantics Needing Review

- `then_clause_review`: 15 findings, examples `EXR-001`, `EXR-001-ALT5`, `EXR-002`, `EXRP-002`, `EXRP-003`, `EXRP-004`.
- `if_you_do_not_success_gated`: 12 findings, examples `GD01-003`, `GD01-112`, `GD02-058`, `GD02-069`, `GD02-111`, `GD03-039`.
- `may_effect_not_optional`: 6 findings, examples `GD01-048`, `GD03-079`, `GD03-118`, `GD04-070`, `GD04-090`, `ST06-009`.

These need careful runtime semantics because `If you do`, `Then`, and `you may` differ under rule 5-20 and optional activation rules.

Recommended next step: implement explicit action chaining semantics for success-gated follow-up, unconditional ordered follow-up, and optional action choices.

### Smaller Remaining Groups

- `stacking_keyword_missing_value`: 7 findings. Numeric keywords like Repair, Breach, and Support need values.
- `damage_amount_mismatch`: 6 findings. Printed damage amount differs from IR.
- `target_condition_missing`: 6 findings. Link/paired/damaged target requirements need supported conditions.
- `target_filter_mismatch`: 6 warning findings and 2 fixable findings remain, mostly complex nested structures.
- `draw_amount_mismatch`: 3 findings.
- `unknown_action`: 3 validation findings.
- `malformed_cost_modifier`: 2 validation findings.
- `malformed_stat_modifier`: 2 validation findings.
- `legacy_check_card_state_value`: 1 finding, `ST09-006`, where `value: TRASH` should not be blindly converted to `state`.

## Suggested Carry-Forward Order

1. Add runtime vocabulary for selected-target binding and chained action resolution.
2. Add condition vocabulary for damaged, zone-origin, destroyed, and destroyed-by-battle/effect cases.
3. Normalize timing representation for dual `Main/Action`, `During Pair`, and `During Link`.
4. Re-run deterministic `--fix` and audit.
5. Use grouped LLM calls only after the runtime vocabulary is expressive enough to reject fewer valid cards.

## Commands

```bash
python3 -m tools.semantic_exburst_audit \
  --output-dir card_effects_exburst \
  --normalized-cards exburst_cards_normalized.json \
  --card-database-dir card_database \
  --json-out docs/exburst_semantic_audit_latest.json \
  --markdown-out docs/exburst_semantic_audit_latest.md
```

```bash
python3 -m tools.semantic_exburst_audit \
  --output-dir card_effects_exburst \
  --normalized-cards exburst_cards_normalized.json \
  --card-database-dir card_database \
  --fix
```
