"""
Re-convert all cards after implementing validation fixes
"""
import json
import sys
from convert_card_effects import CardEffectConverter


def main():
    """Re-convert cards and show progress"""
    
    # Read the validation report to get failed cards
    try:
        with open('validation_report.json', 'r') as f:
            report = json.load(f)
        
        failed_cards = [card['card_id'] for card in report['failed_cards']]
        print(f"Found {len(failed_cards)} failed cards to re-convert")
    except FileNotFoundError:
        print("No validation report found. Converting all cards from database...")
        # Load all card IDs
        with open('card_database/all_cards.json', 'r') as f:
            all_cards = json.load(f)
        failed_cards = [card['ID'] for card in all_cards if card.get('Effect')]
    
    # Initialize converter
    converter = CardEffectConverter()
    
    # Re-convert failed cards
    print("\nRe-converting cards with updated logic...")
    success = 0
    errors = 0
    
    for card_id in failed_cards:
        try:
            converted = converter.convert_card(card_id)
            if converted:
                converter.save_effect(card_id, converted)
                success += 1
            else:
                errors += 1
                print(f"  ⚠ {card_id}: No effect data")
        except Exception as e:
            errors += 1
            print(f"  ✗ {card_id}: {str(e)}")
    
    print(f"\n✓ Re-conversion complete:")
    print(f"  Success: {success}")
    print(f"  Errors: {errors}")
    
    # Optionally: Convert ALL cards if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        print("\n" + "="*80)
        print("Converting ALL cards from database...")
        print("="*80)
        
        with open('card_database/all_cards.json', 'r') as f:
            all_cards = json.load(f)
        
        all_card_ids = [card['ID'] for card in all_cards if card.get('Effect')]
        print(f"Found {len(all_card_ids)} cards with effects")
        
        success_all = 0
        errors_all = 0
        
        for i, card_id in enumerate(all_card_ids, 1):
            if i % 50 == 0:
                print(f"  Progress: {i}/{len(all_card_ids)}")
            
            try:
                converted = converter.convert_card(card_id)
                if converted:
                    converter.save_effect(card_id, converted)
                    success_all += 1
                else:
                    errors_all += 1
            except Exception as e:
                errors_all += 1
                print(f"  ✗ {card_id}: {str(e)}")
        
        print(f"\n✓ Full conversion complete:")
        print(f"  Success: {success_all}/{len(all_card_ids)}")
        print(f"  Errors: {errors_all}")


if __name__ == "__main__":
    main()
