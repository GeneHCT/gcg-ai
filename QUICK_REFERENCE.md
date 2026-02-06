# Gundam Card Game Simulator - Quick Reference

## 🎮 Project Overview
Complete card database with 564 unique Gundam Card Game cards, ready for simulator integration.

## 📦 Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

## 🗃️ Card Database

### Database Statistics
- **Total Cards:** 564
- **Sets:** 11 (3 boosters + 8 starter decks)
- **Units:** 323 | **Commands:** 88 | **Pilots:** 63
- **Colors:** Blue (108), Red (115), Green (113), Purple (77), White (103)

### Quick Access

```python
from card_database.card_loader import CardDatabase

db = CardDatabase()

# Get card by ID
card = db.get_card_by_id("GD01-001")

# Search by name
results = db.search_cards("freedom")

# Filter
units = db.get_cards_by_type("UNIT")
blue_cards = db.get_cards_by_color("Blue")
gd01_cards = db.get_cards_by_set("GD01")
```

## 🧪 Testing

```bash
# Validate database
python card_database/test_cases.py

# Demo queries
python card_database/card_loader.py
```

## 🔄 Re-scraping

```bash
# Scrape all cards (takes ~8 minutes)
python scrape_cards_official.py

# Test mode (1 card per set)
# Edit scrape_cards_official.py: TEST_MODE = 1
```

## 📊 Files

- `card_database/all_cards.json` - Master file (all 564 cards)
- `card_database/GD*.json` - Booster set cards
- `card_database/ST*.json` - Starter deck cards
- `card_database/T-*.json` - Token cards
- `card_database/R-*.json` - Resource cards

## 🎯 Key Features

✅ All unique cards (no alt artwork duplicates)  
✅ Complete data (effects, stats, traits, links)  
✅ 100% validation pass rate  
✅ Ready for simulator integration  
✅ Fast query utilities  
✅ Comprehensive test suite

---

**Status:** Production Ready | **Last Updated:** Feb 7, 2026
