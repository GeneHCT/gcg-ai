"""
Comprehensive validation test runner
Tests card conversions against original text to verify accuracy
"""
import json
from pathlib import Path
from test_cases import CardValidator
import sys


def main():
    """Run validation tests on sample cards"""
    
    # Sample of 80 diverse cards (including problem cards and various patterns)
    # This is a representative sample covering all card types and effect patterns
    sample_cards = [
        # Problem cards that were fixed
        "GD02-003", "GD02-057", "GD01-066", "GD01-046",
        
        # Previously passing cards (from original test set)
        "GD01-007", "GD01-008", "GD01-009", "GD01-012",
        "GD01-014", "GD01-024", "GD01-025", "GD01-028",
        "GD01-029", "GD01-032", "GD01-033", "GD01-034",
        "GD01-038", "GD01-043", "GD01-044", "GD01-045",
        "GD01-048", "GD01-049", "GD01-052", "GD01-053",
        "GD01-055", "GD01-056", "GD01-058", "GD01-059",
        
        # Additional diverse cards
        "GD01-001", "GD01-002", "GD01-003", "GD01-004",
        "GD01-005", "GD01-006", "GD01-010", "GD01-015",
        "GD01-016", "GD01-017", "GD01-019", "GD01-020",
        "GD01-023", "GD01-026", "GD01-027", "GD01-030",
        "GD01-039", "GD01-041", "GD01-042", "GD01-047",
        "GD01-050", "GD01-054", "GD01-061", "GD01-063",
        "GD01-065", "GD01-067", "GD01-068", "GD01-069",
        "GD01-070", "GD01-071", "GD01-072", "GD01-073",
        
        # GD02 set samples
        "GD02-001", "GD02-002", "GD02-004", "GD02-005",
        "GD02-006", "GD02-007", "GD02-008", "GD02-009",
        "GD02-010", "GD02-011", "GD02-014", "GD02-016",
        
        # Starter deck cards (different patterns)
        "ST02-012", "ST03-001", "ST04-014", "ST08-012"
    ]
    
    # Get test mode from args
    test_all = '--all' in sys.argv
    
    if test_all:
        # Load all cards with effects
        with open('card_database/all_cards.json', 'r') as f:
            all_cards = json.load(f)
        test_cards = [card['ID'] for card in all_cards if card.get('Effect')]
        print(f"Testing ALL {len(test_cards)} cards with effects\n")
    else:
        test_cards = sample_cards
        print(f"Testing sample of {len(test_cards)} cards\n")
    
    # Initialize validator
    validator = CardValidator()
    
    # Run validation
    passed = 0
    failed = 0
    errors = []
    
    print("Running validation tests...")
    
    for i, card_id in enumerate(test_cards, 1):
        # Show progress
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(test_cards)} ({passed} passed, {failed} failed)")
        
        try:
            # Load original card
            card_path = Path('card_database') / f'{card_id}.json'
            if not card_path.exists():
                continue
            
            with open(card_path, 'r') as f:
                original_card = json.load(f)
            
            # Load converted effect
            effect_path = Path('card_effects_converted') / card_id
            if not effect_path.exists():
                failed += 1
                errors.append({
                    'card_id': card_id,
                    'error': 'Conversion file not found'
                })
                continue
            
            with open(effect_path, 'r') as f:
                converted_effect = json.load(f)
            
            # Validate
            result = validator.validate_card(original_card, converted_effect)
            
            if result.get('status') == 'PASSED':
                passed += 1
            else:
                failed += 1
                errors.append({
                    'card_id': card_id,
                    'errors': result.get('errors', []),
                    'stats': result.get('validation_stats')
                })
        
        except Exception as e:
            failed += 1
            errors.append({
                'card_id': card_id,
                'error': f"Exception: {str(e)}"
            })
    
    # Print results
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    
    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTotal Cards Tested: {total}")
    print(f"Passed: {passed} ({pass_rate:.1f}%)")
    print(f"Failed: {failed} ({100-pass_rate:.1f}%)")
    
    if errors:
        print(f"\n\nFailed Cards ({len(errors)}):")
        print("-" * 80)
        
        for error_info in errors:  # Show all failures
            card_id = error_info['card_id']
            print(f"\n{card_id}:")
            
            if 'error' in error_info:
                print(f"  Error: {error_info['error']}")
            elif 'errors' in error_info:
                for err in error_info['errors'][:2]:  # Show first 2 errors per card
                    print(f"  - [{err['category']}] {err['error']}")
    
    # Summary stats
    if errors and 'stats' in errors[0]:
        print("\n\nCategory Statistics:")
        print("-" * 80)
        
        categories = ['triggers', 'conditions', 'actions', 'keywords', 'continuous_effects']
        for category in categories:
            total_passed = 0
            total_checks = 0
            
            for error_info in errors:
                if 'stats' in error_info:
                    stats = error_info['stats'].get(category, {})
                    total_passed += stats.get('passed', 0)
                    total_checks += stats.get('total_checks', 0)
            
            if total_checks > 0:
                accuracy = (total_passed / total_checks * 100)
                print(f"{category:20s}: {total_passed:3d}/{total_checks:3d} ({accuracy:5.1f}%)")
    
    print("\n" + "="*80)
    
    # Return exit code based on pass rate
    if pass_rate >= 95:
        print("✅ VALIDATION PASSED - 95%+ accuracy achieved!")
        return 0
    else:
        print(f"⚠️  VALIDATION NEEDS IMPROVEMENT - {pass_rate:.1f}% accuracy")
        return 1


if __name__ == "__main__":
    sys.exit(main())
