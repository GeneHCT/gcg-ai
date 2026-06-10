# ExBurst Remaining Audit Issues

This handoff summarizes the remaining findings after the ExBurst semantic audit and fix passes. The latest machine-readable source is `docs/exburst_semantic_audit_latest.json`; the rendered report is `docs/exburst_semantic_audit_latest.md`.

## Game-Essential Cosmetic Cards (Excluded)

EX bases (`EXB-*`, `EXBP-*`), EX resources (`EXR-*`, `EXRP-*`), and standard resources (`R-*`, `RP-*`) are game-essential cosmetics. Their setup and payment behavior is handled by engine rules, not card-effect IR.

These cards are:

- Written as supported stubs with `parser_source: essential_cosmetic` during conversion
- Skipped by semantic audit and LLM fix batches
- Not queued for LLM review or test-generation prompts

## Current Snapshot

- Total ExBurst IR files audited: 733 (105 essential-cosmetic cards excluded from semantic audit)
- Strict validation status: 732 supported, 0 partial, 1 unsupported (after essential-cosmetic normalization)
- Metadata support status: 725 supported, 7 partial, 1 unsupported
- Strict validation issues: 1 (excluding essential-cosmetic cards)
- Remaining semantic issues: 0
- Affected cards: 0
- `card_effects_exburst/` is intended to be git-tracked going forward.

## What Was Fixed

- Removed the `.gitignore` rule that ignored `card_effects_exburst/`.
- Added and ran `tools/semantic_exburst_audit.py` for deterministic semantic auditing.
- Added and used `tools/llm_fix_exburst_ir.py` for grouped OpenRouter-assisted IR fixes.
- Applied deterministic fixes for clear target filters, including state, traits, level, HP, AP, keyword requirements, and `Choose 1 to N` target ranges.
- Applied guarded LLM fixes where output passed IR validation and semantic re-audit gates.
- Rejected LLM proposals that invented unsupported runtime vocabulary such as unsupported filters or condition types.
- Added general `SELECT_TARGET` runtime support that stores chosen public targets for `SELECTED_CARD` follow-up actions.
- Added `CHECK_DAMAGE` and broader condition target evaluation for damaged/existence-style checks.
- Normalized legacy action shapes, target filters, AP/HP modifiers, keyword grants, dual timing, during-pair/link gates, optional actions, and simple `If you do` chains.
- Added `PAIR_PILOT` runtime support for effect-based Pilot pairing from hand/trash and normalized legacy `ON_PAIR_PILOT` action shapes.
- Added executable `COUNT_CARDS` support for count-result damage and dynamic stat modifiers based on counted zones.
- Made semantic target auditing clause-local so follow-up actions are not compared against an unrelated earlier `Choose ...` phrase.
- Separated true printed keyword grants from keyword references such as target filters or "has <Repair>" checks.
- Added deterministic `SELECT_TARGET` normalization for direct "Choose ... it/them ..." actions such as return-to-hand, rest, stat modification, damage, HP recovery, and keyword grants.
- Added count-aware selected-target binding for multi-choice "Rest them" effects, including runtime accumulation of multiple selected targets.
- Added target-local runtime/validation filters for damaged Units, Link Units, and Units paired with a Pilot of a printed trait.
- Made `next_if_success` executable in the main action loop so normalized `If you do` branches run under rule 5-20.
- Reduced `selected_target_selector_mismatch` findings from 30 to 3 by aligning existing `SELECT_TARGET` actions, skipping activation costs and attack-target permission text, and rewriting clear pronoun consumers to `SELECTED_CARD`.

## Remaining Issue Groups

### Strict Validation Gaps - 1

Current validation groups:

- `unsupported_llm_effect`: 1 finding, example `EB01-044`.

All malformed action/condition validation gaps have been normalized or given runtime support. The remaining validation issue is an effect still explicitly marked unsupported by the LLM parser: most-units-owner targeting.

## Suggested Carry-Forward Order

1. Decide whether the remaining unsupported LLM effect needs new runtime vocabulary or should remain explicitly unsupported.
2. Keep using the semantic audit after parser changes; all executable semantic groups are currently clear.

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
