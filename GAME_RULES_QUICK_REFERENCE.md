# Gundam Card Game - Quick Rules Reference

**Version:** Based on Comprehensive Rules Ver. 1.5.0 (January 30, 2025)

---

## 🎯 Win/Loss Conditions (Rules 1-2)

**You WIN when your opponent is defeated.**

**You LOSE (defeated) when:**
1. You receive **battle damage from a Unit** while having **no cards in your shield area** (Rule 1-2-2-1)
2. You have **no cards remaining in your deck** (Rule 1-2-2-2)
3. You **concede** at any time (Rule 1-2-4)

**Important:** Defeat is checked during Rules Management. If both players are defeated simultaneously, both lose.

---

## 📍 Game Locations (Rules 4)

### Player Zones (each player has their own)
- **Deck Area** (private, face down)
- **Resource Deck Area** (private, face down)
- **Resource Area** (public) - Max 15 Resources total, max 5 EX Resources
- **Battle Area** (public) - Max 6 Units
- **Shield Area** (has two sections):
  - **Shield Section** (private, face down) - No limit
  - **Base Section** (public, face up) - Max 1 Base
- **Hand** (private) - Max 10 cards (enforced during Hand Step)
- **Trash** (public, face up)
- **Removal Area** (public)

### The "Field"
Battle Area + Resource Area + Shield Area = "the field"

---

## 🎴 Card Types (Rules 3)

1. **Unit** - Deployed to Battle Area, can attack, has AP/HP/Link Conditions
2. **Pilot** - Paired beneath Units, grants bonuses and effects
3. **Command** - Played for one-time effects (【Main】/【Action】 timing)
4. **Base** - Deployed to Shield Area Base Section, has AP/HP, absorbs damage
5. **Resource** - Placed in Resource Area to pay costs

### Key Card Properties
- **Lv (Level):** Minimum resources needed to play
- **Cost:** Resources to rest when playing
- **AP (Attack Points):** Offensive strength
- **HP (Hit Points):** Defensive strength (destroyed when HP ≤ 0)
- **Traits:** Categories like (Zeon), (Earth Federation), (Mobile Suit)
- **Color:** Blue, Green, Red, White, Purple (Resources have no color)

---

## 🔄 Turn Structure (Rules 7) ⭐ CRITICAL

### Turn Flow (5 Phases)
```
START PHASE → DRAW PHASE → RESOURCE PHASE → MAIN PHASE → END PHASE
```

### 1. START PHASE (Rule 7-2)
**Steps:**
1. **Active Step:** Set all rested cards to active (battle area, resource area, base section)
2. **Start Step:** Activate "at the start of the turn" effects

### 2. DRAW PHASE (Rule 7-3)
- Active player draws 1 card
- If deck becomes empty after drawing, you immediately lose

### 3. RESOURCE PHASE (Rule 7-4)
- Place 1 Resource from resource deck face-up and active into resource area

### 4. MAIN PHASE (Rule 7-5) ⭐ MOST COMPLEX
**Permitted Actions (any order, any number of times):**
- **Play cards from hand** (pay Level requirement + Cost)
  - Deploy a Unit
  - Deploy a Base
  - Pair a Pilot
  - Activate 【Main】 Command
- **Activate 【Activate･Main】 effects**
- **Attack with a Unit** (see Combat below)

**End:** Active player declares "end main phase" → go to End Phase

### 5. END PHASE (Rule 7-6)
**Steps:**
1. **Action Step:** Players alternate activating 【Action】 Commands/【Activate･Action】 effects (standby player starts)
2. **End Step:** Activate "at the end of the turn" effects
3. **Hand Step:** Discard down to 10 cards if hand exceeds limit
4. **Cleanup Step:** "During this turn" effects end

---

## ⚔️ Combat System (Rules 8) ⭐ CRITICAL

### Attack Declaration
- Active player selects an **active** Unit in battle area
- **Rest it** and declare attack target:
  - **Player** (opponent)
  - **Rested enemy Unit**

### Battle Steps (5 steps)
```
ATTACK STEP → BLOCK STEP → ACTION STEP → DAMAGE STEP → BATTLE END STEP
```

### 1. ATTACK STEP (Rule 8-2)
- Rest attacking Unit, declare target
- 【Attack】 effects trigger
- "During this battle" effects gain effect
- **If attacking/targeted Unit is destroyed/moved, skip to Battle End Step**

### 2. BLOCK STEP (Rule 8-3)
- Standby player may activate **<Blocker>** on one active Unit
- <Blocker> redirects attack to that Unit
- Can only use <Blocker> once per attack
- Originally targeted Unit cannot use its own <Blocker>
- **If attacking/targeted Unit is destroyed/moved, skip to Battle End Step**

### 3. ACTION STEP (Rule 8-4)
- Players alternate activating 【Action】 Commands/【Activate･Action】 effects (standby player first)
- **If attacking/targeted Unit is destroyed/moved, skip to Battle End Step**

### 4. DAMAGE STEP (Rule 8-5) ⭐ DAMAGE RESOLUTION

#### Attack on Player (Rule 8-5-2)
1. **No Base, No Shields:** Player receives battle damage = attacking Unit's AP → **Player loses immediately**
2. **No Base, Has Shields:** Deal damage to **top Shield**
   - Shield has 1 HP → destroyed → reveal it
   - If has 【Burst】 effect, choose whether to activate
   - Excess damage doesn't carry over to next Shield
3. **Has Base:** Deal damage to **Base**
   - Use counters to track damage
   - Base destroyed when HP ≤ 0
   - **<First Strike>** keyword: Base takes damage before normal timing

#### Attack on Unit (Rule 8-5-3)
- **Simultaneous damage:** Both Units deal damage = their AP to each other
- Use counters to track damage
- Unit destroyed when HP ≤ 0
- **<First Strike>** keyword: Attacking Unit deals damage first (if enemy destroyed, attacking Unit takes no damage)
- **Both destroyed:** Destruction is simultaneous

### 5. BATTLE END STEP (Rule 8-6)
- "During this battle" effects end
- Return to Main Phase

---

## 🎬 Action Steps (Rules 9) ⭐ IMPORTANT

**When:** During End Phase Action Step AND during Battle Action Step

**How:**
1. **Standby player** may: Activate 【Action】 Command OR 【Activate･Action】 effect OR Pass
2. **Active player** may: Activate 【Action】 Command OR 【Activate･Action】 effect OR Pass
3. Repeat back and forth until **both players pass consecutively**

**Then:** Action Step ends

---

## 🔧 Effect Activation and Resolution (Rules 10) ⭐ CRITICAL

### Effect Types

#### 1. CONSTANT EFFECTS (Rule 10-1-5)
- Always active while in valid location
- No triggering needed
- When multiple conflict, "can't" effects take precedence

#### 2. TRIGGERED EFFECTS (Rule 10-1-6)
**Keywords:** 【Deploy】, 【Attack】, 【Destroyed】, 【When Paired】, 【When Linked】
- Activate automatically when conditions met
- Can activate each time (unless 【Once per Turn】)
- If multiple trigger:
  - Same owner: Resolve in owner's chosen order
  - Both players: Active player's effects first, then standby player's
  - New triggers during resolution: Resolve immediately (stack)
  - **【Burst】 effects: Always resolve first (highest priority)**

#### 3. ACTIVATED EFFECTS (Rule 10-1-7)
**Keywords:** 【Activate･Main】, 【Activate･Action】
- Manually activated by player
- Format: `【Activate】 (condition): (effect)`
- **①** symbol = pay cost equal to number in symbol
- Multiple conditions = must satisfy all

#### 4. COMMAND EFFECTS (Rule 10-1-8)
**Keywords:** 【Main】, 【Action】
- Activated by playing Command card at specified timing
- Cannot play if target cannot be chosen (for effects before "Then"/"If you do")

#### 5. SUBSTITUTION EFFECTS (Rule 10-1-9)
- "Do B instead of A" format
- Replaces one event with another

### Effect Resolution Priority
1. **【Burst】** effects (highest priority)
2. New triggers during resolution (stack-based)
3. Active player's triggered effects
4. Standby player's triggered effects

### "If you do" vs "Then" (Rule 5-20) ⭐ IMPORTANT
- **"If you do"**: Second part only happens if first part fully resolved
- **"Then"**: Second part happens even if first part failed

---

## ⚖️ Rules Management (Rules 11) ⭐ AUTOMATIC CHECKS

**Triggers:** Immediately when specific events occur (highest priority)

### Check Order:
1. **Defeat Check** (Rule 11-2)
   - Battle damage while no shields → defeated
   - No cards in deck → defeated
   - If multiple players defeated → all lose

2. **Destruction Management** (Rule 11-3)
   - HP ≤ 0 → destroyed → trash
   - Shields have 1 HP each

3. **Battle Area Excess** (Rule 11-4)
   - Max 6 Units
   - If deploying when full → choose 1 to trash (NOT destroyed)

4. **Base Section Excess** (Rule 11-5)
   - Max 1 Base
   - If deploying when full → choose 1 to trash (NOT destroyed)

---

## 🔑 Keyword Effects (Rules 13-1)

### <Repair X> (Rule 13-1-1)
"At the end of your turn, this Unit recovers X HP."
- Multiple copies stack (add values)

### <Breach X> (Rule 13-1-2)
"When this Unit destroys enemy Unit with battle damage during your turn, deal X damage to first card in opponent's shield area."
- Targets Base if present, otherwise top Shield
- Activates even if both Units destroyed
- Multiple copies stack

### <Support X> (Rule 13-1-3)
"【Activate･Main】Rest this Unit: Choose 1 other friendly Unit. It gets AP+X during this turn."
- Multiple copies stack

### <Blocker> (Rule 13-1-4)
"During block step, may rest this Unit to redirect attack to this Unit."
- Can only activate during block step
- Cannot stack (only have once)

### <First Strike> (Rule 13-1-5)
"Deals battle damage before enemy during damage step."
- If enemy destroyed by First Strike, attacking Unit takes no damage
- Cannot stack

### <High-Maneuver> (Rule 13-1-6)
"While attacking, enemy Units cannot activate <Blocker>."
- Cannot stack

### <Suppression> (Rule 13-1-7)
"Deals damage to first TWO Shields simultaneously when dealing battle damage to Shield."
- If 2 Shields destroyed, reveal both, resolve 【Burst】 in owner's chosen order
- Cannot stack

---

## 🎲 Game Setup (Rules 6)

1. **Deck Construction:**
   - 50 cards (Unit/Pilot/Command/Base)
   - 10 Resource cards
   - 1-2 colors only
   - Max 4 copies of same card (in deck)

2. **Pre-Game:**
   - Shuffle deck, place in deck area
   - Place resource deck in resource deck area
   - Determine Player One (winner of rock-paper-scissors decides)
   - Draw 5 cards (starting hand)
   - Mulligan option: Player One first, then Player Two (shuffle entire hand back, draw 5 new)
   - Place top 6 cards of deck face-down as Shields (overlapping)
   - Place 1 EX Base token (0 AP, 3 HP) in Base Section
   - **Player Two only:** Place 1 EX Resource token in Resource Area

3. **Game Start:** Player One's turn begins

---

## 📝 Important Rules Details

### Units (Rule 3-2)
- **Summoning Sickness:** Cannot attack turn deployed (unless Link Unit)
- **Link Unit:** Unit with Pilot meeting Link Condition → can attack immediately
- **Link Condition:** Brackets like [Garrod Ran] match if Pilot name contains text

### Pilots (Rule 3-3)
- Max 1 Pilot per Unit
- When Unit moves zones, Pilot moves with it
- Pilot traits NOT added to Unit
- Two card texts: Above name (Pilot effect), Below name (Unit gains while paired)

### Active vs Rested (Rule 5-4)
- **Active:** Vertical orientation
- **Rested:** Horizontal orientation
- Cards enter field as Active (unless specified)

### Tokens (Rule 5-17)
- Lv = 0, Cost = 0, No color
- When moved to non-field zone → removed from game (momentarily enters zone for triggers)

### Fundamental Rules (Rule 1-3)
- Card text > Comprehensive rules
- If action impossible, don't do it (partial = do as much as possible)
- Can't put entity into state it's already in (Rule 1-3-2-1)
- Simultaneous choices: Active player chooses first

---

## 🎯 Quick Combat Reference

### Can Attack:
- Player (opponent) ✓
- Rested enemy Unit ✓

### Cannot Attack:
- Active enemy Unit ✗
- Your own Units ✗

### Damage Rules:
- Unit to Unit: Simultaneous (unless <First Strike>)
- Unit to Player: Only if no Shields/Base OR Base survives
- Shield: 1 HP each
- Excess damage does NOT carry over between Shields

---

## 📊 Timing Keywords Summary

| Keyword | Timing | Type |
|---------|--------|------|
| 【Main】 | Main Phase (active player) | Command |
| 【Action】 | Action Step (alternating) | Command |
| 【Activate･Main】 | Main Phase (while not attacking) | Activated |
| 【Activate･Action】 | Action Step | Activated |
| 【Deploy】 | When deployed to field | Triggered |
| 【Attack】 | Attack Step | Triggered |
| 【Destroyed】 | When destroyed → trash | Triggered |
| 【When Paired】 | When Pilot paired | Triggered |
| 【When Linked】 | When Link condition met | Triggered |
| 【During Pair】 | While Pilot paired | Continuous |
| 【During Link】 | While Link condition met | Continuous |
| 【Burst】 | When Shield destroyed | Triggered (highest priority) |
| 【Once per Turn】 | Restriction modifier | Limit |

---

## 🚨 Common Mistakes to Avoid

1. ❌ Attacking with rested Units
2. ❌ Attacking active enemy Units
3. ❌ Forgetting summoning sickness (unless Link Unit)
4. ❌ Carrying excess Shield damage to next Shield
5. ❌ Playing cards without meeting Lv requirement
6. ❌ Forgetting Rules Management (defeat/destruction checks)
7. ❌ Resolving triggered effects in wrong order (Active player first)
8. ❌ Missing 【Burst】 priority (always resolves first)
9. ❌ Treating "If you do" same as "Then"
10. ❌ Forgetting hand limit during Hand Step (max 10)

---

**For full details, refer to `gamerules.txt` with specific rule numbers.**
