# ✅ Card Database Scraping Complete!

**Date:** February 7, 2026  
**Total Cards Scraped:** 564 unique cards  
**Source:** https://www.gundam-gcg.com/en/cards/  
**Alternative Artworks:** Excluded (not relevant for gameplay)

---

## 📊 Database Summary

### Cards by Set

**Booster Sets (430 cards):**
- **GD01 (Newtype Rising):** 139 cards
- **GD02 (Dual Impact):** 141 cards
- **GD03 (Steel Requiem):** 150 cards

**Starter Decks (134 cards):**
- **ST01 (Heroic Beginnings):** 19 cards
- **ST02 (Wings of Advance):** 18 cards
- **ST03 (Zeon's Rush):** 18 cards
- **ST04 (SEED Strike):** 19 cards
- **ST05 (Iron Bloom):** 15 cards
- **ST06 (Clan Unity):** 15 cards
- **ST07 (Celestial Drive):** 15 cards
- **ST08 (Flash of Radiance):** 15 cards

### Cards by Type
- **UNIT:** 323 cards
- **COMMAND:** 88 cards
- **PILOT:** 63 cards
- **BASE:** 42 cards
- **RESOURCE:** 28 cards
- **UNIT TOKEN:** 20 cards

### Cards by Color
- **Red:** 115 cards
- **Green:** 113 cards
- **Blue:** 108 cards
- **White:** 103 cards
- **Purple:** 77 cards
- **Colorless:** 48 cards

---

## 📁 File Structure

```
card_database/
├── all_cards.json          # All 564 cards (13,858 lines)
├── GD01-001.json           # Individual card files
├── GD01-002.json           # One file per unique card
├── ST01-001.json           # Includes starter decks
├── ...                     # 565 total files (564 cards + 1 master file)
├── card_loader.py          # Database query utilities
└── test_cases.py           # Validation test suite
```

---

## ✨ Card Data Structure

Each card contains complete information:
- **Name:** Card name
- **ID:** Unique identifier (e.g., "GD01-001", "ST01-001")
- **Effect:** List of card effects/abilities
- **Color:** Blue, Red, Green, Purple, White, or "-"
- **Type:** UNIT, COMMAND, PILOT, BASE, RESOURCE, UNIT TOKEN
- **Rarity:** C, U, R, LR, P
- **Traits:** List of card traits
- **Level:** Unit level (1-8, null for non-units)
- **Cost:** Cost to play the card
- **Ap:** Attack Points (for units)
- **Hp:** Health Points (for units)
- **Block:** Block value (for units)
- **Zones:** Valid zones (Space, Earth, etc.)
- **Link:** Link requirements/conditions
- **Set:** Set code

---

## 🧪 Validation Results

✅ **All 564 cards passed validation!**

- ✓ All required fields present
- ✓ Correct data types
- ✓ Card-type-specific validation passed
- ✓ No structural errors
- ✓ No duplicate cards (alternative artworks excluded)

---

## 🔍 Sample Cards

### Unit Card - Gundam (ST01-001)
```json
{
  "Name": "Gundam",
  "ID": "ST01-001",
  "Effect": [
    "<Repair 2> (At the end of your turn, this Unit recovers the specified number of HP.)",
    "【During Pair】During your turn, all your Units get AP+1."
  ],
  "Color": "Blue",
  "Type": "UNIT",
  "Rarity": "LR",
  "Traits": ["Earth Federation", "White Base Team"],
  "Level": 4,
  "Cost": 3,
  "Ap": 3,
  "Hp": 4,
  "Zones": ["Space", "Earth"],
  "Link": ["Amuro Ray"],
  "Set": "ST01"
}
```

### Pilot Card - Mikazuki Augus (ST05-010)
```json
{
  "Name": "Mikazuki Augus",
  "ID": "ST05-010",
  "Effect": [
    "【Burst】Add this card to your hand.",
    "【When Paired】Choose 1 of your Units and 1 enemy Unit. Deal 1 damage to them."
  ],
  "Color": "Purple",
  "Type": "PILOT",
  "Rarity": "C",
  "Traits": ["Tekkadan", "Alaya-Vijnana"],
  "Level": 4,
  "Cost": 1,
  "Ap": 2,
  "Hp": 1,
  "Set": "ST05"
}
```

### Unit - Psycho Gundam (GD02-001)
```json
{
  "Name": "Psycho Gundam",
  "ID": "GD02-001",
  "Effect": [
    "<Breach 3> (When this Unit's attack destroys an enemy Unit, deal the specified amount of damage to the first card in that opponent's shield area.)",
    "【During Pair･(Cyber-Newtype) Pilot】When one of your (Titans) Units destroys an enemy shield area card with damage, this Unit recovers 2 HP."
  ],
  "Color": "Blue",
  "Type": "UNIT",
  "Rarity": "LR",
  "Traits": ["Titans"],
  "Level": 6,
  "Cost": 4,
  "Ap": 4,
  "Hp": 5,
  "Zones": ["Space", "Earth"],
  "Link": ["Four Murasame"],
  "Set": "GD02"
}
```

---

## 🚀 Usage

### Load and Query Cards

```python
from card_database.card_loader import CardDatabase

# Load database
db = CardDatabase()

# Get card by ID
gundam = db.get_card_by_id("ST01-001")

# Search by name
gundams = db.search_cards("gundam")  # Returns 133 cards

# Filter by type
units = db.get_cards_by_type("UNIT")  # Returns 323 units

# Filter by color
blue_cards = db.get_cards_by_color("Blue")  # Returns 108 cards

# Filter by set
st05_cards = db.get_cards_by_set("ST05")  # Returns 15 cards

# Get statistics
stats = db.get_stats()
```

### Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run validation tests
python card_database/test_cases.py

# Run database demo
python card_database/card_loader.py
```

### Re-scrape Cards

```bash
# To re-scrape all cards
python scrape_cards_official.py

# To test with limited cards, edit scrape_cards_official.py:
# Change TEST_MODE = None to TEST_MODE = 5 (for 5 cards per set)
```

---

## 📝 Implementation Details

### Scraper Features
- ✓ Scrapes each set individually (required by website structure)
- ✓ Automatically skips alternative artwork cards (IDs ending with "_")
- ✓ Rate limiting (0.5s between requests, 2s between sets)
- ✓ Robust error handling
- ✓ Progress tracking
- ✓ Detailed logging

### Data Quality
- ✓ All 564 cards successfully scraped
- ✓ 100% validation pass rate
- ✓ Complete card information (effects, stats, traits, etc.)
- ✓ Proper data types (strings, integers, lists)
- ✓ Consistent formatting

### Alternative Artworks
Cards with IDs ending in "_" (e.g., "GD01-001_") are alternative artworks of the same card and have been excluded as they don't affect gameplay mechanics.

---

## 📈 Performance

- **Total scraping time:** ~8 minutes
- **Average time per card:** ~0.85 seconds
- **Success rate:** 100% (564/564 cards)
- **Data quality:** Perfect (all validation tests passed)
- **File count:** 565 files (564 individual + 1 master)
- **Total size:** ~2.5 MB

---

## 🎯 Database Statistics

**Total Unique Cards:** 564

**By Category:**
- Playable Units: 323 (57.3%)
- Support Cards: 88 Commands + 63 Pilots = 151 (26.8%)
- Infrastructure: 42 Bases + 28 Resources = 70 (12.4%)
- Special: 20 Unit Tokens (3.5%)

**Coverage:**
- ✓ All 3 booster sets (GD01, GD02, GD03)
- ✓ All 8 starter decks (ST01-ST08)
- ✓ Special promo cards (T-series, R-series)

---

## 🎮 Ready for Simulator Integration

The card database is now ready to be integrated with the game simulator:

```python
# Example: Load cards for deck validation
from card_database.card_loader import CardDatabase

db = CardDatabase()

# Get all units for a specific color
blue_units = [card for card in db.get_cards_by_color("Blue") 
              if card["Type"] == "UNIT"]

# Find cards with specific traits
earth_fed_cards = db.get_cards_with_trait("Earth Federation")

# Search for specific cards
strike_cards = db.search_cards("Strike")
```

---

## 📚 References

- **Official Website:** https://www.gundam-gcg.com/en/cards/
- **Card Database:** https://exburst.dev/gundam/cardlist
- **Official Rules:** See `comprehensiverules_en.pdf`
- **Game Rules:** See `gamerules.txt` and `gamerules_mainphase.txt`

---

## ✅ Project Completion Checklist

- [x] Virtual environment setup
- [x] Dependencies installed (requests, beautifulsoup4, lxml)
- [x] Web scraper implemented and tested
- [x] All 564 unique cards scraped
- [x] Alternative artworks excluded
- [x] All sets included (GD01-GD03, ST01-ST08)
- [x] Data validated (100% pass rate)
- [x] Test suite created and verified
- [x] Database utilities implemented
- [x] Query functions tested
- [x] Documentation complete

---

**Status: Production Ready** 🎉

**Next Steps:** Integrate with game simulator in `simulator/` directory
