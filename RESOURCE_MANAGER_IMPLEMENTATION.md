# Resource Management System Implementation

## Summary

Successfully refactored and implemented the resource management system for the TCG simulator based on the actual game rules from `gamerules.txt`.

## Changes Made

### 1. Created `simulator/resource_manager.py`

Replaced the skeleton `simulator/resource_logic.py` with a fully-implemented `ResourceManager` class that properly handles:

#### Game Rules Implemented:

- **Rule 2-9 (Lv/Level Condition)**
  - Checks if player has enough total resources (including EX resources) to meet a card's level requirement
  - Both active and rested resources count toward level condition
  
- **Rule 2-10 (Cost Payment)**
  - Pays costs by resting active resources in the resource area
  - Only active (not rested) resources can be used to pay costs
  
- **Rule 4-4 (Resource Area)**
  - Enforces max 15 resources in resource area
  - Enforces max 5 EX resources
  - Resource area is public (both players can view)
  
- **Rule 5-4 (Active/Rested State)**
  - Resources can be Active (vertical) or Rested (horizontal)
  - Resources are placed Active when added
  - Resources are reset to Active at start of turn
  
- **Rule 7-5-2-2 (Playing Cards)**
  - Checks both Lv condition and Cost condition before allowing card play
  - Properly rests resources when paying costs

#### Key Features:

- **ResourceState Class**: Tracks which resources are rested using a set of indices
- **ResourceManager Methods**:
  - `can_play_card()` - Checks if player can afford to play a card
  - `check_lv_condition()` - Verifies level requirement
  - `can_pay_cost()` - Checks if player has enough active resources
  - `pay_cost()` - Rests resources to pay a cost
  - `reset_all_resources()` - Resets all resources to active (start of turn)
  - `can_add_resource()` - Checks resource limits
  - `add_resource()` - Adds resource from resource deck
  - `add_ex_resource()` - Adds EX resource
  - `count_active_resources()` - Counts non-rested resources
  - `count_total_resources()` - Counts all resources (for Lv check)

### 2. Updated `simulator/game_manager.py`

**Player Class Changes:**
- Added `_rested_resource_indices: set` field to track which resources are rested
- Updated `get_active_resources()` to use ResourceManager for accurate counts
- Now properly supports rested/active state for resources

**TurnManager Changes:**
- `start_phase()` now calls `ResourceManager.reset_all_resources()` to reset resources at start of turn

**ObservationGenerator Changes:**
- Updated to pass `game_state` parameter when calling `get_active_resources()`

### 3. Updated `simulator/random_agent.py`

**LegalActionGenerator:**
- `_can_play_card()` now uses `ResourceManager.can_play_card()` instead of manual checks
- Properly passes `game_state` parameter

**ActionExecutor:**
- `PLAY_UNIT` action now uses `ResourceManager.can_play_card()` and `ResourceManager.pay_cost()`
- `PLAY_COMMAND` action now uses ResourceManager for cost payment
- Removed old manual resource resting logic

### 4. Updated `simulator/trigger_manager.py`

- `_can_afford_cost()` now uses `ResourceManager.can_pay_cost()` for RESOURCE cost type
- `_pay_cost()` now uses `ResourceManager.pay_cost()` for proper resource resting

### 5. Updated `simulator/action_executor.py`

- Deploy from zone action now uses ResourceManager for checking and paying costs
- Properly rests resources when deploying units from hand

### 6. Updated `simulator/rest_mechanics.py`

- `RestCostManager` methods now delegate to ResourceManager
- Added deprecation notices to guide developers to use ResourceManager directly

### 7. Updated `simulator/run_simulation.py`

- `log_phase_transition()` now passes `game_state` when calling `get_active_resources()`

### 8. Deleted Old File

- Removed `simulator/resource_logic.py` (skeleton pseudo-code)

## Testing

Created comprehensive test suite in `test_resource_manager.py` that validates:

1. ✓ Basic resource operations (counting total/active resources)
2. ✓ Lv condition checking (with and without EX resources)
3. ✓ Cost payment by resting resources
4. ✓ Resource reset at start of turn
5. ✓ Can play card integration (Lv + Cost together)
6. ✓ Resource area limits (15 max, 5 EX max)

All tests pass successfully!

## How It Works

### Resource State Tracking

Resources are Card objects stored in `player.resource_area`. Since Card objects don't have an `is_rested` attribute, we track rested state separately:

- Each Player has a `_rested_resource_indices` set
- When a resource at index `i` is rested, `i` is added to the set
- When checking if a resource is active, we check if its index is NOT in the set

### Cost Payment Flow

1. Player attempts to play a card
2. `ResourceManager.can_play_card()` checks:
   - Lv condition: `total_resources >= card.level`
   - Cost condition: `active_resources >= card.cost`
3. If checks pass, `ResourceManager.pay_cost()` is called:
   - Gets list of active resource indices
   - Rests the first `cost` number of active resources
   - Adds their indices to the rested set

### Turn Reset Flow

1. At start of turn, `TurnManager.start_phase()` is called
2. Calls `RestManager.reset_all_cards()` to reset units and bases
3. Calls `ResourceManager.reset_all_resources()` to reset resources
4. Resource reset clears the `_rested_resource_indices` set
5. All resources become active again

## Integration with Existing Code

The ResourceManager seamlessly integrates with:

- **random_agent.py** - Uses ResourceManager to check if cards can be played and pays costs
- **action_executor.py** - Uses ResourceManager for deploy-from-zone effects
- **trigger_manager.py** - Uses ResourceManager for activated ability costs
- **game_manager.py** - Uses ResourceManager for turn start reset
- **rest_mechanics.py** - Delegates to ResourceManager for cost payment

All existing code has been updated to use the new ResourceManager, ensuring consistent resource handling throughout the simulator.

## Naming Convention

Following the project's naming pattern:
- `rest_mechanics.py` → manages rest/active state
- `base_system.py` → manages base-related logic
- `link_system.py` → manages linking
- `resource_manager.py` → manages resource-related operations ✓

The name "resource_manager" fits perfectly with the existing module naming structure.
