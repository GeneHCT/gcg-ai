# Card Effect Schema - Quick Reference Guide

## Basic Structure

```json
{
  "card_id": "GD01-XXX",
  "effects": [ /* array of effect objects */ ],
  "keywords": [ /* array of keyword objects */ ],
  "continuous_effects": [ /* array of continuous effect objects */ ]
}
```

---

## Effect Types

| Type | Usage |
|------|-------|
| `TRIGGERED` | Effects that activate on game events (Deploy, Attack, Destroyed) |
| `ACTIVATED` | Player-activated abilities with costs |
| `CONTINUOUS` | Always-on effects while condition is true |
| `KEYWORD` | Static keyword abilities |
| `REPLACEMENT` | Effects that change how something happens |

---

## Common Triggers

| Trigger Code | Card Text |
|--------------|-----------|
| `ON_DEPLOY` | 【Deploy】 |
| `ON_DESTROYED` | 【Destroyed】 |
| `ON_ATTACK` | 【Attack】 |
| `ON_BURST` | 【Burst】 |
| `ON_MAIN_PHASE` | 【Main】 |
| `ON_ACTION_PHASE` | 【Action】 |
| `WHILE_LINKED` | 【During Link】 |
| `WHILE_PAIRED` | 【During Pair】 |
| `ON_PAIRED` | 【When Paired】 |
| `ACTIVATE_MAIN` | 【Activate･Main】 |
| `ACTIVATE_ACTION` | 【Activate･Action】 |

---

## Common Conditions

### Count Cards
```json
{
  "type": "COUNT_CARDS",
  "zone": "BATTLE_AREA",
  "owner": "SELF",
  "traits": ["Zeon"],
  "operator": ">=",
  "value": 2
}
```

### Check Stat
```json
{
  "type": "CHECK_STAT",
  "stat": "HP",
  "operator": "<=",
  "value": 3
}
```

### Check Turn
```json
{
  "type": "CHECK_TURN",
  "turn_owner": "SELF"
}
```

### Check Card State
```json
{
  "type": "CHECK_CARD_STATE",
  "state": "RESTED"
}
```

---

## Common Actions

### Draw
```json
{"type": "DRAW", "target": "SELF", "amount": 1}
```

### Damage Unit
```json
{
  "type": "DAMAGE_UNIT",
  "target": {"selector": "ENEMY_UNIT", "count": 1},
  "amount": 2
}
```

### Rest Unit
```json
{
  "type": "REST_UNIT",
  "target": {"selector": "ENEMY_UNIT", "count": 1}
}
```

### Deploy Token
```json
{
  "type": "DEPLOY_TOKEN",
  "token": {
    "name": "Zaku II",
    "traits": ["Zeon"],
    "ap": 1,
    "hp": 1
  },
  "count": 1
}
```

### Grant Keyword
```json
{
  "type": "GRANT_KEYWORD",
  "target": {"selector": "SELF"},
  "keyword": "BREACH",
  "value": 3,
  "duration": "THIS_TURN"
}
```

### Modify Stat
```json
{
  "type": "MODIFY_STAT",
  "target": {"selector": "SELF"},
  "stat": "AP",
  "modification": "+2",
  "duration": "THIS_TURN"
}
```

### Recover HP
```json
{
  "type": "RECOVER_HP",
  "target": {"selector": "SELF"},
  "amount": 2
}
```

### Destroy Card
```json
{
  "type": "DESTROY_CARD",
  "target": {"selector": "ENEMY_UNIT", "count": 1}
}
```

---

## Common Targets

### Self
```json
{"selector": "SELF"}
```

### Single Enemy Unit
```json
{"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"}
```

### All Friendly Units with Trait
```json
{
  "selector": "FRIENDLY_UNIT",
  "selection_method": "ALL",
  "filters": {"traits": ["Zeon"]}
}
```

### Enemy Unit with Low HP
```json
{
  "selector": "ENEMY_UNIT",
  "count": 1,
  "selection_method": "CHOOSE",
  "filters": {"hp": {"operator": "<=", "value": 3}}
}
```

### Variable Count
```json
{
  "selector": "ENEMY_UNIT",
  "variable_count": {"min": 1, "max": 2},
  "selection_method": "CHOOSE"
}
```

---

## Keywords

| Keyword | Value | Description |
|---------|-------|-------------|
| `BLOCKER` | null | Rest to redirect attacks |
| `REPAIR` | X | Recovers X HP at end of turn |
| `BREACH` | X | Damage shields when destroying Units |
| `HIGH_MANEUVER` | null | Can't be blocked |
| `FIRST_STRIKE` | null | Deals damage first in battle |
| `SUPPORT` | X | Rest to give another Unit AP+X |
| `SUPPRESSION` | null | Shield damage hits multiple cards |

---

## Costs

### Resource Cost (①②③)
```json
{"cost_type": "RESOURCE", "amount": 2}
```

### Exile Cost
```json
{
  "cost_type": "EXILE",
  "exile_requirements": {
    "source": "TRASH",
    "filters": {"traits": ["Titans"]},
    "amount": 3
  }
}
```

### Rest Self
```json
{"cost_type": "REST_SELF"}
```

---

## Zones

- `BATTLE_AREA` - Units in play
- `HAND` - Player's hand
- `DECK` - Player's deck
- `TRASH` - Discard pile
- `SHIELD_AREA` - Shield cards
- `EXILE` - Exiled from game
- `RESOURCE_AREA` - Resource cards

---

## Operators

- `>=` - Greater than or equal
- `<=` - Less than or equal
- `==` - Equal to
- `!=` - Not equal to
- `>` - Greater than
- `<` - Less than

---

## Durations

- `PERMANENT` - Lasts forever
- `THIS_TURN` - Until end of turn
- `THIS_BATTLE` - Until end of battle
- `WHILE_CONDITION` - While condition is true

---

## Quick Patterns

### "If you have X, do Y"
```json
{
  "conditions": [{"type": "COUNT_CARDS", ...}],
  "actions": [...]
}
```

### "You may X. If you do, Y"
```json
{
  "actions": [
    {
      "type": "...",
      "optional": true,
      "conditional_next": {
        "if_performed": [...]
      }
    }
  ]
}
```

### "While X, Y"
```json
{
  "effect_type": "CONTINUOUS",
  "conditions": [...],
  "modifications": [...]
}
```

### "【Once per Turn】"
```json
{
  "restrictions": {"once_per_turn": true}
}
```

### "Choose 1 to 2"
```json
{
  "target": {
    "variable_count": {"min": 1, "max": 2}
  }
}
```

### "Deal 1 damage for each X"
```json
{
  "type": "DAMAGE_UNIT",
  "calculation": {
    "type": "PER_COUNT",
    "base": 1,
    "multiplier": {...}
  }
}
```

---

## Translation Guide

### Common Text Patterns

| Card Text | Schema Representation |
|-----------|----------------------|
| "Draw 1" | `{"type": "DRAW", "amount": 1}` |
| "If you have another (Trait)" | `{"type": "COUNT_CARDS", "traits": ["Trait"], "exclude_self": true, "operator": ">=", "value": 1}` |
| "Choose 1 enemy Unit" | `{"selector": "ENEMY_UNIT", "count": 1}` |
| "This Unit gains <Breach 3>" | `{"type": "GRANT_KEYWORD", "keyword": "BREACH", "value": 3}` |
| "during this turn" | `"duration": "THIS_TURN"` |
| "Rest it" | `{"type": "REST_UNIT", "target": ...}` |
| "Deal 2 damage to it" | `{"type": "DAMAGE_UNIT", "amount": 2}` |
| "Deploy 1 token" | `{"type": "DEPLOY_TOKEN", ...}` |
| "Destroy it" | `{"type": "DESTROY_CARD"}` |
| "recovers 2 HP" | `{"type": "RECOVER_HP", "amount": 2}` |
| "gets AP+2" | `{"type": "MODIFY_STAT", "stat": "AP", "modification": "+2"}` |
| "Lv.4 or lower" | `"level": {"operator": "<=", "value": 4}` |
| "3 or less HP" | `"hp": {"operator": "<=", "value": 3}` |
| "While X is in play" | Continuous effect with COUNT_CARDS condition |
| "During your turn" | `{"type": "CHECK_TURN", "turn_owner": "SELF"}` |
| "You may" | `"optional": true` |
| "If you do" | `"conditional_next": {"if_performed": [...]}` |

---

## Validation Checklist

- [ ] All traits match card's Traits field
- [ ] Triggers are from approved list
- [ ] Actions are from approved list
- [ ] Target selectors are valid
- [ ] Operators are valid
- [ ] All required fields present
- [ ] Effect ID is unique
- [ ] Original text preserved in metadata

---

## Common Mistakes to Avoid

❌ **Wrong:** Using trait name not in card data  
✅ **Right:** Use exact trait from card's Traits field

❌ **Wrong:** Missing `exclude_self` when checking "another Unit"  
✅ **Right:** Add `"exclude_self": true`

❌ **Wrong:** Forgetting `selection_method` for targets  
✅ **Right:** Specify "CHOOSE", "RANDOM", or "ALL"

❌ **Wrong:** Using wrong zone (e.g., "FIELD" instead of "BATTLE_AREA")  
✅ **Right:** Use approved zone names

❌ **Wrong:** Missing duration on temporary effects  
✅ **Right:** Add "duration": "THIS_TURN" or "THIS_BATTLE"

❌ **Wrong:** Not handling optional actions properly  
✅ **Right:** Use `"optional": true` with `conditional_next`

---

## Testing Your Conversion

1. **Validate Structure**: Check all required fields present
2. **Check Traits**: Verify traits match card data
3. **Verify Logic**: Ensure conditions/actions match card text
4. **Test Edge Cases**: Check optional chains, variable counts
5. **Compare Similar Cards**: Look for consistency
6. **Human Readable**: Can you read JSON and understand the effect?
