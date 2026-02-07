# Schema Structure Visualization

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CARD JSON FILE                        │
│  (card_effects_converted/GD01-XXX)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │           card_id: "GD01-XXX"               │
        └─────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┬──────────────────┐
        ▼                     ▼                      ▼                  ▼
   ┌─────────┐         ┌──────────┐          ┌──────────┐      ┌──────────┐
   │ effects │         │ keywords │          │continuous│      │ metadata │
   │  array  │         │  array   │          │ _effects │      │  object  │
   └─────────┘         └──────────┘          └──────────┘      └──────────┘
```

---

## Effect Object Structure

```
┌────────────────────────────────────────────────────────────────┐
│                       EFFECT OBJECT                            │
└────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┬─────────────┐
        ▼                     ▼                      ▼             ▼
  ┌──────────┐          ┌──────────┐         ┌──────────┐  ┌──────────┐
  │effect_id │          │effect_   │         │restrictions │ metadata │
  │          │          │  type    │         │           │  │          │
  └──────────┘          └──────────┘         └──────────┘  └──────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                     ▼                      ▼
  ┌──────────┐          ┌──────────┐         ┌──────────┐
  │ triggers │          │conditions│         │ actions  │
  │  array   │          │  array   │         │  array   │
  └──────────┘          └──────────┘         └──────────┘
```

---

## Effect Types Hierarchy

```
                    EFFECT TYPE
                        │
        ┌───────────────┼───────────────┬──────────────┐
        ▼               ▼               ▼              ▼
   TRIGGERED       ACTIVATED       CONTINUOUS      REPLACEMENT
        │               │               │              │
        │               │               │              │
    ┌───┴───┐       ┌───┴───┐      ┌───┴───┐      ┌───┴───┐
    │triggers│      │triggers│      │conditions│   │triggers│
    │conditions     │conditions     │modifications│ │actions │
    │actions │      │cost    │      │          │   │(replace)│
    └───────┘       │actions │      └──────────┘   └────────┘
                    │restrictions
                    └────────┘
```

---

## Trigger Flow

```
GAME EVENT OCCURS
        │
        ▼
┌───────────────────┐
│ Check Triggers    │
│ (ON_DEPLOY,       │
│  ON_ATTACK, etc.) │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Evaluate          │
│ Conditions        │
│ (all must pass)   │
└───────────────────┘
        │
        ├─────── FAIL ────► Effect doesn't trigger
        │
        ▼ PASS
┌───────────────────┐
│ Execute Actions   │
│ (in sequence)     │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Check for         │
│ Conditional Next  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Game State        │
│ Updated           │
└───────────────────┘
```

---

## Condition Evaluation

```
                    CONDITION OBJECT
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                  ▼
    ┌────────┐      ┌──────────┐      ┌──────────┐
    │  type  │      │parameters│      │ operator │
    └────────┘      └──────────┘      └──────────┘
        │                 │                  │
        └─────────────────┴──────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Evaluate against      │
              │ current game state    │
              └───────────────────────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
            TRUE (pass)         FALSE (fail)
```

---

## Action Execution

```
                    ACTION OBJECT
                          │
        ┌─────────────────┼─────────────────┬──────────────┐
        ▼                 ▼                  ▼              ▼
    ┌────────┐      ┌──────────┐      ┌──────────┐  ┌──────────┐
    │  type  │      │  target  │      │parameters│  │ optional │
    └────────┘      └──────────┘      └──────────┘  └──────────┘
        │                 │                  │              │
        └─────────────────┴──────────────────┴──────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Resolve Target        │
              │ (who/what is affected)│
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Execute Action        │
              │ (modify game state)   │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Conditional Next?     │
              │ (follow-up actions)   │
              └───────────────────────┘
```

---

## Target Resolution

```
                    TARGET SELECTOR
                          │
        ┌─────────────────┼─────────────────┬──────────────┐
        ▼                 ▼                  ▼              ▼
   ┌─────────┐      ┌──────────┐      ┌──────────┐  ┌──────────┐
   │selector │      │  count   │      │ filters  │  │selection │
   │  type   │      │          │      │          │  │  method  │
   └─────────┘      └──────────┘      └──────────┘  └──────────┘
        │                 │                  │              │
        └─────────────────┴──────────────────┴──────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Find all cards        │
              │ matching selector     │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Apply filters         │
              │ (trait, HP, AP, etc.) │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Selection method      │
              │ (CHOOSE/RANDOM/ALL)   │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Return target(s)      │
              └───────────────────────┘
```

---

## Continuous Effect Flow

```
┌───────────────────┐
│ Game State        │
│ Changes           │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Check ALL         │
│ Continuous Effects│
│ in play           │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Evaluate          │
│ Conditions        │
└───────────────────┘
        │
  ┌─────┴─────┐
  ▼           ▼
TRUE        FALSE
  │           │
  ▼           ▼
Apply      Remove
Modification  Modification
  │           │
  └─────┬─────┘
        │
        ▼
┌───────────────────┐
│ Updated Game      │
│ State             │
└───────────────────┘
```

---

## Cost Payment Flow

```
┌───────────────────┐
│ Player activates  │
│ ability           │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Check cost        │
│ requirements      │
└───────────────────┘
        │
  ┌─────┴─────┐
  ▼           ▼
Can Pay    Can't Pay
  │           │
  ▼           ▼
┌─────────┐ ┌──────────┐
│Pay cost │ │Effect    │
│(Resource│ │doesn't   │
│ /Exile/ │ │activate  │
│ Rest)   │ └──────────┘
└─────────┘
  │
  ▼
┌───────────────────┐
│ Execute effect    │
└───────────────────┘
```

---

## Data Flow Example: Simple Effect

**Card:** GD01-007 - "【Destroyed】If you have another (OZ) Unit in play, draw 1."

```
┌─────────────────────────────────────────┐
│ GAME EVENT: Unit Destroyed              │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Check: Is trigger ON_DESTROYED?         │
│ Result: YES ✓                           │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Evaluate Condition:                     │
│ COUNT_CARDS(zone=BATTLE_AREA,           │
│   owner=SELF, traits=["OZ"],            │
│   exclude_self=true) >= 1               │
│                                         │
│ Check game state: 1 (OZ) Unit in play   │
│ Result: TRUE ✓                          │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Execute Action: DRAW                    │
│ Parameters: target=SELF, amount=1       │
│                                         │
│ Player draws 1 card                     │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Effect Complete                         │
└─────────────────────────────────────────┘
```

---

## Data Flow Example: Complex Effect

**Card:** ST01-015 - White Base conditional token deployment

```
┌─────────────────────────────────────────┐
│ PLAYER ACTION: Activate ability         │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Check trigger: ACTIVATE_MAIN            │
│ Result: YES ✓                           │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Check cost: 2 Resources                 │
│ Player has resources?                   │
│ Result: YES ✓                           │
│ Pay 2 resources                         │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Execute: CONDITIONAL_BRANCH             │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Check Branch 1:                         │
│ COUNT_CARDS(BATTLE_AREA, UNIT) == 0?    │
│                                         │
│ Current Units: 0                        │
│ Result: TRUE ✓                          │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Execute: DEPLOY_TOKEN                   │
│ Token: Gundam (AP3, HP3)                │
│                                         │
│ Deploy Gundam token to battle area      │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Skip Branch 2 & 3 (already matched)     │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Effect Complete                         │
└─────────────────────────────────────────┘
```

---

## Schema Component Relationships

```
                 ┌──────────────┐
                 │   CARD JSON  │
                 └──────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ EFFECTS │    │KEYWORDS │    │CONTINUOUS│
   └─────────┘    └─────────┘    └─────────┘
        │                              │
        ▼                              ▼
   ┌─────────┐                   ┌─────────┐
   │TRIGGERS │                   │CONDITIONS│
   └─────────┘                   └─────────┘
        │                              │
        ▼                              ▼
   ┌─────────┐                   ┌─────────┐
   │CONDITIONS│                  │MODIFICATIONS│
   └─────────┘                   └─────────┘
        │
        ▼
   ┌─────────┐
   │ ACTIONS │
   └─────────┘
        │
        ▼
   ┌─────────┐
   │ TARGETS │
   └─────────┘
        │
        ▼
   ┌─────────┐
   │ FILTERS │
   └─────────┘
```

---

## Validation Chain

```
┌─────────────────────────────────────────┐
│ JSON Structure Validation               │
│ - All required fields present           │
│ - Correct data types                    │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Enum Validation                         │
│ - Triggers from approved list           │
│ - Actions from approved list            │
│ - Selectors from approved list          │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Reference Validation                    │
│ - Traits match card data                │
│ - Card IDs exist                        │
│ - Zones are valid                       │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Logic Validation                        │
│ - Conditions match actions              │
│ - Targets valid for actions             │
│ - Costs make sense                      │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Consistency Validation                  │
│ - Similar cards use similar patterns    │
│ - Effect matches original text          │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ VALIDATED ✓                             │
└─────────────────────────────────────────┘
```

---

## Implementation Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  (UI, Card Display, Effect Text Generation)                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    GAME LOGIC LAYER                          │
│  (Effect Execution, Condition Evaluation, Action Processing) │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    STATE MANAGEMENT LAYER                    │
│  (Game State, Card State, Zone Management)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                         │
│  (Card Database, Effect JSON Files)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                             │
│  (JSON Files, Database)                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Extensibility Points

```
NEW MECHANIC DISCOVERED
        │
        ▼
┌─────────────────────┐
│ Is it a new...      │
└─────────────────────┘
        │
    ┌───┴────┬────────┬────────┬────────┐
    ▼        ▼        ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Trigger?││Condition││Action? ││Target? ││Keyword?│
└────────┘└────────┘└────────┘└────────┘└────────┘
    │        │        │        │        │
    └────────┴────────┴────────┴────────┘
              │
              ▼
    ┌───────────────────┐
    │ Add to enum       │
    │ Document behavior │
    │ Update examples   │
    └───────────────────┘
              │
              ▼
    ┌───────────────────┐
    │ Schema extended   │
    │ (backward compat) │
    └───────────────────┘
```

---

## Summary

This visualization shows:

1. **Hierarchical Structure**: How card data is organized
2. **Flow Diagrams**: How effects are triggered and executed
3. **Relationships**: How components connect
4. **Validation**: How data is verified
5. **Extensibility**: How to add new mechanics

The schema is designed to be:
- **Clear**: Easy to understand and visualize
- **Modular**: Components can be mixed and matched
- **Extensible**: New mechanics can be added
- **Validated**: Structure enforces correctness
