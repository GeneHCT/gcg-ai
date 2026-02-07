# Gundam Card Game - Card Effect JSON Schema Proposal

## Executive Summary

This document proposes a comprehensive JSON schema for converting Gundam Card Game card effects from human-readable text into machine-readable format. The schema is designed to handle the current 474 cards with effects and be extensible for future card releases.

**Statistics:**
- Total cards analyzed: 564
- Cards with effects: 474 (84%)
- Cards without effects: 90 (16%)

---

## Schema Design Philosophy

### Core Principles

1. **Modularity**: Effects are composed of reusable building blocks (triggers, conditions, actions, targets)
2. **Extensibility**: New trigger types, conditions, and actions can be added without breaking existing cards
3. **Explicit over Implicit**: All game rules and interactions must be explicitly defined
4. **Validation-Ready**: Schema enables validation of effect legality before execution
5. **Future-Proof**: Supports unknown future mechanics through flexible structure

### Key Architectural Decisions

1. **Multiple Effects Per Card**: Each card can have multiple independent effect objects
2. **Effect Chaining**: Support for "If you do" chains and sequential actions
3. **Optional Actions**: "You may" effects are handled via `optional: true` flag
4. **Replacement Effects**: Special handling for cost modification and replacement effects
5. **Continuous Effects**: State-based effects that continuously check conditions

---

## Top-Level Schema Structure

```json
{
  "card_id": "GD01-007",
  "effects": [
    {
      "effect_id": "GD01-007-E1",
      "effect_type": "TRIGGERED",
      "triggers": [...],
      "conditions": [...],
      "actions": [...],
      "restrictions": {...},
      "metadata": {...}
    }
  ],
  "keywords": [...],
  "continuous_effects": [...]
}
```

---

## Effect Types

### 1. TRIGGERED
Effects that activate in response to specific game events.

**Example:** 【Destroyed】Draw 1.

### 2. ACTIVATED
Effects that require player activation and usually have costs.

**Example:** 【Activate･Main】②：Deal 1 damage to 1 enemy Unit.

### 3. CONTINUOUS
Effects that apply while a condition is true.

**Example:** While a friendly white Base is in play, this Unit gains <Repair 1>.

### 4. KEYWORD
Static abilities represented by keywords.

**Example:** <Blocker>, <Repair 1>, <Breach 3>

### 5. REPLACEMENT
Effects that replace how something happens.

**Example:** Play this card as if it has 0 Lv. and cost.

---

## Trigger System

### Primary Triggers

| Trigger Code | Description | Example |
|--------------|-------------|---------|
| `ON_PLAY` | When card is played from hand (before Deploy) | "When playing this card from your hand..." |
| `ON_DEPLOY` | When card enters the battle area | 【Deploy】 |
| `ON_ATTACK` | When this Unit attacks | 【Attack】 |
| `ON_DESTROYED` | When this Unit is destroyed | 【Destroyed】 |
| `ON_BURST` | When this card is burst from shield area | 【Burst】 |
| `ON_MAIN_PHASE` | Main phase effect | 【Main】 |
| `ON_ACTION_PHASE` | Action phase effect | 【Action】 |

### Pairing/Linking Triggers

| Trigger Code | Description | Example |
|--------------|-------------|---------|
| `ON_PAIRED` | When this Unit pairs with a Pilot | 【When Paired】 |
| `ON_LINKED` | When this Unit links with a Pilot | 【When Linked】 |
| `WHILE_PAIRED` | While this Unit has a paired Pilot | 【During Pair】 |
| `WHILE_LINKED` | While this Unit has a linked Pilot | 【During Link】 |

### Event Triggers

| Trigger Code | Description | Example |
|--------------|-------------|---------|
| `ON_UNIT_DESTROYED_BY_SELF` | When this Unit destroys another Unit | "When this Unit destroys an enemy Unit..." |
| `ON_UNIT_DESTROYED_BY_ANY` | When any Unit destroys another Unit | "When one of your Units destroys..." |
| `ON_BATTLE_DAMAGE_DEALT` | When this Unit deals battle damage | "When this Unit deals battle damage..." |
| `ON_SHIELD_DESTROYED` | When this Unit destroys a shield | "When this Unit destroys an enemy shield..." |
| `ON_HP_RECOVERED` | When this Unit recovers HP | "When this Unit recovers HP..." |
| `ON_RESTED_BY_EFFECT` | When this Unit is rested by an effect | "When this Unit is rested by an opponent's effect..." |
| `ON_EFFECT_DAMAGE_RECEIVED` | When this Unit receives effect damage | "When this Unit receives effect damage..." |

### Combined Triggers

Triggers can be combined. Examples:
- 【During Link】【Attack】 = `["WHILE_LINKED", "ON_ATTACK"]`
- 【During Pair】【Destroyed】 = `["WHILE_PAIRED", "ON_DESTROYED"]`

---

## Condition System

### Condition Structure

```json
{
  "type": "CONDITION_TYPE",
  "parameters": {...},
  "operator": ">=|<=|==|!=|>|<",
  "value": 1,
  "negate": false
}
```

### Card Count Conditions

#### COUNT_CARDS
Count cards in a specific zone.

```json
{
  "type": "COUNT_CARDS",
  "zone": "BATTLE_AREA|TRASH|HAND|DECK|SHIELD_AREA",
  "owner": "SELF|OPPONENT|ANY",
  "card_type": "UNIT|PILOT|COMMAND|BASE",
  "traits": ["Zeon", "Neo Zeon"],
  "trait_operator": "ANY|ALL",
  "level": {"operator": "<=", "value": 4},
  "exclude_self": true,
  "operator": ">=",
  "value": 1
}
```

**Example:** "If you have another (OZ) Unit in play"
```json
{
  "type": "COUNT_CARDS",
  "zone": "BATTLE_AREA",
  "owner": "SELF",
  "traits": ["OZ"],
  "exclude_self": true,
  "operator": ">=",
  "value": 1
}
```

### Stat Conditions

#### CHECK_STAT
Check a Unit's stats.

```json
{
  "type": "CHECK_STAT",
  "target": "TARGET_SELECTOR",
  "stat": "HP|AP|LEVEL|COST",
  "operator": "<=|>=|==|!=|<|>",
  "value": 3
}
```

**Example:** "Enemy Unit with 5 or less HP"
```json
{
  "type": "CHECK_STAT",
  "stat": "HP",
  "operator": "<=",
  "value": 5
}
```

### Game State Conditions

#### CHECK_PLAYER_LEVEL
```json
{
  "type": "CHECK_PLAYER_LEVEL",
  "player": "SELF|OPPONENT",
  "operator": ">=",
  "value": 6
}
```

#### CHECK_TURN
```json
{
  "type": "CHECK_TURN",
  "turn_owner": "SELF|OPPONENT"
}
```

#### CHECK_BATTLE_STATE
```json
{
  "type": "CHECK_BATTLE_STATE",
  "state": "IN_BATTLE|ATTACKING|DEFENDING",
  "against": "TARGET_SELECTOR"
}
```

### Card State Conditions

#### CHECK_CARD_STATE
```json
{
  "type": "CHECK_CARD_STATE",
  "target": "TARGET_SELECTOR",
  "state": "ACTIVE|RESTED|DAMAGED|PAIRED|LINKED",
  "paired_pilot_traits": ["Coordinator"]
}
```

#### CHECK_KEYWORD
```json
{
  "type": "CHECK_KEYWORD",
  "target": "TARGET_SELECTOR",
  "keyword": "BLOCKER|REPAIR|BREACH|HIGH_MANEUVER|FIRST_STRIKE|SUPPORT"
}
```

### Card Name Conditions

#### CHECK_CARD_NAME
```json
{
  "type": "CHECK_CARD_NAME",
  "target": "TARGET_SELECTOR",
  "name_contains": "Unicorn Mode",
  "exact_match": false
}
```

### Token Conditions

#### CHECK_IS_TOKEN
```json
{
  "type": "CHECK_IS_TOKEN",
  "target": "TARGET_SELECTOR",
  "is_token": true
}
```

---

## Action System

### Action Structure

```json
{
  "type": "ACTION_TYPE",
  "target": "TARGET_SELECTOR",
  "parameters": {...},
  "conditional_next": {...},
  "optional": false
}
```

### Card Draw/Discard Actions

#### DRAW
```json
{
  "type": "DRAW",
  "target": "SELF|OPPONENT",
  "amount": 1
}
```

#### DISCARD
```json
{
  "type": "DISCARD",
  "target": "SELF|OPPONENT",
  "amount": 1,
  "selection_method": "RANDOM|CHOOSE|ALL"
}
```

### Damage Actions

#### DAMAGE_UNIT
```json
{
  "type": "DAMAGE_UNIT",
  "target": {...},
  "amount": 2,
  "calculation": {
    "type": "FIXED|PER_COUNT|PER_STAT",
    "base": 1,
    "multiplier": {
      "stat": "AP",
      "divisor": 4
    }
  }
}
```

**Example:** "Deal 1 damage for each 4 AP this Unit has"
```json
{
  "type": "DAMAGE_UNIT",
  "target": {"selector": "ENEMY_UNIT", "count": 1},
  "calculation": {
    "type": "PER_STAT",
    "base": 1,
    "multiplier": {
      "stat": "AP",
      "divisor": 4,
      "source": "SELF"
    }
  }
}
```

#### DAMAGE_PLAYER
```json
{
  "type": "DAMAGE_PLAYER",
  "target": "OPPONENT",
  "amount": 1
}
```

### Deploy Actions

#### DEPLOY_CARD
```json
{
  "type": "DEPLOY_CARD",
  "source": "HAND|TRASH|DECK",
  "filters": {
    "card_type": "UNIT",
    "traits": ["Zeon"],
    "level": {"operator": "<=", "value": 3}
  },
  "count": 1,
  "state": "ACTIVE|RESTED",
  "pay_cost": true,
  "selection_method": "CHOOSE|REVEAL|TOP_DECK"
}
```

#### DEPLOY_TOKEN
```json
{
  "type": "DEPLOY_TOKEN",
  "token": {
    "name": "Gundam",
    "traits": ["White Base Team"],
    "ap": 3,
    "hp": 3,
    "keywords": [],
    "effects": []
  },
  "count": 1,
  "state": "RESTED"
}
```

**Example:** White Base conditional token deployment
```json
{
  "type": "CONDITIONAL_BRANCH",
  "conditions": [
    {
      "if": {
        "type": "COUNT_CARDS",
        "zone": "BATTLE_AREA",
        "owner": "SELF",
        "card_type": "UNIT",
        "operator": "==",
        "value": 0
      },
      "then": {
        "type": "DEPLOY_TOKEN",
        "token": {"name": "Gundam", "traits": ["White Base Team"], "ap": 3, "hp": 3}
      }
    },
    {
      "if": {
        "type": "COUNT_CARDS",
        "zone": "BATTLE_AREA",
        "owner": "SELF",
        "card_type": "UNIT",
        "operator": "==",
        "value": 1
      },
      "then": {
        "type": "DEPLOY_TOKEN",
        "token": {"name": "Guncannon", "traits": ["White Base Team"], "ap": 2, "hp": 2}
      }
    },
    {
      "if": {
        "type": "COUNT_CARDS",
        "zone": "BATTLE_AREA",
        "owner": "SELF",
        "card_type": "UNIT",
        "operator": ">=",
        "value": 2
      },
      "then": {
        "type": "DEPLOY_TOKEN",
        "token": {"name": "Guntank", "traits": ["White Base Team"], "ap": 1, "hp": 1}
      }
    }
  ]
}
```

### State Change Actions

#### REST_UNIT
```json
{
  "type": "REST_UNIT",
  "target": {...}
}
```

#### SET_ACTIVE
```json
{
  "type": "SET_ACTIVE",
  "target": {...}
}
```

### Stat Modification Actions

#### MODIFY_STAT
```json
{
  "type": "MODIFY_STAT",
  "target": {...},
  "stat": "AP|HP|LEVEL|COST",
  "modification": "+2|-2|=0",
  "duration": "PERMANENT|THIS_TURN|THIS_BATTLE|WHILE_CONDITION"
}
```

**Example:** "This Unit gets AP+2 during this turn"
```json
{
  "type": "MODIFY_STAT",
  "target": {"selector": "SELF"},
  "stat": "AP",
  "modification": "+2",
  "duration": "THIS_TURN"
}
```

#### RECOVER_HP
```json
{
  "type": "RECOVER_HP",
  "target": {...},
  "amount": 2
}
```

### Keyword Actions

#### GRANT_KEYWORD
```json
{
  "type": "GRANT_KEYWORD",
  "target": {...},
  "keyword": "BLOCKER|REPAIR|BREACH|HIGH_MANEUVER|FIRST_STRIKE|SUPPORT|SUPPRESSION",
  "value": 3,
  "duration": "PERMANENT|THIS_TURN|THIS_BATTLE|WHILE_CONDITION"
}
```

**Example:** "This Unit gains <Breach 4> during this turn"
```json
{
  "type": "GRANT_KEYWORD",
  "target": {"selector": "SELF"},
  "keyword": "BREACH",
  "value": 4,
  "duration": "THIS_TURN"
}
```

### Destroy Actions

#### DESTROY_CARD
```json
{
  "type": "DESTROY_CARD",
  "target": {...}
}
```

### Resource Actions

#### PLACE_RESOURCE
```json
{
  "type": "PLACE_RESOURCE",
  "resource_type": "NORMAL|EX",
  "state": "ACTIVE|RESTED"
}
```

### Deck Manipulation Actions

#### LOOK_AT_DECK
```json
{
  "type": "LOOK_AT_DECK",
  "owner": "SELF|OPPONENT",
  "amount": 3,
  "from": "TOP|BOTTOM",
  "reveal_to": "SELF|ALL",
  "conditional_next": {
    "conditions": [...],
    "actions": [...]
  }
}
```

**Example:** Zaku I Sniper Type deploy effect
```json
{
  "type": "LOOK_AT_DECK",
  "owner": "SELF",
  "amount": 1,
  "from": "TOP",
  "reveal_to": "SELF",
  "conditional_next": {
    "conditions": [
      {
        "type": "CHECK_CARD_TYPE",
        "card_type": "UNIT",
        "traits": ["Zeon", "Neo Zeon"],
        "trait_operator": "ANY"
      }
    ],
    "actions": [
      {
        "type": "ADD_TO_HAND",
        "target": {"selector": "LOOKED_AT_CARD"},
        "optional": true,
        "reveal": true
      }
    ],
    "else_actions": [
      {
        "type": "MOVE_CARD",
        "target": {"selector": "LOOKED_AT_CARD"},
        "destination": "DECK_BOTTOM"
      }
    ]
  }
}
```

#### RETURN_TO_HAND
```json
{
  "type": "RETURN_TO_HAND",
  "target": {...}
}
```

#### ADD_TO_HAND
```json
{
  "type": "ADD_TO_HAND",
  "target": {...},
  "reveal": false
}
```

#### MOVE_CARD
```json
{
  "type": "MOVE_CARD",
  "target": {...},
  "destination": "DECK_TOP|DECK_BOTTOM|TRASH|HAND|EXILE",
  "shuffle_after": false,
  "state": "ACTIVE|RESTED"
}
```

#### SHUFFLE_DECK
```json
{
  "type": "SHUFFLE_DECK",
  "owner": "SELF|OPPONENT"
}
```

#### SHIELD_TO_HAND
```json
{
  "type": "SHIELD_TO_HAND",
  "amount": 1
}
```

### Exile Actions

#### EXILE_CARDS
```json
{
  "type": "EXILE_CARDS",
  "source": "TRASH|HAND|DECK|BATTLE_AREA",
  "filters": {
    "card_type": "UNIT",
    "traits": ["Titans"]
  },
  "amount": 3,
  "selection_method": "CHOOSE"
}
```

### Battle Actions

#### CHANGE_ATTACK_TARGET
```json
{
  "type": "CHANGE_ATTACK_TARGET",
  "new_target": {...},
  "allowed_targets": ["ACTIVE_UNITS"]
}
```

#### PREVENT_ATTACK
```json
{
  "type": "PREVENT_ATTACK",
  "target": {...},
  "duration": "THIS_TURN"
}
```

#### FORCE_ATTACK
```json
{
  "type": "FORCE_ATTACK",
  "attacker": {...},
  "can_attack_on_deploy": true
}
```

### Protection Actions

#### PREVENT_DAMAGE
```json
{
  "type": "PREVENT_DAMAGE",
  "target": {...},
  "damage_type": "BATTLE|EFFECT|ALL",
  "duration": "THIS_BATTLE|THIS_TURN"
}
```

### Complex Actions

#### CONDITIONAL_BRANCH
```json
{
  "type": "CONDITIONAL_BRANCH",
  "conditions": [
    {
      "if": {...},
      "then": {...}
    }
  ]
}
```

#### ACTION_SEQUENCE
```json
{
  "type": "ACTION_SEQUENCE",
  "actions": [
    {...},
    {...}
  ],
  "execute_all": true
}
```

#### OPTIONAL_ACTION_CHAIN
"You may X. If you do, Y"

```json
{
  "type": "ACTION_SEQUENCE",
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

---

## Target System

### Target Selector Structure

```json
{
  "selector": "SELECTOR_TYPE",
  "count": 1,
  "variable_count": {"min": 1, "max": 2},
  "filters": {...},
  "selection_method": "CHOOSE|RANDOM|ALL"
}
```

### Selector Types

#### Self-Referential
- `SELF` - This card
- `PAIRED_PILOT` - The Pilot paired with this Unit
- `LINKED_PILOT` - The Pilot linked with this Unit

#### Friendly Targets
- `FRIENDLY_UNIT` - Any friendly Unit
- `FRIENDLY_BASE` - Any friendly Base
- `FRIENDLY_CARD` - Any friendly card
- `OTHER_FRIENDLY_UNIT` - Friendly Unit excluding self

#### Enemy Targets
- `ENEMY_UNIT` - Any enemy Unit
- `ENEMY_BASE` - Any enemy Base
- `ENEMY_PLAYER` - The opponent

#### Contextual Targets
- `ATTACKING_UNIT` - The Unit currently attacking
- `DEFENDING_UNIT` - The Unit currently defending
- `BATTLING_UNIT` - The Unit in battle with this Unit
- `LOOKED_AT_CARD` - Card from a LOOK_AT action
- `REVEALED_CARD` - Card from a reveal action

### Filter Structure

```json
{
  "card_type": "UNIT|PILOT|COMMAND|BASE",
  "traits": ["Zeon", "Neo Zeon"],
  "trait_operator": "ANY|ALL",
  "level": {"operator": "<=", "value": 4},
  "cost": {"operator": ">=", "value": 3},
  "ap": {"operator": "<=", "value": 3},
  "hp": {"operator": "<=", "value": 2},
  "state": "ACTIVE|RESTED|DAMAGED",
  "is_token": true,
  "has_keyword": "BLOCKER",
  "has_paired_pilot": false,
  "name_contains": "Gundam",
  "color": "BLUE|GREEN|RED|WHITE|PURPLE"
}
```

### Target Examples

**"Choose 1 enemy Unit"**
```json
{
  "selector": "ENEMY_UNIT",
  "count": 1,
  "selection_method": "CHOOSE"
}
```

**"All friendly (Zeon) Units"**
```json
{
  "selector": "FRIENDLY_UNIT",
  "selection_method": "ALL",
  "filters": {
    "traits": ["Zeon"]
  }
}
```

**"Choose 1 to 2 enemy Units with 3 or less HP"**
```json
{
  "selector": "ENEMY_UNIT",
  "variable_count": {"min": 1, "max": 2},
  "selection_method": "CHOOSE",
  "filters": {
    "hp": {"operator": "<=", "value": 3}
  }
}
```

**"1 enemy Unit token"**
```json
{
  "selector": "ENEMY_UNIT",
  "count": 1,
  "selection_method": "CHOOSE",
  "filters": {
    "is_token": true
  }
}
```

---

## Keyword System

### Keyword Structure

```json
{
  "keyword": "KEYWORD_TYPE",
  "value": 3,
  "description": "Human-readable description"
}
```

### Keyword Types

| Keyword | Value | Description |
|---------|-------|-------------|
| `BLOCKER` | null | Rest this Unit to change the attack target to it |
| `REPAIR` | X | At end of turn, recovers X HP |
| `BREACH` | X | When attack destroys enemy Unit, deal X damage to first shield |
| `HIGH_MANEUVER` | null | Can't be blocked |
| `FIRST_STRIKE` | null | Deals damage before enemy Unit in battle |
| `SUPPORT` | X | Rest to give another Unit AP+X |
| `SUPPRESSION` | null | Damage to shields hits multiple cards |

---

## Cost System

### Cost Structure

```json
{
  "cost_type": "RESOURCE|EXILE|ACTIVATION",
  "amount": 2,
  "exile_requirements": {
    "source": "TRASH",
    "filters": {
      "traits": ["Titans"]
    },
    "amount": 3
  }
}
```

### Cost Types

#### RESOURCE
Circled number costs (①, ②, ③)
```json
{
  "cost_type": "RESOURCE",
  "amount": 2
}
```

#### EXILE
Exile cards as cost
```json
{
  "cost_type": "EXILE",
  "exile_requirements": {
    "source": "TRASH",
    "filters": {
      "traits": ["Titans"]
    },
    "amount": 3,
    "selection_method": "CHOOSE"
  }
}
```

#### REST_SELF
Rest this card as cost
```json
{
  "cost_type": "REST_SELF"
}
```

---

## Restrictions System

```json
{
  "once_per_turn": true,
  "once_per_game": false,
  "only_if_condition": {...}
}
```

---

## Continuous Effects

### Continuous Effect Structure

```json
{
  "effect_id": "GD01-016-CE1",
  "effect_type": "CONTINUOUS",
  "conditions": [...],
  "modifications": [
    {
      "type": "MODIFY_STAT",
      "target": "SELF",
      "stat": "COST",
      "modification": "-1",
      "zone": "HAND"
    }
  ]
}
```

**Example:** "While you have 2 or more (Earth Federation) Units in play, this card in your hand gets cost -1."

```json
{
  "effect_id": "GD01-016-CE1",
  "effect_type": "CONTINUOUS",
  "conditions": [
    {
      "type": "COUNT_CARDS",
      "zone": "BATTLE_AREA",
      "owner": "SELF",
      "card_type": "UNIT",
      "traits": ["Earth Federation"],
      "operator": ">=",
      "value": 2
    }
  ],
  "modifications": [
    {
      "type": "MODIFY_STAT",
      "target": {"selector": "SELF"},
      "stat": "COST",
      "modification": "-1",
      "zone": "HAND"
    }
  ]
}
```

---

## Replacement Effects

### Replacement Effect Structure

```json
{
  "effect_type": "REPLACEMENT",
  "replaces": "PLAY|DEPLOY|ATTACK|DESTROY",
  "conditions": [...],
  "modifications": [...]
}
```

**Example:** "When playing this card from your hand, you may destroy 1 of your Link Units with \"Unicorn Mode\" in its card name that is Lv.5. If you do, play this card as if it has 0 Lv. and cost."

```json
{
  "effect_id": "GD01-002-E1",
  "effect_type": "REPLACEMENT",
  "triggers": ["ON_PLAY"],
  "conditions": [
    {
      "type": "PLAYED_FROM_HAND"
    }
  ],
  "actions": [
    {
      "type": "DESTROY_CARD",
      "target": {
        "selector": "FRIENDLY_UNIT",
        "count": 1,
        "selection_method": "CHOOSE",
        "filters": {
          "state": "LINKED",
          "name_contains": "Unicorn Mode",
          "level": {"operator": "==", "value": 5}
        }
      },
      "optional": true,
      "conditional_next": {
        "if_performed": [
          {
            "type": "MODIFY_PLAY_COST",
            "target": {"selector": "SELF"},
            "modifications": {
              "level": "=0",
              "cost": "=0"
            }
          }
        ]
      }
    }
  ]
}
```

---

## Complete Card Examples

### Example 1: Simple Triggered Effect (GD01-007)

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
      ],
      "restrictions": {}
    }
  ]
}
```

### Example 2: Keyword Ability (GD02-072)

**Text:** 
- "<Blocker> (Rest this Unit to change the attack target to it.)"
- "While a friendly white Base is in play, this Unit gains <Repair 1>."

```json
{
  "card_id": "GD02-072",
  "keywords": [
    {
      "keyword": "BLOCKER",
      "value": null,
      "description": "Rest this Unit to change the attack target to it."
    }
  ],
  "continuous_effects": [
    {
      "effect_id": "GD02-072-CE1",
      "effect_type": "CONTINUOUS",
      "conditions": [
        {
          "type": "COUNT_CARDS",
          "zone": "BATTLE_AREA",
          "owner": "SELF",
          "card_type": "BASE",
          "color": "WHITE",
          "operator": ">=",
          "value": 1
        }
      ],
      "modifications": [
        {
          "type": "GRANT_KEYWORD",
          "target": {"selector": "SELF"},
          "keyword": "REPAIR",
          "value": 1
        }
      ]
    }
  ]
}
```

### Example 3: Complex Activated Ability (ST01-015)

**Text:** "【Activate･Main】【Once per Turn】②：Deploy 1 [Gundam]((White Base Team)･AP3･HP3) Unit token if you have no Units in play, deploy 1 [Guncannon]((White Base Team)･AP2･HP2) Unit token if you have only 1 Unit in play, or deploy 1 [Guntank]((White Base Team)･AP1･HP1) Unit token if you have 2 or more Units in play."

```json
{
  "card_id": "ST01-015",
  "effects": [
    {
      "effect_id": "ST01-015-E1",
      "effect_type": "ACTIVATED",
      "triggers": ["ACTIVATE_MAIN"],
      "cost": {
        "cost_type": "RESOURCE",
        "amount": 2
      },
      "restrictions": {
        "once_per_turn": true
      },
      "actions": [
        {
          "type": "CONDITIONAL_BRANCH",
          "conditions": [
            {
              "if": {
                "type": "COUNT_CARDS",
                "zone": "BATTLE_AREA",
                "owner": "SELF",
                "card_type": "UNIT",
                "operator": "==",
                "value": 0
              },
              "then": {
                "type": "DEPLOY_TOKEN",
                "token": {
                  "name": "Gundam",
                  "traits": ["White Base Team"],
                  "ap": 3,
                  "hp": 3,
                  "keywords": [],
                  "effects": []
                },
                "count": 1,
                "state": "ACTIVE"
              }
            },
            {
              "if": {
                "type": "COUNT_CARDS",
                "zone": "BATTLE_AREA",
                "owner": "SELF",
                "card_type": "UNIT",
                "operator": "==",
                "value": 1
              },
              "then": {
                "type": "DEPLOY_TOKEN",
                "token": {
                  "name": "Guncannon",
                  "traits": ["White Base Team"],
                  "ap": 2,
                  "hp": 2,
                  "keywords": [],
                  "effects": []
                },
                "count": 1,
                "state": "ACTIVE"
              }
            },
            {
              "if": {
                "type": "COUNT_CARDS",
                "zone": "BATTLE_AREA",
                "owner": "SELF",
                "card_type": "UNIT",
                "operator": ">=",
                "value": 2
              },
              "then": {
                "type": "DEPLOY_TOKEN",
                "token": {
                  "name": "Guntank",
                  "traits": ["White Base Team"],
                  "ap": 1,
                  "hp": 1,
                  "keywords": [],
                  "effects": []
                },
                "count": 1,
                "state": "ACTIVE"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Example 4: Exile Cost Ability (GD03-015)

**Text:** "【Activate･Main】【Once per Turn】Exile 3 (Titans) cards from your trash: This Unit gains <Breach 4> during this turn."

```json
{
  "card_id": "GD03-015",
  "effects": [
    {
      "effect_id": "GD03-015-E1",
      "effect_type": "ACTIVATED",
      "triggers": ["ACTIVATE_MAIN"],
      "cost": {
        "cost_type": "EXILE",
        "exile_requirements": {
          "source": "TRASH",
          "filters": {
            "traits": ["Titans"]
          },
          "amount": 3,
          "selection_method": "CHOOSE"
        }
      },
      "restrictions": {
        "once_per_turn": true
      },
      "actions": [
        {
          "type": "GRANT_KEYWORD",
          "target": {"selector": "SELF"},
          "keyword": "BREACH",
          "value": 4,
          "duration": "THIS_TURN"
        }
      ]
    }
  ]
}
```

### Example 5: Event-Triggered Continuous Effect (ST03-001)

**Text:** "During your turn, when this Unit destroys an enemy shield area card with battle damage, choose 1 enemy Unit. Deal 2 damage to it."

```json
{
  "card_id": "ST03-001",
  "effects": [
    {
      "effect_id": "ST03-001-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_SHIELD_DESTROYED"],
      "conditions": [
        {
          "type": "CHECK_TURN",
          "turn_owner": "SELF"
        },
        {
          "type": "CHECK_DAMAGE_TYPE",
          "damage_type": "BATTLE"
        }
      ],
      "actions": [
        {
          "type": "DAMAGE_UNIT",
          "target": {
            "selector": "ENEMY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE"
          },
          "amount": 2
        }
      ]
    }
  ]
}
```

### Example 6: Optional Action Chain (GD01-048)

**Text:** "【Deploy】Look at the top card of your deck. If it is a (Zeon)/(Neo Zeon) Unit card, you may reveal it and add it to your hand. Return any remaining card to the bottom of your deck."

```json
{
  "card_id": "GD01-048",
  "effects": [
    {
      "effect_id": "GD01-048-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_DEPLOY"],
      "actions": [
        {
          "type": "LOOK_AT_DECK",
          "owner": "SELF",
          "amount": 1,
          "from": "TOP",
          "reveal_to": "SELF",
          "conditional_next": {
            "conditions": [
              {
                "type": "CHECK_CARD_TYPE",
                "card_type": "UNIT",
                "traits": ["Zeon", "Neo Zeon"],
                "trait_operator": "ANY"
              }
            ],
            "actions": [
              {
                "type": "ADD_TO_HAND",
                "target": {"selector": "LOOKED_AT_CARD"},
                "reveal": true,
                "optional": true
              }
            ],
            "else_actions": [
              {
                "type": "MOVE_CARD",
                "target": {"selector": "LOOKED_AT_CARD"},
                "destination": "DECK_BOTTOM"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

---

## Metadata Fields

```json
{
  "metadata": {
    "original_text": "【Destroyed】If you have another (OZ) Unit in play, draw 1.",
    "complexity_score": 2,
    "parsing_version": "1.0",
    "last_updated": "2026-02-07",
    "parsing_notes": "Simple conditional triggered effect",
    "requires_manual_review": false
  }
}
```

---

## Schema Validation Rules

### Required Fields
1. Every effect must have: `effect_id`, `effect_type`
2. TRIGGERED/ACTIVATED effects must have: `triggers`, `actions`
3. CONTINUOUS effects must have: `conditions`, `modifications`
4. Targets with selection must specify: `selector`, `count` or `variable_count`

### Validation Checks
1. **Trait Validation**: All traits must match the card's `Traits` field in card_database
2. **Trigger Validation**: Triggers must be from approved list
3. **Action Validation**: Actions must be from approved list
4. **Target Validation**: Target selectors must be valid for the action type
5. **Cost Validation**: Costs must match game rules
6. **Stat Validation**: Stats must be HP, AP, LEVEL, or COST

---

## Future Extensibility

### Adding New Mechanics
1. **New Triggers**: Add to trigger enum, document behavior
2. **New Conditions**: Create new condition type with parameters
3. **New Actions**: Create new action type with parameters
4. **New Keywords**: Add to keyword enum, define behavior

### Versioning Strategy
- Schema version in metadata field
- Backward compatibility through optional fields
- Migration scripts for schema updates

### Edge Case Handling
- Unknown effects: Store as `original_text` with `requires_manual_review: true`
- Complex interactions: Use nested conditional structures
- Future keywords: Extensible keyword system

---

## Implementation Recommendations

### Phase 1: Core System (474 cards)
1. Implement basic trigger types (Deploy, Destroyed, Attack)
2. Implement core actions (Draw, Damage, Rest, Deploy)
3. Handle simple conditions (trait checks, card counts)
4. Convert 80% of existing cards

### Phase 2: Advanced Features
1. Implement continuous effects
2. Implement replacement effects
3. Handle complex conditional chains
4. Convert remaining 20% of cards

### Phase 3: Validation & Testing
1. Build schema validator
2. Create test suite for each effect type
3. Validate all converted cards
4. Document edge cases

### Phase 4: Maintenance
1. Monitor new card releases
2. Update schema for new mechanics
3. Maintain conversion tools
4. Update documentation

---

## Summary Statistics

### Effect Distribution
- **Triggered Effects**: ~350 cards (74%)
- **Continuous Effects**: ~80 cards (17%)
- **Keywords Only**: ~40 cards (8%)
- **Replacement Effects**: ~4 cards (1%)

### Complexity Levels
- **Simple** (1 trigger, 1 action): ~200 cards (42%)
- **Medium** (1-2 triggers, 2-3 actions, simple conditions): ~220 cards (46%)
- **Complex** (multiple triggers, nested conditions, chains): ~54 cards (11%)

### Most Common Patterns
1. Deploy → Action (draw, damage, deploy token)
2. Destroyed → Conditional Draw/Damage
3. Attack → Stat modification
4. Continuous stat/keyword modification
5. Activated abilities with costs

---

## Conclusion

This schema provides a comprehensive, extensible foundation for converting Gundam Card Game effects into machine-readable format. It handles:

✅ All 474 existing cards with effects  
✅ Complex conditional chains and optional actions  
✅ Multiple effect types (triggered, activated, continuous, replacement)  
✅ Flexible targeting and filtering system  
✅ Cost system (resources, exile, activation)  
✅ Keyword abilities and token creation  
✅ Future extensibility for new mechanics  

The schema prioritizes **explicitness**, **validation**, and **extensibility** to support both current gameplay simulation and future card releases.
