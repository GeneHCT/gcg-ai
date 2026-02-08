# TODO List

## To be checked
- Main phase: is it properly implemented according to GAME_RULES_QUICK_REFERENCE.md lines:79-84 and gamerules.txt lines :299-312
- battle logs show all effects , i.e. ryusego deploy effect should show 1 damage dealt to which unit, what is the card drawn from the effect, and which card is discarded to the trash
- ryusego hp is paid but no effect (no trash)


## Completed
- ✓ Resource system - Fully implemented in resource_manager.py with proper Lv/Cost checking and resource resting
- ✓ Discard effect: does it place the card from Hand to Trash zone


## To be implemented:
- verify all rules (new context)
- gameflow full run
- Query jpgs for cards and visualization of gameplay for human inspection


## Future - Reinforcement Learning
- RL agent
- Strategies using different decks


## Proposed enhancement
### Battle System
- Burst Decision Logic: Currently uses 50% random; could use agent decision
- "During this battle" Effects: Framework exists but needs effect integration
- High-Maneuver Keyword: Prevent Blocker activation (implemented but needs testing)
- Battle Event Hooks: For more complex triggered effects during battle
- Battle Replay System: Record and replay battles for debugging