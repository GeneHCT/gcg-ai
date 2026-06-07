# ExBurst LLM Rerun Summary

Latest 104-card LLM rerun result:

- Supported: 88
- Partial: 9
- Unsupported: 7

## Partial Cards

Mostly parser-shape cleanup remains:

- `GD01-002`, `ST10-014`: malformed `MODIFY_COST`; LLM emitted `cost` or `amount` instead of required `modification`.
- `GD03-107`: LLM emitted `COUNT_CARDS` as an action instead of a condition or calculation.
- `GD03-120`: condition emitted as trigger-like `ON_UNIT_DESTROYED_BY_DAMAGE`.
- `GD04-002`, `GD04-035`: empty nested optional action.
- `GD04-057`: variable AP reduction from trash count needs normalized dynamic stat modifier shape.
- `GD04-070`: `ON_PAIR_PILOT` emitted as an action instead of trigger or metadata.
- `GD04-117`: blank condition object.

## Unsupported Cards

These are either true mechanics gaps or LLM parse failures:

- `EB01-044`: needs “most numerous enemy player owner” target selection; also missing keyword recovery.
- `GD02-098`: true runtime gap: name alias modifier.
- `GD04-075`: true runtime/parser gap: cost reduction based on trash count with trait filter.
- `GD01-101`, `GD02-102`, `GD03-104`, `GD04-021`: LLM parser validation failures (`InstructorRetryException`), likely recoverable by broadening Pydantic/normalizer tolerance.

## Takeaway

The rerun is a strong improvement. Remaining partials are mostly deterministic normalizer fixes; unsupported is down to a few real mechanics plus four LLM schema rejection cases.
