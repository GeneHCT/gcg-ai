# Simulation Fix - Resource Manager Integration

## Issue
After implementing the ResourceManager, the simulation was failing with:
```
TypeError: LegalActionGenerator._can_play_card() missing 1 required positional argument: 'game_state'
```

## Root Cause
The `action_step_manager.py` file was still calling `_can_play_card()` with the old signature (2 parameters) instead of the new signature (3 parameters including `game_state`).

## Fix Applied

### Updated `simulator/action_step_manager.py`
Changed line 58 from:
```python
if card.type == 'COMMAND' and LegalActionGenerator._can_play_card(player, card):
```

To:
```python
if card.type == 'COMMAND' and LegalActionGenerator._can_play_card(player, card, game_state):
```

## Verification

### Test Results

1. **Unit Test**: Verified ResourceManager correctly spends resources
   - Before playing Cost 3 card: 5 active resources
   - After playing Cost 3 card: 2 active resources ✓

2. **Full Simulation Tests**:
   - Seed 42, 20 turns: Completed successfully (17 turns, Player 0 wins)
   - Seed 123, 30 turns: Completed successfully (23 turns, Player 0 wins)

### Sample Game Log Output
```
Resources: 3 (Active: 2, EX: 1)
Legal Actions Available: 5
    play_unit: 3 options
        - Hyakuren (Lv3, Cost2, AP4/HP3)
        - Ryusei-Go (Graze Custom Ⅱ) (Lv3, Cost2, AP2/HP2)
        - Ryusei-Go (Graze Custom Ⅱ) (Lv3, Cost2, AP2/HP2)

→ Action #4: PLAY_UNIT: Hyakuren (Lv3, Cost2)
    Result: Deployed Hyakuren (AP=4, HP=3)
```

## Status

✅ **All systems operational**

The simulator now works correctly with the ResourceManager:
- ✓ Resource Lv conditions are checked before playing cards
- ✓ Resource costs are paid by resting resources
- ✓ Resources reset to active at start of each turn
- ✓ Action step manager properly checks card playability
- ✓ Full game simulations run to completion
- ✓ Random agents can play cards correctly

## Files Modified

1. `simulator/action_step_manager.py` - Added missing `game_state` parameter to `_can_play_card()` call

## No Further Changes Needed

All other files in the simulator were already updated correctly:
- `simulator/random_agent.py` ✓
- `simulator/game_manager.py` ✓
- `simulator/trigger_manager.py` ✓
- `simulator/action_executor.py` ✓
- `simulator/rest_mechanics.py` ✓
- `simulator/run_simulation.py` ✓
