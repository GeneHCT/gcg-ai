# 1. Architecture & State Management
- **Immutability:** Treat GameState as immutable where possible. Use `.copy(deep=True)` for branching in RL search.
- **Deterministic:** All RNG must use `numpy.random.Generator` with a seed. No global `random`.
- **Decoupling:** Separate 'Game State' (data) from 'Engine' (logic) and 'Interpreter' (effect resolution).

# 2. Card Effect Interpreter (The IR System)
- **Schema-First:** Effects must NOT be hard-coded. Use the Intermediate Representation (IR) JSON schema.
- **Hook System:** Implement an event-bus for triggers: `on_play`, `on_destroy`, `on_attack`, `on_battle_damage`.
- **Condition/Action Pattern:** Cards are composed of 'Conditions' (e.g., Trait check) and 'Actions' (e.g., Draw, Damage).

# 3. RL & Vectorization Rules
- **Observation Space:** Every `get_observation()` call must return a fixed-size NumPy array or Dict of arrays.
- **Action Masking:** Every state must provide a `get_legal_actions_mask()` bitmask. Never let the agent choose an illegal move.
- **Reward Shaping:** Keep reward logic in a separate `RewardManager` class, not inside the core engine logic.

# 4. Code Style & Token Efficiency
- **Be Concise:** No boilerplate. Omit docstrings for self-explanatory methods.
- **Type Hinting:** Mandatory type hints for all function signatures to aid AI reasoning.
- **Performance:** Use list comprehensions and NumPy vectorization over for-loops for board-state calculations.
- **DRY Keywords:** Use a registry/enum for Keywords (Blocker, Breach, etc.) to prevent string-matching errors.

# 5. Game Constants (From gamerules.txt)
- **Max Units in Battle Area:** 6 (Rule 11-4)
- **Max Bases in Shield Area:** 1 (Rule 11-5)
- **Max Hand Size:** 10 (enforced during Hand Step, Rule 7-6-5)
- **Max Resources:** 15 total, max 5 EX Resources (Rule 4-4-2)
- **Starting Shields:** 6 cards (Rule 6-2-2)
- **Shield HP:** 1 HP each (Rule 4-6-4-2)
- **EX Base Stats:** 0 AP, 3 HP (Rule 5-17-3-1-1)
- **Deck Size:** 50 cards (Rule 6-1-1)
- **Resource Deck Size:** 10 cards (Rule 6-1-1)
- **Max Card Copies in Deck:** 4 (Rule 2-1-2)

# 6. Turn Phase Flow (Rule 7)
```
START PHASE → DRAW PHASE → RESOURCE PHASE → MAIN PHASE → END PHASE
```
- **Start Phase:** Active Step (set all active) → Start Step (trigger effects)
- **Draw Phase:** Active player draws 1
- **Resource Phase:** Place 1 Resource (active)
- **Main Phase:** Play cards, activate effects, attack (any order, repeat)
- **End Phase:** Action Step → End Step → Hand Step → Cleanup Step

# 7. Combat Step Flow (Rule 8)
```
ATTACK STEP → BLOCK STEP → ACTION STEP → DAMAGE STEP → BATTLE END STEP
```
- **Skip to Battle End Step** if attacking/targeted Unit destroyed/moved after Attack/Block/Action steps
- **Damage Step:** Unit-to-Unit simultaneous (unless <First Strike>), Unit-to-Shield/Base sequential

# 8. Effect Resolution Priority (Rule 10-1-6)
1. **【Burst】** effects (always highest priority)
2. New triggers during resolution (stack/interrupt)
3. Active player's triggered effects (in owner's chosen order)
4. Standby player's triggered effects (in owner's chosen order)

# 9. Rules Management (Rule 11) - Automatic State-Based Actions
**Check in this order whenever game state changes:**
1. **Defeat Check:** No shields + battle damage OR no deck → defeated
2. **Destruction:** HP ≤ 0 → destroyed → trash
3. **Battle Area Excess:** >6 Units → choose 1 to trash (NOT destroyed)
4. **Base Section Excess:** >1 Base → choose 1 to trash (NOT destroyed)

# 10. Targeting & Attack Rules
- **Can Attack:** Opponent player OR rested enemy Unit (Rule 8-2-1)
- **Cannot Attack:** Active enemy Units, your own Units, same-turn deployed (unless Link Unit)
- **Summoning Sickness:** Units cannot attack turn deployed (Rule 3-2-4) UNLESS Link Unit (Rule 3-2-6-3)
- **Link Unit:** Unit + Pilot meeting Link Condition → can attack immediately

# 11. Important Mechanics
- **"If you do" vs "Then":** (Rule 5-20)
  - "If you do": Second effect only if first resolves fully
  - "Then": Second effect happens even if first fails
- **Card Text > Rules:** Card effects override comprehensive rules (Rule 1-3-1)
- **Impossible Actions:** Don't perform (Rule 1-3-2), partial = do as much as possible
- **Already in State:** Cannot put card into state it's already in (Rule 1-3-2-1)
- **Simultaneous Choices:** Active player chooses first (Rule 1-3-4)
- **Tokens:** Lv=0, Cost=0, No color, removed when leaving field (Rule 5-17-2)

# 12. Action Step Protocol (Rule 9)
- **Standby player acts first** (not active player!)
- Alternates: Standby → Active → Standby → Active...
- Ends when **both pass consecutively**
- Occurs: During battle (after Block Step) AND during End Phase

# 13. Keyword Stacking Rules
**Stack (add values):**
- <Repair X> (Rule 13-1-1-2)
- <Breach X> (Rule 13-1-2-5)
- <Support X> (Rule 13-1-3-2)

**Don't Stack (only have once):**
- <Blocker> (Rule 13-1-4-2)
- <First Strike> (Rule 13-1-5-3)
- <High-Maneuver> (Rule 13-1-6-2)
- <Suppression> (Rule 13-1-7-2)