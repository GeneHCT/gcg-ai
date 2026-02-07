# Gundam Card Game AI

A complete reinforcement learning environment for the Gundam Card Game, featuring automated card scraping, effect conversion, and a production-ready game simulator.

## Overview

This project implements a full pipeline for training RL agents to play the Gundam Card Game:

```
Stage 1: Scrape Cards → Stage 2: Convert Effects → Stage 3: Simulate Game → Stage 4: Train RL Agent
   (565 cards)           (98.5% accuracy)          (Production Ready)         (Future Work)
```

### Current Status

- ✅ **Stage 1 Complete**: 565 cards scraped from official sources
- ✅ **Stage 2 Complete**: 474 card effects converted to machine-readable format (98.5% accuracy)
- ✅ **Stage 3 Complete**: Full game simulator with all rules implemented
- ⏳ **Stage 4 Pending**: RL agent training infrastructure

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd gcg-ai

# Install dependencies
pip install -r requirements.txt
```

### Run a Game Simulation

```bash
# Run a game with sample decks
python3 -m simulator.run_simulation 42 20 game.log decks/the-o.txt decks/tekkadan.txt
```

**Parameters:**
- `42` - Random seed (for reproducibility)
- `20` - Maximum turns
- `game.log` - Output log file
- `decks/the-o.txt` - Player 0's deck
- `decks/tekkadan.txt` - Player 1's deck

### Use the Simulator Programmatically

```python
from simulator.game_manager import GameManager
from simulator.deck_loader import DeckLoader

# Load decks
deck_p0, res_p0, _ = DeckLoader.load_deck_with_resource("decks/the-o.txt")
deck_p1, res_p1, _ = DeckLoader.load_deck_with_resource("decks/tekkadan.txt")

# Initialize game
manager = GameManager(seed=42)
game_state = manager.setup_game(deck_p0, deck_p1, res_p0, res_p1)

# Get observation for RL agent (368 features)
obs = manager.get_observation(player_id=0)

# Get legal actions
legal_actions = manager.get_legal_actions(player_id=0)
```

### Run Validation Tests

```bash
# Test card effect conversion accuracy
python3 run_validation_tests.py

# Test with all converted cards (takes longer)
python3 run_validation_tests.py --all
```

## Project Structure

```
gcg-ai/
├── card_database/              # Stage 1: Scraped card data
│   ├── all_cards.json          # 565 cards in unified JSON
│   └── *.json                  # Individual card files
│
├── card_effects_converted/     # Stage 2: Converted effect files
│   └── GD01-001, GD01-002...   # 474 card effect JSONs (no extension)
│
├── simulator/                  # Stage 3: Game engine
│   ├── game_manager.py         # Core game state and turn management
│   ├── gamestate.py            # Game state data structures
│   ├── effect_interpreter.py   # Card effect execution
│   ├── action_executor.py      # Game action execution
│   ├── trigger_manager.py      # Event-driven trigger system
│   ├── keyword_interpreter.py  # Keyword mechanics implementation
│   ├── unit.py                 # Card and unit classes
│   ├── deck_loader.py          # Deck file parser
│   ├── random_agent.py         # Random agent implementation
│   ├── run_simulation.py       # Simulation runner
│   └── README.md               # Detailed simulator documentation
│
├── decks/                      # Sample deck files
│   ├── the-o.txt
│   └── tekkadan.txt
│
├── scrape_cards_official.py    # Stage 1: Card scraper
├── convert_card_effects.py     # Stage 2: Effect converter (2,019 lines)
├── test_cases.py               # Validation framework
├── run_validation_tests.py     # Test runner
│
├── gamerules.txt               # Official comprehensive rules (Ver. 1.5.0)
├── GAME_RULES_QUICK_REFERENCE.md  # Quick rules lookup
├── IR_SCHEMA_DOCUMENTATION.md  # Card effect schema reference
├── TODO.md                     # Current development tasks
└── README.md                   # This file
```

## Pipeline Stages

### Stage 1: Card Scraping

**Purpose**: Extract card data from official sources into structured JSON format.

**Script**: `scrape_cards_official.py`

**Output**: 565 cards in `card_database/`
- `all_cards.json` - Complete card database
- Individual JSON files per card (e.g., `GD01-001.json`)

**Card Data Structure**:
```json
{
  "Name": "Freedom Gundam",
  "ID": "GD01-001",
  "Type": "Unit",
  "Color": "Blue",
  "Level": 7,
  "Cost": 1,
  "Ap": 11,
  "Hp": 11,
  "Traits": ["Mobile Suit", "SEED"],
  "Effect": ["【Deploy】Draw 1.", "【Attack】This Unit gains +2 AP."],
  "Keywords": ["<Repair 2>", "<Breach 2>"],
  "Link": ["(Kira Yamato)"],
  "Rarity": "RR",
  "Set": "GD01"
}
```

**Status**: ✅ Complete (565 cards)

### Stage 2: Card Effect Conversion

**Purpose**: Convert natural language card effects into machine-readable Intermediate Representation (IR) format for the simulator.

**Script**: `convert_card_effects.py` (2,019 lines)

**Output**: 474 effect files in `card_effects_converted/`

**Conversion Accuracy**: 98.5% overall
- **Triggers**: 100% accuracy (ON_DEPLOY, ON_ATTACK, ON_DESTROYED, etc.)
- **Actions**: 100% accuracy (DRAW, DAMAGE_UNIT, REST_UNIT, etc.)
- **Continuous Effects**: 100% accuracy (static modifiers)
- **Conditions**: 95%+ accuracy (trait checks, stat checks, etc.)

**IR Schema**: See [`IR_SCHEMA_DOCUMENTATION.md`](IR_SCHEMA_DOCUMENTATION.md) for complete reference.

**Example Conversion**:

Original text: `【Deploy】If you have 3 or more (Zeon) cards in play, draw 1.`

Converted IR:
```json
{
  "card_id": "GD01-007",
  "effects": [
    {
      "effect_id": "GD01-007-E1",
      "effect_type": "TRIGGERED",
      "triggers": ["ON_DEPLOY"],
      "conditions": [
        {
          "type": "COUNT_CARDS",
          "count": 3,
          "operator": ">=",
          "filters": {"traits": ["Zeon"], "zone": "field", "controller": "self"}
        }
      ],
      "actions": [
        {"type": "DRAW", "count": 1, "target": "self"}
      ]
    }
  ]
}
```

**Testing**: Run `python3 run_validation_tests.py` to validate conversions.

**Status**: ✅ Complete (474/474 cards converted)

### Stage 3: Game Simulation

**Purpose**: Execute full Gundam Card Game matches with complete rule implementation.

**Package**: `simulator/` (20+ modules, ~5,000 lines of code)

**Key Features**:
- **Complete Turn Flow**: All 5 phases (Start, Draw, Resource, Main, End)
- **Combat System**: Attack declarations, blocking, damage resolution
- **Keyword Mechanics**: Repair, Breach, Support, First Strike, High-Maneuver, Blocker, Suppression, Burst
- **Effect System**: Triggered effects, activated effects, continuous effects
- **Link/Pair System**: Unit-Pilot linking mechanics
- **Base System**: Base deployment and protection
- **Win Conditions**: Shield destruction, deck-out detection

**Game Rules**: Based on [Comprehensive Rules Ver. 1.5.0](gamerules.txt)
- Quick reference: [`GAME_RULES_QUICK_REFERENCE.md`](GAME_RULES_QUICK_REFERENCE.md)

**RL-Ready Features**:
- **Observation Space**: 368-dimensional feature vector
- **Legal Action Generation**: Dynamic action masking
- **Deterministic**: Seeded random number generation
- **State Serialization**: Full game state can be saved/restored

**Documentation**: See [`simulator/README.md`](simulator/README.md) for detailed documentation.

**Status**: ✅ Production-ready

### Stage 4: RL Agent Training

**Purpose**: Train reinforcement learning agents to play the game at competitive level.

**Status**: ⏳ Not yet started

**Planned Components**:
1. **Gym Environment Wrapper**: OpenAI Gym-compatible interface
2. **Action Space Definition**: Complete action encoding/decoding
3. **Reward Shaping**: Reward function design
4. **Training Infrastructure**: PPO, DQN, or other RL algorithms
5. **Evaluation Framework**: Agent performance metrics

**Next Steps**:
- Implement Gym environment wrapper
- Define complete action space encoding
- Design reward function
- Set up training pipeline
- Train baseline agents

## Game Rules Summary

### Setup
- 50-card main deck + 10-card resource deck
- Draw 5 initial cards
- Place 6 shields face-down from main deck
- Deploy 1 EX Base (0 AP / 3 HP) in base section
- Player 2 starts with 1 EX Resource

### Turn Flow
1. **Start Phase**: Reset all units to active, trigger start effects
2. **Draw Phase**: Draw 1 card
3. **Resource Phase**: Place 1 resource from resource deck
4. **Main Phase**: Play cards, activate effects, declare attacks
5. **End Phase**: Resolve end-of-turn effects, hand limit (10 cards)

### Combat
- Attack target: Opponent's player (hits shields/bases) OR rested enemy units
- **Blocker**: Can intercept attacks on player
- **First Strike**: Deals damage before counter-damage
- **High-Maneuver**: Cannot be blocked
- **Suppression**: Damages 2 shields simultaneously
- **Breach X**: Deal X extra shield damage when destroying a unit

### Win Conditions
1. Opponent receives battle damage from a unit while having 0 shields
2. Opponent's deck is empty when they need to draw

For complete rules, see [`gamerules.txt`](gamerules.txt) or [`GAME_RULES_QUICK_REFERENCE.md`](GAME_RULES_QUICK_REFERENCE.md).

## Development

### Requirements

- Python 3.8+
- Dependencies in `requirements.txt`:
  - `requests` - HTTP requests for scraping
  - `beautifulsoup4`, `lxml` - HTML parsing
  - `selenium` - Web automation (optional)

### Adding New Cards

1. **Scrape the card**: Add card ID to scraper or manually create JSON in `card_database/`
2. **Convert effects**: Run `python3 convert_card_effects.py <card_id>` or use the converter API
3. **Validate**: Run `python3 run_validation_tests.py` to check conversion accuracy
4. **Test in simulator**: Create a deck with the card and run a simulation

### Running Tests

```bash
# Run game simulation with test decks
python3 -m simulator.run_simulation

# Run with specific parameters
python3 -m simulator.run_simulation <seed> <max_turns> <log_file> <deck_p0> <deck_p1>

# Validate card conversions
python3 run_validation_tests.py

# Validate all cards (slower)
python3 run_validation_tests.py --all
```

### Deck Format

Create `.txt` files in `decks/` directory:

```
// Main Deck (50 cards total)
4x GD01-118
3x GD03-123
1x GD03-104
4x GD03-101
// ... (total 50 cards)

// Resource Deck (10 cards)
10x R-001
```

## Statistics

### Card Database
- **565 total cards** scraped from official sources
- **474 cards** with effect text (84% of database)
- **91 cards** without effects (vanilla units, basic resources)

### Effect Conversion
- **474/474 cards** successfully converted (100%)
- **98.5% validation accuracy** on sample set
- **100% accuracy** on core mechanics (triggers, actions, continuous effects)

### Simulator
- **368-dimensional** observation space for RL
- **~5,000 lines** of implementation code
- **20+ modules** across game engine, effects, and mechanics
- **All keyword mechanics** implemented
- **Complete rule coverage** from official rulebook Ver. 1.5.0

## Documentation

### Essential Documentation
- [`README.md`](README.md) - This file (project overview)
- [`TODO.md`](TODO.md) - Current development tasks
- [`gamerules.txt`](gamerules.txt) - Official comprehensive rules (Ver. 1.5.0)
- [`GAME_RULES_QUICK_REFERENCE.md`](GAME_RULES_QUICK_REFERENCE.md) - Quick rules lookup for developers

### Technical Documentation
- [`IR_SCHEMA_DOCUMENTATION.md`](IR_SCHEMA_DOCUMENTATION.md) - Card effect IR schema reference
- [`simulator/README.md`](simulator/README.md) - Detailed simulator documentation
- [`.cursor/rules/tcg-logic.md`](.cursor/rules/tcg-logic.md) - Development rules for AI coding assistance

### Code Documentation
All major modules include inline documentation:
- `convert_card_effects.py` - Effect converter implementation
- `simulator/game_manager.py` - Game state management
- `simulator/effect_interpreter.py` - Effect execution engine
- `simulator/action_executor.py` - Game action handlers

## Architecture

### Design Principles

1. **Schema-First Effects**: Card effects are data, not code. All effects are JSON files interpreted at runtime.
2. **Immutable State**: Game state uses immutability where possible for RL search trees.
3. **Deterministic**: All randomness uses seeded RNG for reproducibility.
4. **Decoupled**: Clear separation between game state, game engine, and effect interpreter.
5. **RL-Compatible**: Fixed-size observations, action masking, state serialization.

### Key Systems

- **Effect Interpreter**: Executes card effects from IR JSON files
- **Trigger Manager**: Event-driven system for effect triggers
- **Keyword Interpreter**: Implements keyword mechanics (Repair, Breach, etc.)
- **Action Executor**: Executes game actions (draw, damage, deploy, etc.)
- **Combat Manager**: Handles attack declarations and damage resolution
- **Link System**: Manages Unit-Pilot linking mechanics

## Contributing

This is a research project for TCG game AI development. Key areas for contribution:

1. **Card Database**: Add more cards from newer sets
2. **Effect Conversion**: Improve converter accuracy for edge cases
3. **Simulator**: Add missing mechanics or fix rule discrepancies
4. **RL Infrastructure**: Implement Stage 4 (Gym wrapper, training pipeline)
5. **Documentation**: Improve guides and examples

## License

[Add license information here]

## Acknowledgments

- Card data sourced from official Gundam Card Game materials
- Game rules based on Comprehensive Rules Ver. 1.5.0 (January 30, 2025)

---

**Current Status**: Ready for RL agent development (Stage 4)

**Last Updated**: February 8, 2026
