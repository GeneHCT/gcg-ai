# Card Effect Conversion Examples

This document provides 20 diverse examples of card effects converted to the proposed JSON schema, covering various complexity levels and mechanics.

---

## Example 1: Simple Deploy Effect

**Card:** GD01-007 (Noin's Aries)  
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
  ]
}
```

---

## Example 2: Keyword + Continuous Effect

**Card:** GD02-072 (Hyaku-Shiki)  
**Text:**
- "<Blocker>"
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

---

## Example 3: Replacement Effect

**Card:** GD01-002 (Unicorn Gundam Destroy Mode)  
**Text:** "When playing this card from your hand, you may destroy 1 of your Link Units with \"Unicorn Mode\" in its card name that is Lv.5. If you do, play this card as if it has 0 Lv. and cost."

```json
{
  "card_id": "GD01-002",
  "effects": [
    {
      "effect_id": "GD01-002-E1",
      "effect_type": "REPLACEMENT",
      "triggers": ["ON_PLAY"],
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
    },
    {
      "effect_id": "GD01-002-E2",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_ATTACK"],
      "actions": [
        {
          "type": "REST_UNIT",
          "target": {
            "selector": "ENEMY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE"
          }
        }
      ]
    }
  ]
}
```

---

## Example 4: Conditional Token Deployment

**Card:** ST01-015 (White Base)  
**Text:** "【Activate･Main】【Once per Turn】②：Deploy 1 [Gundam]((White Base Team)･AP3･HP3) Unit token if you have no Units in play, deploy 1 [Guncannon]((White Base Team)･AP2･HP2) Unit token if you have only 1 Unit in play, or deploy 1 [Guntank]((White Base Team)･AP1･HP1) Unit token if you have 2 or more Units in play."

```json
{
  "card_id": "ST01-015",
  "effects": [
    {
      "effect_id": "ST01-015-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_BURST"],
      "actions": [
        {
          "type": "DEPLOY_CARD",
          "target": {"selector": "SELF"},
          "pay_cost": true
        }
      ]
    },
    {
      "effect_id": "ST01-015-E2",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_DEPLOY"],
      "actions": [
        {
          "type": "SHIELD_TO_HAND",
          "amount": 1
        }
      ]
    },
    {
      "effect_id": "ST01-015-E3",
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
                  "hp": 3
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
                  "hp": 2
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
                  "hp": 1
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

---

## Example 5: Exile Cost Ability

**Card:** GD03-015 (Baund Doc)  
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

---

## Example 6: Event-Triggered Effect

**Card:** ST03-001 (Sinanju)  
**Text:** "During your turn, when this Unit destroys an enemy shield area card with battle damage, choose 1 enemy Unit. Deal 2 damage to it."

```json
{
  "card_id": "ST03-001",
  "continuous_effects": [
    {
      "effect_id": "ST03-001-CE1",
      "effect_type": "CONTINUOUS",
      "conditions": [
        {
          "type": "CHECK_CARD_STATE",
          "target": {"selector": "SELF"},
          "state": "PAIRED"
        }
      ],
      "modifications": [
        {
          "type": "GRANT_KEYWORD",
          "target": {"selector": "SELF"},
          "keyword": "HIGH_MANEUVER"
        }
      ]
    }
  ],
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

---

## Example 7: Look and Reveal

**Card:** GD01-048 (Zaku I Sniper Type)  
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

## Example 8: Variable Count Targeting

**Card:** GD01-099 (Intercept Orders)  
**Text:** "【Main】/【Action】Choose 1 to 2 enemy Units with 3 or less HP. Rest them."

```json
{
  "card_id": "GD01-099",
  "effects": [
    {
      "effect_id": "GD01-099-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_BURST"],
      "actions": [
        {
          "type": "REST_UNIT",
          "target": {
            "selector": "ENEMY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE",
            "filters": {
              "hp": {"operator": "<=", "value": 5}
            }
          }
        }
      ]
    },
    {
      "effect_id": "GD01-099-E2",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_MAIN_PHASE", "ON_ACTION_PHASE"],
      "actions": [
        {
          "type": "REST_UNIT",
          "target": {
            "selector": "ENEMY_UNIT",
            "variable_count": {"min": 1, "max": 2},
            "selection_method": "CHOOSE",
            "filters": {
              "hp": {"operator": "<=", "value": 3}
            }
          }
        }
      ]
    }
  ]
}
```

---

## Example 9: Dynamic Damage Calculation

**Card:** GD03-033 (Providence Gundam)  
**Text:** "【Attack】Choose 1 enemy Unit. Deal 1 damage to it for each 4 AP this Unit has."

```json
{
  "card_id": "GD03-033",
  "effects": [
    {
      "effect_id": "GD03-033-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_ATTACK"],
      "actions": [
        {
          "type": "DAMAGE_UNIT",
          "target": {
            "selector": "ENEMY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE"
          },
          "calculation": {
            "type": "PER_STAT",
            "base": 1,
            "multiplier": {
              "stat": "AP",
              "source": "SELF",
              "divisor": 4
            }
          }
        }
      ]
    }
  ]
}
```

---

## Example 10: Combined Triggers

**Card:** GD01-046 (CGUE)  
**Text:** "【During Pair･(Coordinator) Pilot】【Once per Turn】When you use this Unit's <Support> to increase a (ZAFT) Unit's AP, set this Unit as active."

```json
{
  "card_id": "GD01-046",
  "keywords": [
    {
      "keyword": "SUPPORT",
      "value": 3,
      "description": "Rest this Unit. 1 other friendly Unit gets AP+3 during this turn."
    }
  ],
  "effects": [
    {
      "effect_id": "GD01-046-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_SUPPORT_USED"],
      "conditions": [
        {
          "type": "CHECK_CARD_STATE",
          "target": {"selector": "SELF"},
          "state": "PAIRED",
          "paired_pilot_traits": ["Coordinator"]
        },
        {
          "type": "CHECK_SUPPORT_TARGET_TRAIT",
          "traits": ["ZAFT"]
        }
      ],
      "restrictions": {
        "once_per_turn": true
      },
      "actions": [
        {
          "type": "SET_ACTIVE",
          "target": {"selector": "SELF"}
        }
      ]
    }
  ]
}
```

---

## Example 11: Continuous Stat Modification

**Card:** GD01-016 (Zaku Warrior)  
**Text:** "While you have 2 or more (Earth Federation) Units in play, this card in your hand gets cost -1."

```json
{
  "card_id": "GD01-016",
  "continuous_effects": [
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
  ]
}
```

---

## Example 12: Conditional Keyword Granting

**Card:** GD01-054 (Zamza-Zah)  
**Text:** "While this Unit has 5 or more AP, it gains <Breach 3>."

```json
{
  "card_id": "GD01-054",
  "continuous_effects": [
    {
      "effect_id": "GD01-054-CE1",
      "effect_type": "CONTINUOUS",
      "conditions": [
        {
          "type": "CHECK_STAT",
          "target": {"selector": "SELF"},
          "stat": "AP",
          "operator": ">=",
          "value": 5
        }
      ],
      "modifications": [
        {
          "type": "GRANT_KEYWORD",
          "target": {"selector": "SELF"},
          "keyword": "BREACH",
          "value": 3
        }
      ]
    }
  ]
}
```

---

## Example 13: Area Effect

**Card:** GD01-102 (Securing the Supply Line)  
**Text:** "【Main】All friendly Units that are Lv.4 or lower recover 2 HP."

```json
{
  "card_id": "GD01-102",
  "effects": [
    {
      "effect_id": "GD01-102-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_MAIN_PHASE"],
      "actions": [
        {
          "type": "RECOVER_HP",
          "target": {
            "selector": "FRIENDLY_UNIT",
            "selection_method": "ALL",
            "filters": {
              "level": {"operator": "<=", "value": 4}
            }
          },
          "amount": 2
        }
      ]
    }
  ]
}
```

---

## Example 14: Multiple Token Types

**Card:** GD01-066 (Justice Gundam)  
**Text:** "【Deploy】Deploy 1 [Fatum-00]((Triple Ship Alliance)･AP2･HP2･<Blocker>) Unit token."

```json
{
  "card_id": "GD01-066",
  "effects": [
    {
      "effect_id": "GD01-066-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_DEPLOY"],
      "actions": [
        {
          "type": "DEPLOY_TOKEN",
          "token": {
            "name": "Fatum-00",
            "traits": ["Triple Ship Alliance"],
            "ap": 2,
            "hp": 2,
            "keywords": [
              {
                "keyword": "BLOCKER",
                "value": null
              }
            ]
          },
          "count": 1,
          "state": "ACTIVE"
        }
      ]
    },
    {
      "effect_id": "GD01-066-E2",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_ATTACK"],
      "conditions": [
        {
          "type": "CHECK_CARD_STATE",
          "target": {"selector": "SELF"},
          "state": "PAIRED"
        }
      ],
      "actions": [
        {
          "type": "FORCE_ATTACK",
          "attacker": {
            "selector": "FRIENDLY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE",
            "filters": {
              "traits": ["Triple Ship Alliance"],
              "is_token": true
            }
          },
          "can_attack_on_deploy": true
        }
      ]
    }
  ]
}
```

---

## Example 15: Deck Manipulation

**Card:** GD01-003 (Unicorn Gundam)  
**Text:** "【During Link】【Attack】Choose 12 cards from your trash. Return them to their owner's deck and shuffle it. If you do, set this Unit as active. It gains <First Strike> during this turn."

```json
{
  "card_id": "GD01-003",
  "effects": [
    {
      "effect_id": "GD01-003-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["WHILE_LINKED", "ON_ATTACK"],
      "actions": [
        {
          "type": "MOVE_CARD",
          "target": {
            "selector": "CARD_IN_TRASH",
            "count": 12,
            "selection_method": "CHOOSE",
            "filters": {
              "owner": "SELF"
            }
          },
          "destination": "DECK_TOP",
          "shuffle_after": true,
          "optional": false,
          "conditional_next": {
            "if_performed": [
              {
                "type": "SET_ACTIVE",
                "target": {"selector": "SELF"}
              },
              {
                "type": "GRANT_KEYWORD",
                "target": {"selector": "SELF"},
                "keyword": "FIRST_STRIKE",
                "duration": "THIS_TURN"
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

## Example 16: Paired Pilot Condition

**Card:** GD01-025 (Wing Gundam)  
**Text:** "【When Paired･(Operation Meteor) Pilot】Place 1 rested Resource. Then, this Unit gains <First Strike> during this turn."

```json
{
  "card_id": "GD01-025",
  "effects": [
    {
      "effect_id": "GD01-025-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_PAIRED"],
      "conditions": [
        {
          "type": "CHECK_CARD_STATE",
          "target": {"selector": "PAIRED_PILOT"},
          "paired_pilot_traits": ["Operation Meteor"]
        }
      ],
      "actions": [
        {
          "type": "PLACE_RESOURCE",
          "resource_type": "NORMAL",
          "state": "RESTED"
        },
        {
          "type": "GRANT_KEYWORD",
          "target": {"selector": "SELF"},
          "keyword": "FIRST_STRIKE",
          "duration": "THIS_TURN"
        }
      ]
    }
  ]
}
```

---

## Example 17: Opponent's Turn Trigger

**Card:** GD03-128 (Doritea)  
**Text:** "【Once per Turn】During your opponent's turn, when one of your Units is rested by one of your opponent's effects, choose 1 enemy Unit. Deal 1 damage to it."

```json
{
  "card_id": "GD03-128",
  "effects": [
    {
      "effect_id": "GD03-128-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_BURST"],
      "actions": [
        {
          "type": "DEPLOY_CARD",
          "target": {"selector": "SELF"},
          "pay_cost": true
        }
      ]
    },
    {
      "effect_id": "GD03-128-E2",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_DEPLOY"],
      "actions": [
        {
          "type": "SHIELD_TO_HAND",
          "amount": 1
        }
      ]
    },
    {
      "effect_id": "GD03-128-E3",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_RESTED_BY_EFFECT"],
      "conditions": [
        {
          "type": "CHECK_TURN",
          "turn_owner": "OPPONENT"
        },
        {
          "type": "CHECK_EFFECT_SOURCE",
          "source": "OPPONENT"
        }
      ],
      "restrictions": {
        "once_per_turn": true
      },
      "actions": [
        {
          "type": "DAMAGE_UNIT",
          "target": {
            "selector": "ENEMY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE"
          },
          "amount": 1
        }
      ]
    }
  ]
}
```

---

## Example 18: Destroy with Conditions

**Card:** GD02-111 (Decisive Last Resort)  
**Text:** "【Main】Choose 6 purple Unit cards from your trash. Exile them from the game. If you do, choose 1 enemy Unit. Destroy it."

```json
{
  "card_id": "GD02-111",
  "effects": [
    {
      "effect_id": "GD02-111-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_BURST"],
      "actions": [
        {
          "type": "DAMAGE_UNIT",
          "target": {
            "selector": "ENEMY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE",
            "filters": {
              "level": {"operator": "<=", "value": 3}
            }
          },
          "amount": 2
        }
      ]
    },
    {
      "effect_id": "GD02-111-E2",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_MAIN_PHASE"],
      "actions": [
        {
          "type": "EXILE_CARDS",
          "source": "TRASH",
          "filters": {
            "card_type": "UNIT",
            "color": "PURPLE"
          },
          "amount": 6,
          "selection_method": "CHOOSE",
          "conditional_next": {
            "if_performed": [
              {
                "type": "DESTROY_CARD",
                "target": {
                  "selector": "ENEMY_UNIT",
                  "count": 1,
                  "selection_method": "CHOOSE"
                }
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

## Example 19: Battle-Specific Timing

**Card:** GD01-063 (Gundam X)  
**Text:** "During your turn, while this Unit is battling an enemy Unit that is Lv.2 or lower, it gains <First Strike>."

```json
{
  "card_id": "GD01-063",
  "continuous_effects": [
    {
      "effect_id": "GD01-063-CE1",
      "effect_type": "CONTINUOUS",
      "conditions": [
        {
          "type": "CHECK_TURN",
          "turn_owner": "SELF"
        },
        {
          "type": "CHECK_BATTLE_STATE",
          "state": "IN_BATTLE",
          "against": {
            "selector": "BATTLING_UNIT",
            "filters": {
              "level": {"operator": "<=", "value": 2}
            }
          }
        }
      ],
      "modifications": [
        {
          "type": "GRANT_KEYWORD",
          "target": {"selector": "SELF"},
          "keyword": "FIRST_STRIKE"
        }
      ]
    }
  ]
}
```

---

## Example 20: COMMAND Card with Pilot

**Card:** ST02-012 (Simultaneous Fire)  
**Text:**
- "【Main】Choose 1 of your Units. It gains <Breach 3> during this turn."
- "【Pilot】[Trowa Barton]"

```json
{
  "card_id": "ST02-012",
  "effects": [
    {
      "effect_id": "ST02-012-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_MAIN_PHASE"],
      "actions": [
        {
          "type": "GRANT_KEYWORD",
          "target": {
            "selector": "FRIENDLY_UNIT",
            "count": 1,
            "selection_method": "CHOOSE"
          },
          "keyword": "BREACH",
          "value": 3,
          "duration": "THIS_TURN"
        }
      ]
    }
  ],
  "pilot_for": ["Trowa Barton"],
  "metadata": {
    "original_text": "【Main】Choose 1 of your Units. It gains <Breach 3> during this turn. 【Pilot】[Trowa Barton]",
    "card_type": "COMMAND"
  }
}
```

---

## Summary of Patterns Covered

1. **Simple triggered effects** - Deploy, Destroyed, Attack
2. **Keyword abilities** - Blocker, Repair, Breach
3. **Continuous effects** - While conditions are true
4. **Replacement effects** - Modify how cards are played
5. **Conditional branching** - Multiple outcomes based on game state
6. **Exile costs** - Alternative cost payment
7. **Event triggers** - React to specific game events
8. **Look and reveal** - Deck manipulation
9. **Variable targeting** - Choose 1 to X
10. **Dynamic calculations** - Damage based on stats
11. **Combined triggers** - Multiple conditions
12. **Stat modification** - Temporary and continuous
13. **Area effects** - Affect multiple cards
14. **Token deployment** - Create tokens with abilities
15. **Deck shuffle** - Move cards and shuffle
16. **Paired pilot conditions** - Specific pilot requirements
17. **Opponent's turn** - Effects during opponent's turn
18. **Optional chains** - "If you do" patterns
19. **Battle-specific** - During combat only
20. **COMMAND cards** - Pilot attachment cards

All examples include proper structure, validation-ready format, and extensibility for future mechanics.
