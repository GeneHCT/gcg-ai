"""
Game Simulation with Random Agents and Detailed Logging

Runs a complete game with two random agents and logs everything
to a file for inspection and verification.
"""
import sys
from datetime import datetime
from typing import TextIO, Optional

from simulator.game_manager import GameManager, TurnManager, Phase, GameResult
from simulator.random_agent import RandomAgent, LegalActionGenerator, ActionExecutor, Action, ActionType
from simulator.effect_integration import EffectIntegration, patch_turn_manager


class GameLogger:
    """
    Handles detailed logging of game events.
    """
    
    def __init__(self, log_file: TextIO):
        """
        Initialize logger.
        
        Args:
            log_file: File object to write logs to
        """
        self.log_file = log_file
        self.turn_count = 0
        self.action_count = 0
    
    def log(self, message: str, indent: int = 0):
        """Write a log message"""
        indent_str = "  " * indent
        self.log_file.write(f"{indent_str}{message}\n")
        self.log_file.flush()
    
    def log_separator(self, char: str = "=", length: int = 80):
        """Write a separator line"""
        self.log(char * length)
    
    def log_header(self, title: str):
        """Write a section header"""
        self.log_separator()
        self.log(f"  {title}")
        self.log_separator()
    
    def log_game_start(self, manager: GameManager):
        """Log game initialization"""
        self.log_header("GAME START")
        game_state = manager.game_state
        
        self.log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Seed: {manager.seed}")
        self.log(f"Deterministic: {manager.is_deterministic()}")
        self.log("")
        
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            self.log(f"Player {player_id} Initial State:")
            self.log(f"  Main Deck: {len(player.main_deck)} cards", 1)
            self.log(f"  Resource Deck: {len(player.resource_deck)} cards", 1)
            self.log(f"  Hand: {len(player.hand)} cards", 1)
            
            # Show ALL cards in hand
            for i, card in enumerate(player.hand):
                self.log(f"    [{i+1}] {card.name} (ID: {card.id}, Lv{card.level}, Cost{card.cost})", 2)
            
            self.log(f"  Shields: {len(player.shield_area)} cards", 1)
            
            # Show shield cards
            for i, shield in enumerate(player.shield_area):
                self.log(f"    [{i+1}] {shield.name} (ID: {shield.id})", 2)
            
            self.log(f"  Bases: {len(player.bases)} (HP: {player.bases[0].current_hp if player.bases else 0})", 1)
            self.log(f"  EX Resources: {player.ex_resources}", 1)
            self.log("")
        
        self.log(f"Starting Player: Player {game_state.turn_player}")
        self.log("")
    
    def log_phase_transition(self, game_state, phase_name: str):
        """Log phase transition"""
        self.log_separator("-", 80)
        self.log(f">>> PHASE: {phase_name}")
        self.log_separator("-", 80)
        
        player = game_state.players[game_state.turn_player]
        self.log(f"Active Player: Player {game_state.turn_player}")
        self.log(f"  Hand: {len(player.hand)} cards", 1)
        self.log(f"  Resources: {player.get_total_resources()} (Active: {player.get_active_resources()}, EX: {player.ex_resources})", 1)
        self.log(f"  Battle Area: {len(player.battle_area)} units", 1)
        
        # Show base status
        if player.bases:
            base_hp = sum(b.current_hp for b in player.bases if b.current_hp > 0)
            self.log(f"  Bases: {len([b for b in player.bases if b.current_hp > 0])} active (Total HP: {base_hp})", 1)
        
        self.log(f"  Shields: {len(player.shield_area)}", 1)
        self.log("")
    
    def log_turn_start(self, game_state):
        """Log start of turn"""
        self.turn_count += 1
        self.log_separator("=", 80)
        self.log(f"TURN {game_state.turn_number} - Player {game_state.turn_player}'s Turn")
        self.log_separator("=", 80)
        self.log("")
    
    def log_legal_actions(self, legal_actions: list):
        """Log available legal actions"""
        self.log(f"Legal Actions Available: {len(legal_actions)}")
        
        # Group by type
        action_types = {}
        for action in legal_actions:
            action_type = action.action_type.value
            if action_type not in action_types:
                action_types[action_type] = []
            action_types[action_type].append(action)
        
        for action_type, actions in action_types.items():
            self.log(f"  {action_type}: {len(actions)} options", 1)
            
            # Show details for some action types
            if action_type == "play_unit" and len(actions) <= 5:
                for action in actions:
                    card = action.card
                    self.log(f"    - {card.name} (Lv{card.level}, Cost{card.cost}, AP{card.ap}/HP{card.hp})", 2)
            elif action_type == "attack_player":
                for action in actions:
                    unit = action.unit
                    self.log(f"    - {unit.card_data.name} (AP{unit.ap})", 2)
            elif action_type == "attack_unit" and len(actions) <= 5:
                for action in actions:
                    attacker = action.unit
                    defender = action.target
                    self.log(f"    - {attacker.card_data.name} -> {defender.card_data.name}", 2)
    
    def log_action_chosen(self, action: Action):
        """Log the chosen action"""
        self.action_count += 1
        self.log("")
        self.log(f"→ Action #{self.action_count}: {action}")
    
    def log_action_result(self, result: str):
        """Log the result of an action"""
        self.log(f"  Result: {result}", 1)
        self.log("")
    
    def log_game_state_summary(self, game_state):
        """Log current game state summary"""
        self.log("Current Game State:")
        
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            self.log(f"  Player {player_id}:", 1)
            self.log(f"    Hand: {len(player.hand)} cards", 2)
            self.log(f"    Deck: {len(player.main_deck)} cards", 2)
            self.log(f"    Resources: {player.get_total_resources()}", 2)
            self.log(f"    Battle Area: {len(player.battle_area)} units", 2)
            
            # Show units in battle
            for i, unit in enumerate(player.battle_area):
                status = "RESTED" if unit.is_rested else "ACTIVE"
                keywords = list(unit.keywords.keys()) if unit.keywords else []
                keywords_str = f" [{', '.join(keywords)}]" if keywords else ""
                self.log(f"      [{i+1}] {unit.card_data.name} ({status}, AP{unit.ap}, HP{unit.current_hp}/{unit.hp}){keywords_str}", 3)
            
            self.log(f"    Shields: {len(player.shield_area)} + {len(player.bases)} bases", 2)
            self.log(f"    Trash: {len(player.trash)} cards", 2)
        
        self.log("")
    
    def log_game_end(self, game_state):
        """Log game end"""
        self.log_separator("=", 80)
        self.log("GAME END")
        self.log_separator("=", 80)
        
        self.log(f"Result: {game_state.game_result.value}")
        self.log(f"Winner: Player {game_state.winner}")
        self.log(f"Total Turns: {game_state.turn_number}")
        self.log(f"Total Actions: {self.action_count}")
        self.log("")
        
        # Final state
        self.log("Final State:")
        for player_id in [0, 1]:
            player = game_state.players[player_id]
            self.log(f"  Player {player_id}:", 1)
            self.log(f"    Deck: {len(player.main_deck)} cards", 2)
            self.log(f"    Hand: {len(player.hand)} cards", 2)
            self.log(f"    Battle Area: {len(player.battle_area)} units", 2)
            self.log(f"    Shields: {len(player.shield_area)} + {len(player.bases)} bases", 2)
            self.log(f"    Trash: {len(player.trash)} cards", 2)
        
        self.log_separator("=", 80)


def create_test_deck(size: int = 50, prefix: str = "Card") -> list:
    """Create a test deck with varied cards"""
    deck = []
    
    for i in range(size):
        level = min((i // 5) + 1, 7)
        cost = min((i // 7), 6)
        ap = min(level, 6)
        hp = min(level, 6)
        
        colors = ['Blue', 'Red', 'Green', 'Yellow']
        color = colors[i % len(colors)]
        
        # Add some keywords to make it interesting
        effects = []
        if i % 5 == 0:
            effects.append(f'<Repair {min(level // 2, 2)}>')
        if i % 7 == 0:
            effects.append(f'<Breach {min(level // 3, 3)}>')
        if i % 11 == 0:
            effects.append('<First Strike>')
        if i % 13 == 0:
            effects.append('<Blocker>')
        
        deck.append({
            'Name': f'{color} {prefix} #{i:03d}',
            'ID': f'{prefix.upper()}-{i:03d}',
            'Type': 'UNIT',
            'Color': color,
            'Level': level,
            'Cost': cost,
            'Ap': ap,
            'Hp': hp,
            'Traits': ['Test Unit'],
            'Zones': ['Space', 'Earth'],
            'Link': [],
            'Effect': effects
        })
    
    return deck


def run_simulation(log_filename: str = "game_simulation.log", 
                   seed: Optional[int] = None,
                   max_turns: int = 50,
                   deck_p0: Optional[str] = None,
                   deck_p1: Optional[str] = None):
    """
    Run a complete game simulation with random agents.
    
    Args:
        log_filename: Name of log file to create
        seed: Random seed for reproducibility
        max_turns: Maximum number of turns before stopping
        deck_p0: Path to Player 0's deck file (optional)
        deck_p1: Path to Player 1's deck file (optional)
    """
    # Open log file
    with open(log_filename, 'w') as log_file:
        logger = GameLogger(log_file)
        
        # Initialize effect system
        logger.log("Initializing effect system...")
        EffectIntegration.initialize()
        patch_turn_manager()
        logger.log("")
        
        # Create game manager
        manager = GameManager(seed=seed)
        
        # Create or load decks
        if deck_p0 and deck_p1:
            # Load from deck files
            from simulator.deck_loader import DeckLoader
            
            logger.log(f"Loading deck for Player 0 from: {deck_p0}")
            deck_p0_cards, resource_p0_cards, valid_p0 = DeckLoader.load_deck_with_resource(deck_p0)
            logger.log(f"  Loaded {len(deck_p0_cards)} cards (valid: {valid_p0})")
            
            logger.log(f"Loading deck for Player 1 from: {deck_p1}")
            deck_p1_cards, resource_p1_cards, valid_p1 = DeckLoader.load_deck_with_resource(deck_p1)
            logger.log(f"  Loaded {len(deck_p1_cards)} cards (valid: {valid_p1})")
            logger.log("")
            
            if not valid_p0 or not valid_p1:
                logger.log("ERROR: Deck validation failed!")
                return
        else:
            # Generate test decks
            logger.log("Generating test decks...")
            deck_p0_cards = create_test_deck(50, "P0")
            deck_p1_cards = create_test_deck(50, "P1")
            resource_p0_cards = create_test_deck(10, "R0")
            resource_p1_cards = create_test_deck(10, "R1")
        
        # Setup game
        game_state = manager.setup_game(deck_p0_cards, deck_p1_cards, resource_p0_cards, resource_p1_cards)
        
        # Log game start
        logger.log_game_start(manager)
        
        # Create random agents
        agent_0 = RandomAgent(0, seed=seed)
        agent_1 = RandomAgent(1, seed=(seed + 1) if seed else None)
        agents = {0: agent_0, 1: agent_1}
        
        # Main game loop
        turn_number = 0
        while not game_state.is_terminal() and turn_number < max_turns:
            turn_number += 1
            
            # Log turn start
            logger.log_turn_start(game_state)
            
            current_player = game_state.turn_player
            agent = agents[current_player]
            
            # START PHASE
            logger.log_phase_transition(game_state, "START PHASE")
            game_state = TurnManager.start_phase(game_state)
            logger.log("All units reset to active", 1)
            logger.log("")
            
            # DRAW PHASE
            logger.log_phase_transition(game_state, "DRAW PHASE")
            deck_before = len(game_state.players[current_player].main_deck)
            game_state = TurnManager.draw_phase(game_state)
            
            if game_state.is_terminal():
                logger.log("DECK EMPTY - Game Over!", 1)
                break
            
            card_drawn = game_state.players[current_player].hand[-1] if deck_before > 0 else None
            if card_drawn:
                logger.log(f"Drew: {card_drawn.name}", 1)
            logger.log("")
            
            # RESOURCE PHASE
            logger.log_phase_transition(game_state, "RESOURCE PHASE")
            resource_before = len(game_state.players[current_player].resource_area)
            game_state = TurnManager.resource_phase(game_state)
            resource_after = len(game_state.players[current_player].resource_area)
            
            if resource_after > resource_before:
                logger.log(f"Added resource (Total: {resource_after})", 1)
            logger.log("")
            
            # MAIN PHASE
            logger.log_phase_transition(game_state, "MAIN PHASE")
            game_state.current_phase = Phase.MAIN
            
            # Main phase action loop
            main_phase_actions = 0
            max_main_phase_actions = 20  # Prevent infinite loops
            
            while main_phase_actions < max_main_phase_actions:
                # Get legal actions
                legal_actions = LegalActionGenerator.get_legal_actions(game_state)
                
                logger.log(f"Main Phase Action #{main_phase_actions + 1}")
                logger.log_legal_actions(legal_actions)
                
                # Agent chooses action
                chosen_action = agent.choose_action(game_state, legal_actions)
                logger.log_action_chosen(chosen_action)
                
                # End phase if chosen
                if chosen_action.action_type == ActionType.END_PHASE:
                    break
                
                # Pass
                if chosen_action.action_type == ActionType.PASS:
                    logger.log_action_result("Pass")
                    # Could allow multiple passes, but let's end phase for simplicity
                    break
                
                # Execute action
                game_state, result = ActionExecutor.execute_action(game_state, chosen_action)
                logger.log_action_result(result)
                
                # Check win condition
                if game_state.is_terminal():
                    logger.log("GAME OVER after action!", 1)
                    break
                
                main_phase_actions += 1
            
            if main_phase_actions >= max_main_phase_actions:
                logger.log(f"WARNING: Reached max main phase actions limit", 1)
            
            logger.log("")
            
            # END PHASE
            logger.log_phase_transition(game_state, "END PHASE")
            game_state = TurnManager.end_phase(game_state)
            
            # Repair
            player = game_state.players[current_player]
            units_with_repair = [u for u in player.battle_area if u.has_keyword("repair")]
            if units_with_repair:
                logger.log(f"Repair triggered for {len(units_with_repair)} units", 1)
                for unit in units_with_repair:
                    repair_value = unit.get_keyword_value("repair")
                    logger.log(f"  {unit.card_data.name} repaired {repair_value} HP", 2)
            
            # Hand limit check
            if len(player.hand) > 10:
                logger.log(f"Hand size: {len(player.hand)} (over limit of 10)", 1)
                num_to_discard = len(player.hand) - 10
                cards_to_discard = agent.choose_cards_to_discard(player.hand, num_to_discard)
                player.discard_to_limit(cards_to_discard)
                logger.log(f"Discarded {len(cards_to_discard)} cards", 1)
            
            logger.log("")
            
            # Log state summary
            logger.log_game_state_summary(game_state)
            
            # Switch turn
            game_state.turn_player = game_state.get_opponent_id(game_state.turn_player)
            game_state.turn_number += 1
            
            # Update manager
            manager.game_state = game_state
        
        # Check final win condition
        if not game_state.is_terminal():
            logger.log(f"Reached max turns ({max_turns})", 1)
        
        # Log game end
        logger.log_game_end(game_state)
        
        # Print to console too
        print(f"\n✓ Game simulation complete!")
        print(f"  Log file: {log_filename}")
        print(f"  Total turns: {turn_number}")
        print(f"  Total actions: {logger.action_count}")
        print(f"  Result: {game_state.game_result.value}")
        if game_state.winner is not None:
            print(f"  Winner: Player {game_state.winner}")


if __name__ == "__main__":
    # Run simulation with seed for reproducibility
    import sys
    
    seed = 42
    max_turns = 30
    log_file = "game_simulation.log"
    deck_p0 = None
    deck_p1 = None
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        seed = int(sys.argv[1])
    if len(sys.argv) > 2:
        max_turns = int(sys.argv[2])
    if len(sys.argv) > 3:
        log_file = sys.argv[3]
    if len(sys.argv) > 4:
        deck_p0 = sys.argv[4]
    if len(sys.argv) > 5:
        deck_p1 = sys.argv[5]
    
    print("=" * 60)
    print("GUNDAM CARD GAME - SIMULATION")
    print("=" * 60)
    print(f"Running simulation with seed {seed}...")
    print(f"Max turns: {max_turns}")
    print(f"Log file: {log_file}")
    if deck_p0 and deck_p1:
        print(f"Player 0 deck: {deck_p0}")
        print(f"Player 1 deck: {deck_p1}")
    else:
        print("Using generated test decks")
    print("")
    
    run_simulation(
        log_filename=log_file, 
        seed=seed, 
        max_turns=max_turns,
        deck_p0=deck_p0,
        deck_p1=deck_p1
    )
    
    print(f"\nYou can now inspect the log file: {log_file}")
    print(f"  cat {log_file}")
    print(f"  less {log_file}")
    print(f"  head -100 {log_file}")
