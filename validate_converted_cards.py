"""
Card Conversion Validation Suite
Main test runner that validates converted card effects against original card text
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from test_cases import CardValidator
from card_samples import CardSampleSelector


class CardConversionValidator:
    """Main validator for card effect conversions"""
    
    def __init__(self, 
                 card_database_path: str = "card_database/all_cards.json",
                 effects_dir: str = "card_effects_converted"):
        self.card_database_path = card_database_path
        self.effects_dir = effects_dir
        self.validator = CardValidator()
        self.sample_selector = CardSampleSelector()
        
        # Load all cards
        with open(card_database_path, 'r') as f:
            self.all_cards = json.load(f)
        
        # Create card lookup by ID
        self.cards_by_id = {card['ID']: card for card in self.all_cards}
    
    def load_converted_effect(self, card_id: str) -> Optional[Dict]:
        """Load converted effect JSON for a card"""
        effect_path = Path(self.effects_dir) / card_id
        
        if not effect_path.exists():
            return None
        
        try:
            with open(effect_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading {card_id}: {e}")
            return None
    
    def validate_card(self, card_id: str) -> Dict:
        """Validate a single card conversion"""
        # Get original card data
        original_card = self.cards_by_id.get(card_id)
        if not original_card:
            return {
                "card_id": card_id,
                "status": "ERROR",
                "error": "Card not found in database"
            }
        
        # Load converted effect
        converted_effect = self.load_converted_effect(card_id)
        if not converted_effect:
            return {
                "card_id": card_id,
                "card_name": original_card.get("Name", "Unknown"),
                "status": "ERROR",
                "error": "No converted effect file found"
            }
        
        # Run validation
        result = self.validator.validate_card(original_card, converted_effect)
        
        # Add card metadata
        result["card_id"] = card_id
        result["card_name"] = original_card.get("Name", "Unknown")
        result["card_type"] = original_card.get("Type", "Unknown")
        
        return result
    
    def validate_sample(self, card_ids: List[str]) -> Dict:
        """Validate a sample of cards and generate report"""
        results = {
            "metadata": {
                "validation_date": datetime.now().isoformat(),
                "total_cards_tested": len(card_ids),
                "validator_version": "1.0"
            },
            "summary": {
                "total_cards_tested": len(card_ids),
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "pass_rate": "0%",
                "by_category": {
                    "triggers": {"passed": 0, "failed": 0, "total_checks": 0},
                    "conditions": {"passed": 0, "failed": 0, "total_checks": 0},
                    "actions": {"passed": 0, "failed": 0, "total_checks": 0},
                    "targets": {"passed": 0, "failed": 0, "total_checks": 0},
                    "keywords": {"passed": 0, "failed": 0, "total_checks": 0},
                    "continuous_effects": {"passed": 0, "failed": 0, "total_checks": 0}
                }
            },
            "failed_cards": [],
            "warnings": [],
            "passed_cards": []
        }
        
        # Validate each card
        for card_id in card_ids:
            print(f"Validating {card_id}...")
            card_result = self.validate_card(card_id)
            
            # Count by status
            if card_result.get("status") == "ERROR":
                results["summary"]["errors"] += 1
                results["failed_cards"].append(card_result)
            elif card_result.get("errors"):
                results["summary"]["failed"] += 1
                results["failed_cards"].append(card_result)
            else:
                results["summary"]["passed"] += 1
                results["passed_cards"].append({
                    "card_id": card_result["card_id"],
                    "card_name": card_result["card_name"]
                })
            
            # Aggregate category stats
            for category, stats in card_result.get("validation_stats", {}).items():
                if category in results["summary"]["by_category"]:
                    cat_stats = results["summary"]["by_category"][category]
                    cat_stats["passed"] += stats.get("passed", 0)
                    cat_stats["failed"] += stats.get("failed", 0)
                    cat_stats["total_checks"] += stats.get("total_checks", 0)
            
            # Collect warnings
            if card_result.get("warnings"):
                for warning in card_result["warnings"]:
                    warning["card_id"] = card_result["card_id"]
                    warning["card_name"] = card_result["card_name"]
                    results["warnings"].append(warning)
        
        # Calculate pass rate
        tested = results["summary"]["total_cards_tested"]
        passed = results["summary"]["passed"]
        if tested > 0:
            results["summary"]["pass_rate"] = f"{(passed / tested * 100):.2f}%"
        
        return results
    
    def save_report(self, results: Dict, output_path: str = "validation_report.json"):
        """Save validation report to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Report saved to {output_path}")
    
    def print_summary(self, results: Dict):
        """Print human-readable summary"""
        summary = results["summary"]
        
        print("\n" + "="*80)
        print("CARD CONVERSION VALIDATION REPORT")
        print("="*80)
        print(f"\nTotal Cards Tested: {summary['total_cards_tested']}")
        print(f"Passed: {summary['passed']} ({summary['pass_rate']})")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        
        print("\n" + "-"*80)
        print("BY CATEGORY:")
        print("-"*80)
        
        for category, stats in summary["by_category"].items():
            total = stats["total_checks"]
            if total > 0:
                passed = stats["passed"]
                failed = stats["failed"]
                rate = (passed / total * 100) if total > 0 else 0
                print(f"{category.upper():20s} | Checks: {total:3d} | Passed: {passed:3d} | Failed: {failed:3d} | Rate: {rate:5.1f}%")
        
        print("\n" + "-"*80)
        print(f"FAILED CARDS: {len(results['failed_cards'])}")
        print("-"*80)
        
        for card in results["failed_cards"][:10]:  # Show first 10
            print(f"\n{card['card_id']}: {card['card_name']}")
            if card.get("errors"):
                for error in card["errors"][:3]:  # Show first 3 errors per card
                    print(f"  ⚠ [{error['category']}] {error['error']}")
        
        if len(results["failed_cards"]) > 10:
            print(f"\n... and {len(results['failed_cards']) - 10} more (see JSON report)")
        
        print("\n" + "-"*80)
        print(f"WARNINGS: {len(results['warnings'])}")
        print("-"*80)
        
        for warning in results["warnings"][:5]:  # Show first 5 warnings
            print(f"  • {warning['card_id']}: {warning['message']}")
        
        if len(results["warnings"]) > 5:
            print(f"  ... and {len(results['warnings']) - 5} more (see JSON report)")
        
        print("\n" + "="*80)


def main():
    """Main entry point"""
    print("Card Conversion Validation Suite")
    print("-" * 80)
    
    # Initialize validator
    validator = CardConversionValidator()
    
    # Select sample cards
    print("\nSelecting card sample...")
    sample_selector = CardSampleSelector()
    sample_cards = sample_selector.select_stratified_sample(
        validator.cards_by_id,
        validator.effects_dir
    )
    
    print(f"Selected {len(sample_cards)} cards for validation")
    print(f"  Simple: {len(sample_selector.get_simple_cards(sample_cards, validator.cards_by_id))}")
    print(f"  Medium: {len(sample_selector.get_medium_cards(sample_cards, validator.cards_by_id))}")
    print(f"  Complex: {len(sample_selector.get_complex_cards(sample_cards, validator.cards_by_id))}")
    
    # Run validation
    print("\nRunning validation...")
    results = validator.validate_sample(sample_cards)
    
    # Save and display results
    validator.save_report(results, "validation_report.json")
    validator.print_summary(results)


if __name__ == "__main__":
    main()
