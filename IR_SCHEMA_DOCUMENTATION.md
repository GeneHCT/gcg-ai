# Intermediate Representation (IR) Schema Documentation

**Version:** 1.0  
**Purpose:** Schema-first card effect system that avoids hard-coding card effects  
**Location:** `card_effects_converted/` directory

---

## Overview

The IR system represents card effects as JSON data structures that the `effect_interpreter.py` and `action_executor.py` process dynamically. This allows:
- Adding new cards without code changes
- AI-assisted effect conversion from text
- Consistent effect resolution
- Easy debugging and validation

**Key Principle:** Card effects are **data, not code**.

---

## File Structure

### Card Effect File Format
**Location:** `card_effects_converted/[CARD_ID]` (no extension)

```json
{
  "card_id": "GD01-007",
  "effects": [ /* Triggered/Activated effects */ ],
  "continuous_effects": [ /* Continuous/static effects */ ],
  "metadata": {
    "original_text": "Original card text in English",
    "complexity_score": 1-5,
    "parsing_version": "1.0",
    "last_updated": "2026-02-07",
    "card_type": "UNIT" | "PILOT" | "COMMAND" | "BASE"
  }
}
```

---

## Effect Types

### 1. TRIGGERED EFFECTS
Effects that activate automatically when specific events occur.

**Maps to Rules:** Rule 10-1-6 (Triggered Effects)

```json
{
  "effect_id": "GD01-007-E1",
  "effect_type": "TRIGGERED",
  "triggers": ["ON_DESTROYED"],
  "restrictions": ["ONCE_PER_TURN"],  // Optional
  "conditions": [ /* Condition objects */ ],
  "actions": [ /* Action objects */ ]
}
```

#### Trigger Types
| Trigger | Rules Reference | Game Event |
|---------|----------------|------------|
| `ON_DEPLOY` | Rule 13-2-6 (【Deploy】) | When card deployed to field |
| `ON_ATTACK` | Rule 13-2-7 (【Attack】) | When Unit declares attack |
| `ON_DESTROYED` | Rule 13-2-8 (【Destroyed】) | When destroyed → trash |
| `ON_PAIRED` | Rule 13-2-9 (【When Paired】) | When Pilot paired with Unit |
| `ON_LINKED` | Rule 13-2-11 (【When Linked】) | When Link condition met |
| `ON_PLAY_FROM_HAND` | Rule 7-5-2 | When played from hand |
| `ON_BATTLE_DAMAGE` | Rule 8-5 | During damage step |
| `ON_DAMAGE_DEALT` | Rule 5-5 | When dealing damage |
| `ON_BURST` | Rule 13-2-5 (【Burst】) | When Shield destroyed |

### 2. ACTIVATED EFFECTS
Effects that players manually activate.

**Maps to Rules:** Rule 10-1-7 (Activated Effects)

```json
{
  "effect_id": "GD01-XXX-E1",
  "effect_type": "ACTIVATED",
  "activation_timing": "MAIN" | "ACTION",  // 【Activate･Main】 or 【Activate･Action】
  "activation_cost": {
    "type": "REST_SELF" | "PAY_COST" | "DISCARD",
    "amount": 1
  },
  "restrictions": ["ONCE_PER_TURN"],  // Optional
  "conditions": [ /* Condition objects */ ],
  "actions": [ /* Action objects */ ]
}
```

#### Activation Timings
- `MAIN`: Rule 13-2-1 (【Activate･Main】) - During Main Phase, not attacking
- `ACTION`: Rule 13-2-2 (【Activate･Action】) - During Action Steps

### 3. CONTINUOUS EFFECTS
Effects that are always active while conditions met.

**Maps to Rules:** Rule 10-1-5 (Constant Effects)

```json
{
  "effect_id": "GD01-001-E1",
  "effect_type": "CONTINUOUS",
  "description": "All your (White Base Team) Units gain <Repair 1>",
  "active_zones": ["BATTLE_AREA", "SHIELD_AREA"],  // Where effect is active
  "conditions": [ /* Optional conditions */ ],
  "modifiers": [
    {
      "type": "GRANT_KEYWORD",
      "target": {
        "selector": "FRIENDLY_UNIT",
        "filters": { "traits": ["White Base Team"] }
      },
      "keyword": "REPAIR",
      "value": 1
    }
  ]
}
```

#### Modifier Types
- `GRANT_KEYWORD`: Grant keyword effect (Repair, Blocker, etc.)
- `MODIFY_STAT`: Modify AP/HP/Cost/Level
- `PREVENT_ACTION`: Prevent attacks, activations, etc.
- `GRANT_ABILITY`: Grant additional effect text

---

## Conditions System

Conditions are checked before effects resolve. All conditions must be true.

**Maps to Rules:** Rule 10-2 (Effect Conditions)

### Condition Types

#### COUNT_CARDS
**Purpose:** Count cards in a zone matching criteria  
**Example:** "If you have 2 or more other Units"

```json
{
  "type": "COUNT_CARDS",
  "zone": "BATTLE_AREA" | "HAND" | "TRASH" | "SHIELD_AREA",
  "owner": "SELF" | "OPPONENT" | "ANY",
  "card_type": "UNIT" | "PILOT" | "COMMAND" | "BASE",
  "traits": ["OZ", "Mobile Suit"],  // Optional
  "trait_operator": "ANY" | "ALL",  // Default: ANY
  "exclude_self": true | false,
  "operator": ">=" | "<=" | "==" | "!=" | ">" | "<",
  "value": 2
}
```

#### CHECK_STAT
**Purpose:** Check a card's stat value  
**Example:** "If this Unit has 5 or more AP"

```json
{
  "type": "CHECK_STAT",
  "target": { /* Target spec, default: SELF */ },
  "stat": "HP" | "AP" | "LEVEL" | "COST",
  "operator": ">=" | "<=" | "==" | "!=" | ">" | "<",
  "value": 5
}
```

#### CHECK_TURN
**Purpose:** Check whose turn it is  
**Example:** "During your turn"

```json
{
  "type": "CHECK_TURN",
  "turn_owner": "SELF" | "OPPONENT"
}
```

#### CHECK_CARD_STATE
**Purpose:** Check if card is in specific state  
**Example:** "If this Unit is rested"

```json
{
  "type": "CHECK_CARD_STATE",
  "target": { /* Target spec, default: SELF */ },
  "state": "ACTIVE" | "RESTED" | "PAIRED" | "LINKED"
}
```

#### CHECK_PLAYER_LEVEL
**Purpose:** Check player's level (resource count)  
**Example:** "If your Lv is 7 or more" (Rule 2-9-4)

```json
{
  "type": "CHECK_PLAYER_LEVEL",
  "player": "SELF" | "OPPONENT",
  "operator": ">=" | "<=" | "==" | ">" | "<",
  "value": 7
}
```

#### CHECK_LINK_STATUS
**Purpose:** Check if Unit is linked  
**Example:** "If this is a Link Unit"

```json
{
  "type": "CHECK_LINK_STATUS",
  "target": "SELF" | { /* Target spec */ },
  "is_linked": true | false
}
```

#### CHECK_PAIRED_PILOT_TRAIT
**Purpose:** Check paired Pilot's traits  
**Example:** "If paired with (Earth Federation) Pilot" (Rule 13-2-10)

```json
{
  "type": "CHECK_PAIRED_PILOT_TRAIT",
  "required_traits": ["Earth Federation"],
  "trait_operator": "ANY" | "ALL"
}
```

#### CHECK_MILLED_TRAITS
**Purpose:** Check traits of recently milled cards  
**Example:** "If the milled card has (Zeon) trait"

```json
{
  "type": "CHECK_MILLED_TRAITS",
  "traits": ["Zeon"],
  "count": ">=1"  // String format: operator + number
}
```

#### CHECK_CARD_NAME_SUBSTRING
**Purpose:** Check if card name contains substring  
**Example:** "Unicorn Mode" in card name (Rule 2-2-3)

```json
{
  "type": "CHECK_CARD_NAME_SUBSTRING",
  "substring": "Unicorn Mode"
}
```

---

## Actions System

Actions are executed when effect resolves.

**Maps to Rules:** Effects execute actions in order (Rule 1-3-7)

### Action Types

#### DRAW
**Purpose:** Draw cards  
**Rules:** Rule 5-14 (Draw), Rule 7-3 (Draw Phase)

```json
{
  "type": "DRAW",
  "target": "SELF" | "OPPONENT",
  "amount": 1
}
```

#### DAMAGE_UNIT
**Purpose:** Deal effect damage to Unit/Base  
**Rules:** Rule 5-5-4 (Effect Damage)

```json
{
  "type": "DAMAGE_UNIT",
  "target": { /* Target spec */ },
  "amount": 3,
  // OR for calculated damage:
  "calculation": {
    "type": "FIXED" | "PER_STAT",
    "base": 1,
    "multiplier": {
      "stat": "AP" | "HP",
      "source": "SELF",
      "divisor": 2
    }
  }
}
```

#### REST_UNIT
**Purpose:** Rest a Unit/Base  
**Rules:** Rule 5-4 (Active and Rested)

```json
{
  "type": "REST_UNIT",
  "target": {
    "count": 1,
    "selection_method": "CHOOSE" | "RANDOM" | "ALL",
    "selector": "ENEMY_UNIT" | "FRIENDLY_UNIT" | "OTHER_FRIENDLY_UNIT",
    "filters": { /* Optional filters */ }
  }
}
```

#### SET_ACTIVE
**Purpose:** Set card to active (unrest)  
**Rules:** Rule 5-4, Rule 7-2-3 (Active Step)

```json
{
  "type": "SET_ACTIVE",
  "target": { /* Target spec */ }
}
```

#### MODIFY_STAT
**Purpose:** Modify AP/HP temporarily or permanently  
**Rules:** Rule 2-7 (AP), Rule 2-8 (HP)

```json
{
  "type": "MODIFY_STAT",
  "target": { /* Target spec */ },
  "stat": "AP" | "HP" | "COST" | "LEVEL",
  "modification": "+2" | "-1" | "=5",
  "duration": "THIS_TURN" | "THIS_BATTLE" | "PERMANENT"
}
```

#### RECOVER_HP
**Purpose:** Heal damage on Unit/Base  
**Rules:** Rule 5-6 (HP Recovery)

```json
{
  "type": "RECOVER_HP",
  "target": { /* Target spec */ },
  "amount": 2
}
```

#### GRANT_KEYWORD
**Purpose:** Grant keyword effect to Unit  
**Rules:** Rule 13-1 (Keyword Effects)

```json
{
  "type": "GRANT_KEYWORD",
  "target": { /* Target spec */ },
  "keyword": "REPAIR" | "BREACH" | "SUPPORT" | "BLOCKER" | "FIRST_STRIKE" | "HIGH_MANEUVER" | "SUPPRESSION",
  "value": 1,  // For keywords with values (Repair, Breach, Support)
  "duration": "THIS_TURN" | "THIS_BATTLE" | "PERMANENT"
}
```

#### DESTROY_CARD
**Purpose:** Destroy Unit/Base  
**Rules:** Rule 5-10 (Destroy)

```json
{
  "type": "DESTROY_CARD",
  "target": { /* Target spec */ }
}
```

#### DEPLOY_TOKEN
**Purpose:** Create token Unit/Base  
**Rules:** Rule 5-17 (Tokens)

```json
{
  "type": "DEPLOY_TOKEN",
  "token": {
    "name": "Bit",
    "ap": 3,
    "hp": 2,
    "traits": ["Bit"],
    "keywords": [
      { "keyword": "BLOCKER" }
    ]
  },
  "count": 1,
  "state": "ACTIVE" | "RESTED"
}
```

#### PLACE_RESOURCE
**Purpose:** Place Resource from resource deck  
**Rules:** Rule 7-4 (Resource Phase), Rule 5-17-3-2 (EX Resource)

```json
{
  "type": "PLACE_RESOURCE",
  "resource_type": "NORMAL" | "EX",
  "state": "ACTIVE" | "RESTED"
}
```

#### SHIELD_TO_HAND
**Purpose:** Add Shield to hand  
**Rules:** Rule 4-6-4 (Shield Section)

```json
{
  "type": "SHIELD_TO_HAND",
  "amount": 1
}
```

#### ADD_TO_SHIELDS
**Purpose:** Add cards from hand/deck to shields  
**Rules:** Rule 4-6-4 (Shield Section)

```json
{
  "type": "ADD_TO_SHIELDS",
  "source": "HAND" | "DECK",
  "count": 1,
  "selection_method": "CHOOSE" | "RANDOM"
}
```

#### MILL
**Purpose:** Move cards from deck to trash  
**Rules:** Card moves between locations (Rule 4-1-5)

```json
{
  "type": "MILL",
  "target": "SELF" | "OPPONENT",
  "amount": 3,
  "destination": "TRASH"
}
```

#### DEPLOY_FROM_ZONE
**Purpose:** Deploy Unit/Base from non-hand zone  
**Rules:** Rule 5-7-1-1 (Play from other locations)

```json
{
  "type": "DEPLOY_FROM_ZONE",
  "source_zone": "TRASH" | "BANISH" | "DECK",
  "target": {
    "card_type": "UNIT",
    "filters": {
      "level": { "operator": "<=", "value": 3 }
    }
  },
  "pay_cost": true | false,
  "destination": "BATTLE_AREA"
}
```

#### EXILE_CARDS
**Purpose:** Remove cards from game (banish)  
**Rules:** Rule 5-12 (Remove)

```json
{
  "type": "EXILE_CARDS",
  "source_zone": "TRASH" | "HAND" | "DECK",
  "target": {
    "card_type": "UNIT",
    "count": 1,
    "filters": { /* Optional filters */ }
  },
  "destination": "BANISH"
}
```

#### GRANT_ATTACK_TARGETING
**Purpose:** Allow attacking active Units or special targets  
**Rules:** Rule 8-2-1 (Attack target normally: player or rested Unit)

```json
{
  "type": "GRANT_ATTACK_TARGETING",
  "target": { "selector": "SELF" },
  "target_restrictions": {
    "state": "ACTIVE",  // Can attack active Units
    "level": { "operator": "<=", "value": 4 }
  },
  "duration": "THIS_TURN",
  "description": "This Unit can attack active enemy Units"
}
```

#### GRANT_PROTECTION
**Purpose:** Prevent damage or effects  
**Rules:** Rule 10-2-3 (Effects restricted by other effects)

```json
{
  "type": "GRANT_PROTECTION",
  "target": "SELF" | "SELF_SHIELDS" | { /* Target spec */ },
  "protection_type": "PREVENT_DAMAGE" | "PREVENT_EFFECTS",
  "source_filter": { /* Optional: only prevent from certain sources */ },
  "duration": "THIS_TURN" | "THIS_BATTLE"
}
```

#### CONDITIONAL_BRANCH
**Purpose:** If-then logic with multiple branches  
**Rules:** Rule 5-20 ("If you do" vs "Then")

```json
{
  "type": "CONDITIONAL_BRANCH",
  "conditions": [
    {
      "if": { /* Condition object */ },
      "then": { /* Action object */ }
    }
  ]
}
```

#### OPTIONAL_ACTION
**Purpose:** "You may" effects  
**Rules:** Rule 10-1-3 ("you may" effects)

```json
{
  "type": "OPTIONAL_ACTION",
  "optional_actions": [ /* Actions if chosen */ ],
  "next_if_success": [ /* Actions if performed */ ]
}
```

#### OVERRIDE_PLAY_COST
**Purpose:** Reduce/override play cost  
**Rules:** Rule 2-9 (Lv), Rule 2-10 (Cost)

```json
{
  "type": "OVERRIDE_PLAY_COST",
  "cost": 0,
  "level": 0
}
```

---

## Target Specification System

**Purpose:** Flexibly select targets for actions/conditions

### Target Spec Structure
```json
{
  "selector": "ENEMY_UNIT",
  "count": 1,
  "variable_count": { "min": 1, "max": 3 },  // Optional, for "up to X"
  "selection_method": "CHOOSE" | "RANDOM" | "ALL",
  "filters": {
    "traits": ["Zeon"],
    "trait_operator": "ANY" | "ALL",
    "card_type": "UNIT" | "PILOT",
    "level": { "operator": "<=", "value": 3 },
    "hp": { "operator": ">=", "value": 5 },
    "ap": { "operator": ">", "value": 7 },
    "state": "ACTIVE" | "RESTED",
    "is_token": true | false,
    "has_keyword": "BLOCKER" | "REPAIR" | etc.
  }
}
```

### Selectors

#### Self-Referential
- `SELF`: The source card
- `PAIRED_PILOT`: Pilot paired with this Unit

#### Friendly
- `FRIENDLY_UNIT`: All your Units
- `OTHER_FRIENDLY_UNIT`: Your Units except self
- `FRIENDLY_BASE`: Your Base(s)
- `FRIENDLY_RESOURCE`: Your Resources
- `SELF_HAND`: Your hand
- `SELF_TRASH`: Your trash
- `SELF_SHIELDS`: Your shield section

#### Enemy
- `ENEMY_UNIT`: Opponent's Units
- `ENEMY_BASE`: Opponent's Base(s)
- `ENEMY_PLAYER`: The opponent
- `OPPONENT_HAND`: Opponent's hand
- `OPPONENT_TRASH`: Opponent's trash
- `OPPONENT_SHIELDS`: Opponent's shield section

#### Contextual (from trigger data)
- `BATTLING_UNIT`: Unit being battled
- `LOOKED_AT_CARD`: Card from look/search effect

### Selection Methods
- `CHOOSE`: Player chooses (TODO: integrate with agent)
- `RANDOM`: Random selection
- `ALL`: Select all matching targets

---

## Advanced Patterns

### "If you do" Sequencing
**Rules:** Rule 5-20

```json
{
  "actions": [
    {
      "type": "DESTROY_CARD",
      "target": { "selector": "SELF" },
      "conditional_next": {
        "if_performed": [
          { "type": "DRAW", "amount": 2 }
        ]
      }
    }
  ]
}
```

### "Then" Sequencing
**Rules:** Rule 5-20

```json
{
  "actions": [
    { "type": "MILL", "amount": 3 },
    { "type": "DRAW", "amount": 1 }  // Happens even if mill fails
  ]
}
```

### Once Per Turn Restriction
**Rules:** Rule 13-2-13

```json
{
  "effect_type": "TRIGGERED",
  "restrictions": ["ONCE_PER_TURN"],
  "triggers": ["ON_ATTACK"]
}
```

### Multiple Triggers
**Example:** Effect that triggers on multiple events

```json
{
  "effect_type": "TRIGGERED",
  "triggers": ["ON_DEPLOY", "ON_PAIRED"],
  "actions": [ /* Same actions for both triggers */ ]
}
```

### Keyword Stacking
**Rules:** Rule 13-1 (some stack, some don't)

```json
// Repair stacks (adds values) - Rule 13-1-1-2
{ "type": "GRANT_KEYWORD", "keyword": "REPAIR", "value": 2 }

// Blocker doesn't stack - Rule 13-1-4-2
{ "type": "GRANT_KEYWORD", "keyword": "BLOCKER" }
```

---

## Implementation Notes

### Effect Resolution Flow
1. **Trigger Event** occurs in game
2. **TriggerManager** identifies cards with matching triggers
3. **ConditionEvaluator** checks all conditions
4. If conditions pass, **ActionExecutor** executes actions in sequence
5. **Rules Management** checks for state-based actions

### Agent Integration Points
- `selection_method: "CHOOSE"` → Agent decision
- `optional: true` → Agent decision
- `variable_count` → Agent chooses count

### Performance Considerations
- Effects loaded once at startup via `EffectLoader.load_all_effects()`
- Target resolution uses filtered candidates (not full search)
- Conditions short-circuit on first failure

---

## Validation Checklist

When creating new card effects:

- [ ] **Trigger mapping:** Trigger type matches rule keyword (ON_DEPLOY = 【Deploy】)
- [ ] **Condition accuracy:** All "if" clauses converted to conditions
- [ ] **Action order:** Actions execute in card text order (Rule 1-3-7)
- [ ] **"If you do" vs "Then":** Use `conditional_next` for "If you do" (Rule 5-20)
- [ ] **Targeting valid:** Target selector matches card text
- [ ] **Restrictions:** Add `ONCE_PER_TURN` if specified
- [ ] **Keyword stacking:** Check Rule 13-1 for stacking rules
- [ ] **Duration:** Specify duration for temporary effects
- [ ] **Original text:** Include full card text in metadata

---

## Example: Complete Card Effect

**Card:** GD01-007  
**Text:** "【Destroyed】If you have another (OZ) Unit in play, draw 1."

```json
{
  "card_id": "GD01-007",
  "effects": [
    {
      "effect_id": "GD01-007-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_DESTROYED"],
      "conditions": [
        {
          "type": "COUNT_CARDS",
          "zone": "BATTLE_AREA",
          "owner": "SELF",
          "card_type": "UNIT",
          "traits": ["OZ"],
          "exclude_self": true,
          "operator": ">=",
          "value": 1
        }
      ],
      "actions": [
        {
          "type": "DRAW",
          "target": "SELF",
          "amount": 1
        }
      ]
    }
  ],
  "metadata": {
    "original_text": "【Destroyed】If you have another (OZ) Unit in play, draw 1.",
    "complexity_score": 2,
    "parsing_version": "1.0",
    "last_updated": "2026-02-07",
    "card_type": "UNIT"
  }
}
```

---

## References

- **Game Rules:** `gamerules.txt` (Ver. 1.5.0)
- **Quick Reference:** `GAME_RULES_QUICK_REFERENCE.md`
- **TCG Logic Rules:** `.cursor/rules/tcg-logic.md`
- **Implementation:**
  - `simulator/effect_interpreter.py` - Target resolution, condition evaluation
  - `simulator/action_executor.py` - Action execution
  - `simulator/trigger_manager.py` - Event triggering
  - `card_effects_converted/` - Card effect JSON files

---

## Future Enhancements

- [ ] Validation tool for IR JSON files
- [ ] Effect simulator/tester
- [ ] AI-assisted text-to-IR converter
- [ ] Visual effect editor
- [ ] Performance profiling for complex effects
- [ ] Effect debugging/tracing mode
