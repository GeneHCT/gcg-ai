# ExBurst IR Condition and Target Mismatch

## Summary

`GD01-008` Guntank exposed a mismatch between parsed effect conditions and action target selection.

Card text:

> `【Deploy】Choose 1 rested enemy Unit. Deal 1 damage to it.`

The stale checked-in ExBurst IR represented `rested enemy Unit` as a standalone condition:

```json
{
  "type": "CHECK_CARD_STATE",
  "target": "ENEMY_UNIT",
  "value": "RESTED",
  "operator": "=="
}
```

but the `DAMAGE_UNIT` action target was only:

```json
{
  "selector": "ENEMY_UNIT"
}
```

This allowed the effect to damage an active enemy unit when target selection picked the first enemy candidate.

## Root Cause

There were two separate issues.

First, the runtime `CHECK_CARD_STATE` evaluator expected `state`, while this LLM-generated IR used `value`. That meant the condition fell through and passed instead of checking `RESTED`.

Second, even a valid condition would only determine whether the effect can resolve. It does not constrain the action target. `DAMAGE_UNIT` independently calls `TargetResolver.resolve_target()` on its own `target` spec, so the rested requirement must be present on the action target as a filter.

Correct action shape:

```json
{
  "type": "DAMAGE_UNIT",
  "amount": 1,
  "target": {
    "selector": "ENEMY_UNIT",
    "count": 1,
    "selection_method": "CHOOSE",
    "filters": {
      "state": "RESTED"
    }
  },
  "damage_type": "EFFECT"
}
```

## Offline Parser Mismatch

The offline parser already has the correct shape for simple “Choose 1 rested enemy Unit. Deal N damage” effects:

```python
if "rested enemy Unit" in text:
    target["filters"] = {"state": "RESTED"}
```

So the current `card_effects_exburst/GD01-008` file was stale or came from a different LLM parse path. This is not just a one-card data bug; it shows the need to audit converted IR where target restrictions were emitted as separate conditions instead of target filters.

## Runtime Safeguard Added

`TriggerManager` now copies compatible `CHECK_CARD_STATE` conditions onto matching action target filters before executing actions. This helps stale IR like:

- condition: `ENEMY_UNIT == RESTED`
- action target: `ENEMY_UNIT`

become effectively:

- action target: `ENEMY_UNIT` with `filters.state = RESTED`

This is a defensive compatibility layer, not the preferred IR shape.

## Follow-Up Work

- Normalize `CHECK_CARD_STATE` to accept both `state` and legacy `value`.
- Audit `card_effects_exburst/` for `CHECK_CARD_STATE` conditions using `value` instead of `state`.
- Audit effects where a condition target and action target share the same selector, especially `ENEMY_UNIT`, `FRIENDLY_UNIT`, or `SELF`, and move true target restrictions into `target.filters`.
- Prefer parser output that encodes “choose a [qualified] target” as target filters rather than effect-level conditions.
- Add validation warnings for `CHECK_CARD_STATE` conditions that refer to broad selectors while the matching action target has no equivalent filter.

