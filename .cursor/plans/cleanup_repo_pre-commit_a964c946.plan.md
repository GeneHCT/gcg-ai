---
name: Cleanup Repo Pre-Commit
overview: Identify and remove temporary documentation files, test scripts, and logs that were created during development iterations but are no longer needed before git commit. Keep only essential documentation and active code.
todos:
  - id: review-docs
    content: Review and categorize all documentation files based on current relevance
    status: pending
  - id: delete-progress
    content: Remove progress tracking and status documents (11 files)
    status: pending
  - id: delete-analysis
    content: Remove detailed analysis documents (5 files)
    status: pending
  - id: delete-guides
    content: Remove superseded guides and references (4 files)
    status: pending
  - id: delete-test-scripts
    content: Remove one-off test/validation scripts (4 files)
    status: pending
  - id: delete-utilities
    content: Remove helper scripts and artifacts (5 files)
    status: pending
  - id: delete-misc
    content: Remove miscellaneous files (3 files)
    status: pending
  - id: verify-essential
    content: Verify all essential files are preserved (README, code, data, tests)
    status: pending
isProject: false
---

# Cleanup Plan for Pre-Commit

## Analysis

Based on reviewing the project structure and git status, there are significant number of temporary/progress documentation files and validation artifacts that can be safely removed. The project has gone through multiple development iterations with progress tracking documents that are now superseded.

## Core Repository Structure (Keep)

The repository serves 4 main purposes:

1. **Scraping**: `scrape_cards_official.py` → `card_database/*.json`
2. **Conversion**: `convert_card_effects.py` → `card_effects_converted/*`
3. **Simulation**: `simulator/` package
4. **RL Training**: (future work)

## Files to KEEP

### Essential Documentation

- [`README.md`](README.md) - Main project documentation (well-written, current)
- [`TODO.md`](TODO.md) - Current task list
- [`.cursor/rules/tcg-logic.md`](.cursor/rules/tcg-logic.md) - Development rules (actively referenced)
- [`gamerules.txt`](gamerules.txt) - Official game rules (reference material)
- [`simulator/README.md`](simulator/README.md) - Simulator documentation

### Core Scripts (Stage 1-3)

- `scrape_cards_official.py` - Stage 1: Card scraping
- `convert_card_effects.py` - Stage 2: Effect conversion (2,019 lines, main converter)
- `test_cases.py` - Validation framework (actively used)
- `run_validation_tests.py` - Test runner
- All files in `simulator/` - Stage 3: Game simulation

### Data Directories

- `card_database/` - Scraped card data
- `card_effects_converted/` - Converted effects (324 files)
- `decks/` - Deck files for testing

## Files to DELETE

### Category 1: Progress/Status Documents (11 files)

These track development iterations and are superseded by current state:

- `CLEANUP_COMPLETE.md` - Previous cleanup summary
- `VALIDATION_FIXES_COMPLETE.md` - Fix summary (superseded by FINAL)
- `VALIDATION_RESULTS_FINAL.md` - Validation run (superseded by FINAL)
- `FINAL_VALIDATION_RESULTS.md` - Final validation (purpose served)
- `FIXES_COMPLETE_98_PERCENT.md` - Milestone document (superseded)
- `IMPLEMENTATION_COMPLETE_18_CARDS.md` - Implementation log (superseded)
- `SIMPLE_PATTERNS_IMPLEMENTATION_COMPLETE.md` - Implementation log (superseded)
- `ONCE_PER_TURN_IF_YOU_DO_TOKENS_COMPLETE.md` - Implementation log (superseded)
- `PILOT_TRAIT_ATTACK_TARGETING_COMPLETE.md` - Implementation log (superseded)
- `IMPLEMENTATION_SUMMARY_PILOT_ATTACK.md` - Duplicate summary (superseded)
- `REMAINING_30_CARDS.md` - Card list (work completed, now outdated)

### Category 2: Detailed Analysis Documents (5 files)

These were useful during development but are no longer needed:

- `card_conversion_validation_analysis.md` - Detailed validation analysis
- `HALLUCINATION_CORRECTIONS.md` - Error corrections log
- `DOCUMENTATION_INDEX.md` - Internal navigation guide (not needed in repo)
- `CARD_EFFECT_SCHEMA_PROPOSAL.md` - Schema proposal (now implemented)
- `JSON_SCHEMA_DEFINITION.md` - Schema definition (duplicate info)

### Category 3: Guides/References Superseded by README (2 files)

Information now consolidated in main README:

- `TESTING_GUIDE.md` - Testing instructions (can be in README)
- `VALIDATION_SUITE_README.md` - Validation docs (can be in README)

### Category 4: Supporting Reference Docs (2 files)

Useful during conversion work but not essential for repo:

- `IR_SCHEMA_DOCUMENTATION.md` - Comprehensive IR docs (very long, 787+ lines)
- `GAME_RULES_QUICK_REFERENCE.md` - Game rules summary (redundant with gamerules.txt)

### Category 5: One-off Test/Validation Scripts (4 files)

Temporary scripts used during specific implementation phases:

- `validate_18_cards.py` - One-time validation for specific card set
- `validate_converted_cards.py` - Old validation script (superseded by run_validation_tests.py)
- `test_new_actions.py` - Feature testing script
- `test_new_systems.py` - Feature testing script
- `test_effect_system.py` - Feature testing script

### Category 6: Utility Scripts (2 files)

Helper scripts that served their purpose:

- `reconvert_cards.py` - Utility to reconvert cards (useful but not essential)
- `card_samples.py` - Sample selection utility (used by validation, but not critical)

### Category 7: Artifacts (2 files)

Generated output files:

- `validation_report.json` - Test output (regenerated on each run)
- `PROJECT_SUMMARY.md` - Outdated project summary (info in README)

### Category 8: Miscellaneous (1 file)

- `cards_structure.txt` - Card structure notes (info captured in code/database)

## Summary

**Total files to delete: 32 files**

**Rationale:**

- Progress/status documents served their purpose during iterative development
- Implementation is now stable (98.5% accuracy achieved)
- Essential docs (README, gamerules.txt, TODO) provide sufficient context
- Test framework (`test_cases.py`, `run_validation_tests.py`) remains functional
- Conversion and simulation code fully preserved

**After cleanup, the repository will contain:**

- Core functionality: scraping, conversion, simulation
- Essential documentation: README, TODO, rules
- Test infrastructure: validation framework
- Data: card database, converted effects, decks
- ~15 focused documentation files instead of ~47 scattered docs

This creates a clean, maintainable repository ready for Stage 4 (RL agent development).