# Gundam Card Game Simulator (GCG-AI)

A Python-based simulator for the Gundam Card Game, including card database management and game logic implementation.

## Project Structure

```
gcg-ai/
├── venv/                   # Python virtual environment
├── card_database/          # Card data storage
│   ├── all_cards.json     # All cards in one file
│   ├── *.json             # Individual card files (by ID)
│   └── test_cases.py      # Test suite for card validation
├── simulator/             # Game logic modules
│   ├── gamestate.py       # Game state management
│   ├── link_mechanic.py   # Link mechanic implementation
│   ├── mainphase.py       # Main phase logic
│   └── resource_logic.py  # Resource management
├── scrape_cards.py        # Web scraper for card data
├── cards_structure.txt    # Card data structure definition
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Setup

### 1. Create Virtual Environment

The project uses a Python virtual environment to manage dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Dependencies

- `requests` - HTTP library for web requests
- `beautifulsoup4` - HTML parsing
- `lxml` - XML/HTML parser
- `selenium` - Browser automation (optional, for advanced scraping)
- `webdriver-manager` - Automatic webdriver management
- `requests-html` - Alternative scraping library

## Card Database

### Card Structure

Each card follows this structure (defined in `cards_structure.txt`):

```
Name: Str           # Card name
ID: Str             # Unique card identifier
Effect: List[Str]   # Card effects (can be empty)
Color: Str          # Card color
Type: Str           # Card type (Unit, Command, Pilot, etc.)
Rarity: Str         # Rarity (C, U, R, RR, etc.)
Traits: List[Str]   # Card traits
Level: Int          # Level (null for non-units)
Cost: Int           # Cost to play
Ap: Int             # Attack Points (null for non-units)
Hp: Int             # Health Points (null for non-units)
Block: Int          # Block value (null for non-units)
Zones: List[Str]    # Valid zones (Space, Earth, etc.)
Link: List[Str]     # Link targets (optional)
Set: Str            # Set identifier
```

### Example Card

```json
{
  "Name": "Freedom Gundam",
  "ID": "GD01-001",
  "Effect": [
    "[Triple Ship Attack] This Unit can change the attack target to 3 enemy Units."
  ],
  "Color": "Blue",
  "Type": "Unit",
  "Rarity": "R",
  "Traits": ["Mobile Suit", "Earth Federation"],
  "Level": 7,
  "Cost": 1,
  "Ap": 11,
  "Hp": 11,
  "Block": 2,
  "Zones": ["Space"],
  "Link": [],
  "Set": "GD01"
}
```

## Usage

### Scraping Cards

Run the web scraper to fetch card data:

```bash
python scrape_cards.py
```

**Note:** The current implementation generates sample cards based on the Gundam Card Game structure. For scraping real data from https://exburst.dev/gundam/cardlist, you may need:

1. A proper Chrome/Chromium installation for Selenium
2. To reverse engineer the website's API endpoints
3. Permission from the website owners

### Testing Card Data

Validate the card database structure:

```bash
python card_database/test_cases.py
```

This will:
- Check all required fields exist
- Validate data types
- Verify card-type-specific requirements
- Report any structural errors

### Current Sample Cards

The database includes sample cards representing different types:

- **Units:** Freedom Gundam, Strike Gundam, Ball, Zaku II, etc.
- **Commands:** Counterattack, A Show of Resolve
- **Pilots:** Amuro Ray

These are based on actual Gundam Card Game cards and follow the official game structure.

## Development

### Adding New Cards

1. Create a JSON file following the card structure
2. Place it in `card_database/`
3. Add to `card_database/all_cards.json`
4. Run tests to validate: `python card_database/test_cases.py`

### Implementing Game Logic

Game logic modules are in the `simulator/` directory:

- `gamestate.py` - Main game state
- `link_mechanic.py` - Link card mechanics
- `mainphase.py` - Main phase actions
- `resource_logic.py` - Resource management

## Card Sets

Currently supported sets:

- **GD01** - First booster set
- **GD03** - Third booster set
- **GD04** - Fourth booster set
- **ST02** - Starter Deck 02
- **ST04** - Starter Deck 04
- **ST05** - Starter Deck 05
- **ST07** - Starter Deck 07
- **ST08** - Starter Deck 08

## Future Improvements

- [ ] Full web scraping implementation with proper browser automation
- [ ] Complete game simulator with all phases
- [ ] AI opponent implementation
- [ ] Deck builder interface
- [ ] Game replay system
- [ ] Tournament bracket management

## References

- Official Gundam Card Game: https://www.gundam-card.com/
- Card Database: https://exburst.dev/gundam/cardlist
- Comprehensive Rules: See `comprehensiverules_en.pdf`

## License

This project is for educational purposes. All Gundam Card Game content is ©BANDAI.

## Contributing

Contributions are welcome! Please ensure:

1. All cards follow the defined structure
2. Code passes existing tests
3. New features include tests
4. Documentation is updated
