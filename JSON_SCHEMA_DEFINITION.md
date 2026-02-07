# JSON Schema Definition for Card Effects

This is a formal JSON Schema (draft-07) specification for validating card effect JSON files.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://gcg-ai.github.io/schemas/card-effect.schema.json",
  "title": "Gundam Card Game Card Effect Schema",
  "description": "Schema for card effect definitions in the Gundam Card Game simulator",
  "type": "object",
  "required": ["card_id"],
  "properties": {
    "card_id": {
      "type": "string",
      "pattern": "^(GD|ST|R|T)\\d{2}-\\d{3}$",
      "description": "Card identifier matching the format: SET-NUMBER"
    },
    "effects": {
      "type": "array",
      "description": "Array of effect objects",
      "items": {
        "$ref": "#/definitions/effect"
      }
    },
    "keywords": {
      "type": "array",
      "description": "Array of keyword abilities",
      "items": {
        "$ref": "#/definitions/keyword"
      }
    },
    "continuous_effects": {
      "type": "array",
      "description": "Array of continuous effects",
      "items": {
        "$ref": "#/definitions/continuous_effect"
      }
    },
    "pilot_for": {
      "type": "array",
      "description": "Pilot names this card can be paired with (for COMMAND cards)",
      "items": {
        "type": "string"
      }
    },
    "metadata": {
      "$ref": "#/definitions/metadata"
    }
  },
  "definitions": {
    "effect": {
      "type": "object",
      "required": ["effect_id", "effect_type"],
      "properties": {
        "effect_id": {
          "type": "string",
          "pattern": "^[A-Z0-9]+-[A-Z0-9]+-E\\d+$",
          "description": "Unique effect identifier: CARDID-E1"
        },
        "effect_type": {
          "type": "string",
          "enum": ["TRIGGERED", "ACTIVATED", "CONTINUOUS", "KEYWORD", "REPLACEMENT"],
          "description": "Type of effect"
        },
        "triggers": {
          "type": "array",
          "description": "Array of trigger types",
          "items": {
            "type": "string",
            "enum": [
              "ON_PLAY",
              "ON_DEPLOY",
              "ON_ATTACK",
              "ON_DESTROYED",
              "ON_BURST",
              "ON_MAIN_PHASE",
              "ON_ACTION_PHASE",
              "ON_PAIRED",
              "ON_LINKED",
              "WHILE_PAIRED",
              "WHILE_LINKED",
              "ACTIVATE_MAIN",
              "ACTIVATE_ACTION",
              "ON_UNIT_DESTROYED_BY_SELF",
              "ON_UNIT_DESTROYED_BY_ANY",
              "ON_BATTLE_DAMAGE_DEALT",
              "ON_SHIELD_DESTROYED",
              "ON_HP_RECOVERED",
              "ON_RESTED_BY_EFFECT",
              "ON_EFFECT_DAMAGE_RECEIVED",
              "ON_SUPPORT_USED"
            ]
          }
        },
        "conditions": {
          "type": "array",
          "description": "Array of condition objects",
          "items": {
            "$ref": "#/definitions/condition"
          }
        },
        "actions": {
          "type": "array",
          "description": "Array of action objects",
          "items": {
            "$ref": "#/definitions/action"
          }
        },
        "cost": {
          "$ref": "#/definitions/cost"
        },
        "restrictions": {
          "$ref": "#/definitions/restrictions"
        },
        "metadata": {
          "$ref": "#/definitions/metadata"
        }
      }
    },
    "condition": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "COUNT_CARDS",
            "CHECK_STAT",
            "CHECK_PLAYER_LEVEL",
            "CHECK_TURN",
            "CHECK_BATTLE_STATE",
            "CHECK_CARD_STATE",
            "CHECK_KEYWORD",
            "CHECK_CARD_NAME",
            "CHECK_IS_TOKEN",
            "CHECK_CARD_TYPE",
            "CHECK_DAMAGE_TYPE",
            "CHECK_EFFECT_SOURCE",
            "CHECK_SUPPORT_TARGET_TRAIT",
            "PLAYED_FROM_HAND"
          ]
        },
        "zone": {
          "type": "string",
          "enum": ["BATTLE_AREA", "TRASH", "HAND", "DECK", "SHIELD_AREA", "EXILE", "RESOURCE_AREA"]
        },
        "owner": {
          "type": "string",
          "enum": ["SELF", "OPPONENT", "ANY"]
        },
        "card_type": {
          "type": "string",
          "enum": ["UNIT", "PILOT", "COMMAND", "BASE", "RESOURCE"]
        },
        "traits": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "trait_operator": {
          "type": "string",
          "enum": ["ANY", "ALL"],
          "default": "ANY"
        },
        "stat": {
          "type": "string",
          "enum": ["HP", "AP", "LEVEL", "COST"]
        },
        "operator": {
          "type": "string",
          "enum": [">=", "<=", "==", "!=", ">", "<"]
        },
        "value": {
          "type": "integer"
        },
        "exclude_self": {
          "type": "boolean",
          "default": false
        },
        "level": {
          "$ref": "#/definitions/stat_comparison"
        },
        "cost": {
          "$ref": "#/definitions/stat_comparison"
        },
        "ap": {
          "$ref": "#/definitions/stat_comparison"
        },
        "hp": {
          "$ref": "#/definitions/stat_comparison"
        },
        "color": {
          "type": "string",
          "enum": ["BLUE", "GREEN", "RED", "WHITE", "PURPLE"]
        },
        "state": {
          "type": "string",
          "enum": ["ACTIVE", "RESTED", "DAMAGED", "PAIRED", "LINKED", "IN_BATTLE", "ATTACKING", "DEFENDING"]
        },
        "target": {
          "$ref": "#/definitions/target"
        },
        "negate": {
          "type": "boolean",
          "default": false
        },
        "turn_owner": {
          "type": "string",
          "enum": ["SELF", "OPPONENT"]
        },
        "damage_type": {
          "type": "string",
          "enum": ["BATTLE", "EFFECT", "ALL"]
        },
        "keyword": {
          "type": "string",
          "enum": ["BLOCKER", "REPAIR", "BREACH", "HIGH_MANEUVER", "FIRST_STRIKE", "SUPPORT", "SUPPRESSION"]
        },
        "name_contains": {
          "type": "string"
        },
        "exact_match": {
          "type": "boolean",
          "default": false
        },
        "is_token": {
          "type": "boolean"
        },
        "has_keyword": {
          "type": "string"
        },
        "has_paired_pilot": {
          "type": "boolean"
        },
        "paired_pilot_traits": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "action": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "DRAW",
            "DISCARD",
            "DAMAGE_UNIT",
            "DAMAGE_PLAYER",
            "DEPLOY_CARD",
            "DEPLOY_TOKEN",
            "REST_UNIT",
            "SET_ACTIVE",
            "MODIFY_STAT",
            "RECOVER_HP",
            "GRANT_KEYWORD",
            "DESTROY_CARD",
            "PLACE_RESOURCE",
            "LOOK_AT_DECK",
            "RETURN_TO_HAND",
            "ADD_TO_HAND",
            "MOVE_CARD",
            "SHUFFLE_DECK",
            "SHIELD_TO_HAND",
            "EXILE_CARDS",
            "CHANGE_ATTACK_TARGET",
            "PREVENT_ATTACK",
            "FORCE_ATTACK",
            "PREVENT_DAMAGE",
            "CONDITIONAL_BRANCH",
            "ACTION_SEQUENCE",
            "MODIFY_PLAY_COST"
          ]
        },
        "target": {
          "$ref": "#/definitions/target"
        },
        "amount": {
          "type": "integer"
        },
        "calculation": {
          "$ref": "#/definitions/calculation"
        },
        "optional": {
          "type": "boolean",
          "default": false
        },
        "conditional_next": {
          "$ref": "#/definitions/conditional_next"
        },
        "stat": {
          "type": "string",
          "enum": ["HP", "AP", "LEVEL", "COST"]
        },
        "modification": {
          "type": "string",
          "pattern": "^[+\\-=]\\d+$"
        },
        "duration": {
          "type": "string",
          "enum": ["PERMANENT", "THIS_TURN", "THIS_BATTLE", "WHILE_CONDITION"]
        },
        "keyword": {
          "type": "string",
          "enum": ["BLOCKER", "REPAIR", "BREACH", "HIGH_MANEUVER", "FIRST_STRIKE", "SUPPORT", "SUPPRESSION"]
        },
        "value": {
          "type": "integer"
        },
        "source": {
          "type": "string",
          "enum": ["HAND", "TRASH", "DECK", "BATTLE_AREA", "SHIELD_AREA"]
        },
        "destination": {
          "type": "string",
          "enum": ["DECK_TOP", "DECK_BOTTOM", "TRASH", "HAND", "EXILE", "BATTLE_AREA"]
        },
        "filters": {
          "$ref": "#/definitions/filters"
        },
        "token": {
          "$ref": "#/definitions/token"
        },
        "state": {
          "type": "string",
          "enum": ["ACTIVE", "RESTED"]
        },
        "pay_cost": {
          "type": "boolean",
          "default": false
        },
        "selection_method": {
          "type": "string",
          "enum": ["CHOOSE", "REVEAL", "TOP_DECK", "RANDOM", "ALL"]
        },
        "count": {
          "type": "integer",
          "minimum": 1
        },
        "resource_type": {
          "type": "string",
          "enum": ["NORMAL", "EX"]
        },
        "owner": {
          "type": "string",
          "enum": ["SELF", "OPPONENT"]
        },
        "from": {
          "type": "string",
          "enum": ["TOP", "BOTTOM"]
        },
        "reveal_to": {
          "type": "string",
          "enum": ["SELF", "ALL"]
        },
        "reveal": {
          "type": "boolean",
          "default": false
        },
        "shuffle_after": {
          "type": "boolean",
          "default": false
        },
        "damage_type": {
          "type": "string",
          "enum": ["BATTLE", "EFFECT", "ALL"]
        },
        "new_target": {
          "$ref": "#/definitions/target"
        },
        "allowed_targets": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "attacker": {
          "$ref": "#/definitions/target"
        },
        "can_attack_on_deploy": {
          "type": "boolean",
          "default": false
        },
        "conditions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/branch_condition"
          }
        },
        "actions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/action"
          }
        },
        "execute_all": {
          "type": "boolean",
          "default": true
        },
        "modifications": {
          "type": "object",
          "properties": {
            "level": {
              "type": "string"
            },
            "cost": {
              "type": "string"
            }
          }
        }
      }
    },
    "target": {
      "type": "object",
      "required": ["selector"],
      "properties": {
        "selector": {
          "type": "string",
          "enum": [
            "SELF",
            "PAIRED_PILOT",
            "LINKED_PILOT",
            "FRIENDLY_UNIT",
            "FRIENDLY_BASE",
            "FRIENDLY_CARD",
            "OTHER_FRIENDLY_UNIT",
            "ENEMY_UNIT",
            "ENEMY_BASE",
            "ENEMY_PLAYER",
            "ATTACKING_UNIT",
            "DEFENDING_UNIT",
            "BATTLING_UNIT",
            "LOOKED_AT_CARD",
            "REVEALED_CARD",
            "CARD_IN_TRASH"
          ]
        },
        "count": {
          "type": "integer",
          "minimum": 1
        },
        "variable_count": {
          "type": "object",
          "required": ["min", "max"],
          "properties": {
            "min": {
              "type": "integer",
              "minimum": 0
            },
            "max": {
              "type": "integer",
              "minimum": 1
            }
          }
        },
        "filters": {
          "$ref": "#/definitions/filters"
        },
        "selection_method": {
          "type": "string",
          "enum": ["CHOOSE", "RANDOM", "ALL"]
        }
      }
    },
    "filters": {
      "type": "object",
      "properties": {
        "card_type": {
          "type": "string",
          "enum": ["UNIT", "PILOT", "COMMAND", "BASE", "RESOURCE"]
        },
        "traits": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "trait_operator": {
          "type": "string",
          "enum": ["ANY", "ALL"],
          "default": "ANY"
        },
        "level": {
          "$ref": "#/definitions/stat_comparison"
        },
        "cost": {
          "$ref": "#/definitions/stat_comparison"
        },
        "ap": {
          "$ref": "#/definitions/stat_comparison"
        },
        "hp": {
          "$ref": "#/definitions/stat_comparison"
        },
        "state": {
          "type": "string",
          "enum": ["ACTIVE", "RESTED", "DAMAGED"]
        },
        "is_token": {
          "type": "boolean"
        },
        "has_keyword": {
          "type": "string"
        },
        "has_paired_pilot": {
          "type": "boolean"
        },
        "name_contains": {
          "type": "string"
        },
        "color": {
          "type": "string",
          "enum": ["BLUE", "GREEN", "RED", "WHITE", "PURPLE"]
        },
        "owner": {
          "type": "string",
          "enum": ["SELF", "OPPONENT"]
        }
      }
    },
    "stat_comparison": {
      "type": "object",
      "required": ["operator", "value"],
      "properties": {
        "operator": {
          "type": "string",
          "enum": [">=", "<=", "==", "!=", ">", "<"]
        },
        "value": {
          "type": "integer"
        }
      }
    },
    "calculation": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["FIXED", "PER_COUNT", "PER_STAT"]
        },
        "base": {
          "type": "integer"
        },
        "multiplier": {
          "type": "object",
          "properties": {
            "stat": {
              "type": "string",
              "enum": ["HP", "AP", "LEVEL", "COST"]
            },
            "source": {
              "type": "string",
              "enum": ["SELF", "TARGET"]
            },
            "divisor": {
              "type": "integer",
              "minimum": 1
            }
          }
        }
      }
    },
    "conditional_next": {
      "type": "object",
      "properties": {
        "conditions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/condition"
          }
        },
        "actions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/action"
          }
        },
        "else_actions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/action"
          }
        },
        "if_performed": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/action"
          }
        }
      }
    },
    "branch_condition": {
      "type": "object",
      "required": ["if", "then"],
      "properties": {
        "if": {
          "$ref": "#/definitions/condition"
        },
        "then": {
          "$ref": "#/definitions/action"
        }
      }
    },
    "cost": {
      "type": "object",
      "required": ["cost_type"],
      "properties": {
        "cost_type": {
          "type": "string",
          "enum": ["RESOURCE", "EXILE", "REST_SELF"]
        },
        "amount": {
          "type": "integer",
          "minimum": 0
        },
        "exile_requirements": {
          "type": "object",
          "required": ["source", "amount"],
          "properties": {
            "source": {
              "type": "string",
              "enum": ["TRASH", "HAND", "DECK", "BATTLE_AREA"]
            },
            "filters": {
              "$ref": "#/definitions/filters"
            },
            "amount": {
              "type": "integer",
              "minimum": 1
            },
            "selection_method": {
              "type": "string",
              "enum": ["CHOOSE", "RANDOM"]
            }
          }
        }
      }
    },
    "restrictions": {
      "type": "object",
      "properties": {
        "once_per_turn": {
          "type": "boolean",
          "default": false
        },
        "once_per_game": {
          "type": "boolean",
          "default": false
        },
        "only_if_condition": {
          "$ref": "#/definitions/condition"
        }
      }
    },
    "keyword": {
      "type": "object",
      "required": ["keyword"],
      "properties": {
        "keyword": {
          "type": "string",
          "enum": ["BLOCKER", "REPAIR", "BREACH", "HIGH_MANEUVER", "FIRST_STRIKE", "SUPPORT", "SUPPRESSION"]
        },
        "value": {
          "type": ["integer", "null"]
        },
        "description": {
          "type": "string"
        }
      }
    },
    "token": {
      "type": "object",
      "required": ["name", "traits", "ap", "hp"],
      "properties": {
        "name": {
          "type": "string"
        },
        "traits": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "ap": {
          "type": "integer",
          "minimum": 0
        },
        "hp": {
          "type": "integer",
          "minimum": 1
        },
        "keywords": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/keyword"
          }
        },
        "effects": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/effect"
          }
        }
      }
    },
    "continuous_effect": {
      "type": "object",
      "required": ["effect_id", "effect_type", "conditions", "modifications"],
      "properties": {
        "effect_id": {
          "type": "string",
          "pattern": "^[A-Z0-9]+-[A-Z0-9]+-CE\\d+$"
        },
        "effect_type": {
          "type": "string",
          "enum": ["CONTINUOUS"]
        },
        "conditions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/condition"
          }
        },
        "modifications": {
          "type": "array",
          "items": {
            "anyOf": [
              {
                "type": "object",
                "properties": {
                  "type": {
                    "const": "MODIFY_STAT"
                  },
                  "target": {
                    "$ref": "#/definitions/target"
                  },
                  "stat": {
                    "type": "string",
                    "enum": ["HP", "AP", "LEVEL", "COST"]
                  },
                  "modification": {
                    "type": "string"
                  },
                  "zone": {
                    "type": "string",
                    "enum": ["BATTLE_AREA", "HAND"]
                  }
                }
              },
              {
                "type": "object",
                "properties": {
                  "type": {
                    "const": "GRANT_KEYWORD"
                  },
                  "target": {
                    "$ref": "#/definitions/target"
                  },
                  "keyword": {
                    "type": "string"
                  },
                  "value": {
                    "type": ["integer", "null"]
                  }
                }
              }
            ]
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "original_text": {
          "type": "string",
          "description": "Original card text from card database"
        },
        "complexity_score": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10,
          "description": "Subjective complexity rating 1-10"
        },
        "parsing_version": {
          "type": "string",
          "description": "Version of parser/schema used"
        },
        "last_updated": {
          "type": "string",
          "format": "date",
          "description": "Date of last update YYYY-MM-DD"
        },
        "parsing_notes": {
          "type": "string",
          "description": "Notes about conversion process"
        },
        "requires_manual_review": {
          "type": "boolean",
          "default": false,
          "description": "Flag for effects needing manual review"
        },
        "card_type": {
          "type": "string",
          "enum": ["UNIT", "PILOT", "COMMAND", "BASE", "RESOURCE"]
        }
      }
    }
  }
}
```

---

## Usage Example

To validate a card effect JSON file using this schema:

### JavaScript (using ajv)
```javascript
const Ajv = require('ajv');
const schema = require('./card-effect.schema.json');
const cardEffect = require('./card_effects_converted/GD01-007.json');

const ajv = new Ajv();
const validate = ajv.compile(schema);
const valid = validate(cardEffect);

if (!valid) {
  console.log(validate.errors);
}
```

### Python (using jsonschema)
```python
import json
from jsonschema import validate, ValidationError

with open('card-effect.schema.json') as f:
    schema = json.load(f)

with open('card_effects_converted/GD01-007.json') as f:
    card_effect = json.load(f)

try:
    validate(instance=card_effect, schema=schema)
    print("Valid!")
except ValidationError as e:
    print(f"Invalid: {e.message}")
```

---

## Schema Features

### 1. Required Fields Enforcement
- `card_id` is always required
- Each effect must have `effect_id` and `effect_type`
- Appropriate fields required based on effect type

### 2. Enum Validation
- All trigger types, action types, selectors are validated against allowed lists
- Ensures typos are caught immediately

### 3. Pattern Validation
- Card IDs must match format: `(GD|ST|R|T)##-###`
- Effect IDs must match format: `CARDID-E#` or `CARDID-CE#`
- Stat modifications must match format: `+/-/=number`

### 4. Type Safety
- Numbers must be integers where appropriate
- Booleans have proper defaults
- Strings are validated for enums

### 5. Structural Validation
- Nested structures (targets, conditions, actions) are fully validated
- Conditional structures have required fields
- References between components are valid

---

## Extending the Schema

When adding new mechanics:

1. **New Trigger**: Add to `triggers` enum in effect definition
2. **New Condition**: Add to `condition.type` enum and add properties
3. **New Action**: Add to `action.type` enum and add properties
4. **New Target**: Add to `target.selector` enum
5. **New Keyword**: Add to `keyword.keyword` enum

Example adding a new trigger:
```json
{
  "triggers": {
    "enum": [
      // ... existing triggers
      "ON_NEW_MECHANIC"  // Add here
    ]
  }
}
```

---

## Validation Levels

### Level 1: Schema Validation (Automated)
- JSON structure is correct
- Required fields present
- Enums match allowed values
- Types are correct

### Level 2: Reference Validation (Semi-automated)
- Traits match card database
- Card IDs exist
- Effect IDs are unique

### Level 3: Logic Validation (Manual)
- Conditions match actions logically
- Targets make sense for actions
- Effect matches original card text

### Level 4: Game Rules Validation (Testing)
- Effect behaves correctly in simulator
- Edge cases handled properly
- No infinite loops or crashes

---

## Schema Maintenance

### Versioning
- Update `parsing_version` in metadata when schema changes
- Document breaking changes
- Provide migration scripts for old conversions

### Documentation
- Keep enum lists in sync with documentation
- Update examples when schema changes
- Maintain changelog of schema versions

### Testing
- Validate all existing cards when schema changes
- Test edge cases
- Ensure backward compatibility where possible
