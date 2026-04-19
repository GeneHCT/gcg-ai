#!/usr/bin/env python3
"""
Gundam Card Game Official Website Scraper
Scrapes card data from https://www.gundam-gcg.com/en/cards/
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
import re
import time
from typing import Dict, List, Any, Optional

# XPath for card image on detail page (e.g. GD01-001 from gundam-gcg.com/en/cards/)
CARD_IMAGE_XPATH = "/html/body/main/article/div[1]/div[3]/div/div/div/img"


class OfficialGundamScraper:
    """Scraper for official Gundam Card Game website"""
    
    def __init__(self, output_dir: str = "card_database"):
        self.base_url = "https://www.gundam-gcg.com"
        self.cards_url = f"{self.base_url}/en/cards/"
        self.detail_url = f"{self.base_url}/en/cards/detail.php"
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        self.cards = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    @staticmethod
    def fix_effect_array(effects: List[str]) -> List[str]:
        """
        Fix effect array by combining parenthetical explanations with previous elements.
        
        Rules:
        1. If an element starts with '(', combine it with the previous element
        2. Handles spacing correctly whether previous ends with '.' or not
        
        Args:
            effects: List of effect strings
            
        Returns:
            Fixed list of effect strings with parenthetical explanations combined
        """
        if not effects or len(effects) <= 1:
            return effects
        
        fixed = []
        i = 0
        
        while i < len(effects):
            current = effects[i].strip()
            
            # If this element starts with '(', combine it with the previous element
            if current.startswith('(') and fixed:
                # Get the last element we added
                previous = fixed[-1]
                
                # Combine with space separator
                if previous.endswith('.'):
                    # Period already has space semantics, add the parenthetical
                    fixed[-1] = f"{previous} {current}"
                else:
                    # No period, add space before parenthetical
                    fixed[-1] = f"{previous} {current}"
            else:
                # Normal element, add it
                fixed.append(current)
            
            i += 1
        
        return fixed
    
    def get_all_sets(self) -> List[Dict[str, str]]:
        """Get list of all available sets"""
        print("Fetching list of all sets...")
        
        # All known sets from the website - must scrape each individually
        sets = [
            {"name": "Newtype Rising", "code": "GD01", "param": "616101"},
            {"name": "Dual Impact", "code": "GD02", "param": "616102"},
            {"name": "Steel Requiem", "code": "GD03", "param": "616103"},
            {"name": "Heroic Beginnings", "code": "ST01", "param": "616001"},
            {"name": "Wings of Advance", "code": "ST02", "param": "616002"},
            {"name": "Zeon's Rush", "code": "ST03", "param": "616003"},
            {"name": "SEED Strike", "code": "ST04", "param": "616004"},
            {"name": "Iron Bloom", "code": "ST05", "param": "616005"},
            {"name": "Clan Unity", "code": "ST06", "param": "616006"},
            {"name": "Celestial Drive", "code": "ST07", "param": "616007"},
            {"name": "Flash of Radiance", "code": "ST08", "param": "616008"},
        ]
        
        print(f"Found {len(sets)} sets")
        return sets
    
    def get_card_ids_from_set(self, set_param: str, set_name: str) -> List[Dict[str, str]]:
        """Extract all card IDs from a set page"""
        url = f"{self.cards_url}?package={set_param}"
        print(f"\nScraping {set_name}...")
        print(f"  URL: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all card list items
            card_items = soup.find_all('li', class_='cardItem')
            card_ids = []
            
            for card_item in card_items:
                link = card_item.find('a', {'data-src': True})
                img = card_item.find('img', alt=True)
                
                if link and img:
                    data_src = link['data-src']
                    # Extract card ID from detail.php?detailSearch=GD03-001
                    match = re.search(r'detailSearch=([A-Z0-9_-]+)', data_src)
                    if match:
                        card_id = match.group(1)
                        card_name = img['alt']
                        
                        # Skip alternative artwork cards (those ending with _)
                        if card_id.endswith('_'):
                            continue
                        
                        card_ids.append({
                            'id': card_id,
                            'name': card_name,
                            'set': set_name
                        })
            
            print(f"  Found {len(card_ids)} cards")
            return card_ids
            
        except Exception as e:
            print(f"  Error: {e}")
            return []
    
    def _download_card_image(self, soup: BeautifulSoup, card_id: str, detail_page_url: str) -> Optional[str]:
        """Find and download card image from detail page. Returns relative path e.g. images/GD01-001.webp."""
        try:
            # Use CARD_IMAGE_XPATH structure: article > div[0] > div[2] > ... > img (div[3] is 1-indexed)
            article = soup.find("main")
            if article:
                article = article.find("article")
            if not article:
                return None
            
            img = article.find("img")
            if not img:
                return None
            
            src = img.get("src") or img.get("data-src")
            if not src:
                return None
            
            # Resolve relative URL (e.g. ../images/cards/card/GD01-001.webp)
            image_url = urljoin(detail_page_url, src)
            # Strip query string for clean filename
            image_url_base = image_url.split("?")[0]
            ext = os.path.splitext(image_url_base)[1] or ".webp"
            if ext not in (".webp", ".jpg", ".jpeg", ".png"):
                ext = ".webp"
            
            # Download image
            os.makedirs(self.images_dir, exist_ok=True)
            safe_id = card_id.replace("/", "-").replace("_", "-")
            filename = f"{safe_id}{ext}"
            filepath = os.path.join(self.images_dir, filename)
            
            resp = self.session.get(image_url, timeout=15)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            
            return os.path.join("images", filename)
        except Exception as e:
            print(f"    (Image download failed for {card_id}: {e})")
            return None
    
    def scrape_card_detail(self, card_id: str, card_name: str, set_name: str) -> Dict[str, Any]:
        """Scrape detailed card information"""
        url = f"{self.detail_url}?detailSearch={card_id}"
        
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Initialize card data with known info
            normalized_id = card_id.replace('_', '-')
            card_data = {
                "Name": card_name,
                "ID": normalized_id,  # Normalize ID format
                "Effect": [],
                "Color": "",
                "Type": "",
                "Rarity": "",
                "Traits": [],
                "Level": None,
                "Cost": None,
                "Ap": None,
                "Hp": None,
                "Block": None,
                "Zones": [],
                "Link": [],
                "Set": set_name.split('[')[1].rstrip(']') if '[' in set_name else "",
                "ImagePath": None,
            }
            
            # Get all text from the page with newlines preserved
            page_text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            # Parse line by line for better accuracy
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Color (line after "COLOR")
                if line == "COLOR" and i + 1 < len(lines):
                    card_data["Color"] = lines[i + 1]
                    i += 2
                    continue
                
                # Type (line after "TYPE")
                elif line == "TYPE" and i + 1 < len(lines):
                    card_data["Type"] = lines[i + 1]
                    i += 2
                    continue
                
                # Rarity (appears after card ID, before card name)
                elif line in ["C", "U", "R", "LR", "P"] and i < 5:  # Rarity is usually early
                    card_data["Rarity"] = line
                    i += 1
                    continue
                
                # Level (Lv. followed by number)
                elif line.startswith("Lv.") and i + 1 < len(lines):
                    level_match = re.search(r'\d+', lines[i + 1])
                    if level_match:
                        card_data["Level"] = int(level_match.group())
                    i += 2
                    continue
                
                # Cost (line after "COST")
                elif line == "COST" and i + 1 < len(lines):
                    cost_match = re.search(r'\d+', lines[i + 1])
                    if cost_match:
                        card_data["Cost"] = int(cost_match.group())
                    i += 2
                    continue
                
                # Zone (line after "Zone")
                elif line == "Zone" and i + 1 < len(lines):
                    zones_text = lines[i + 1]
                    card_data["Zones"] = [z.strip() for z in zones_text.split() if z.strip()]
                    i += 2
                    continue
                
                # Trait (line after "Trait")
                elif line == "Trait" and i + 1 < len(lines):
                    traits_text = lines[i + 1]
                    # Extract traits in parentheses
                    traits = re.findall(r'\(([^)]+)\)', traits_text)
                    card_data["Traits"] = traits if traits else [traits_text]
                    i += 2
                    continue
                
                # Link (line after "Link")
                elif line == "Link" and i + 1 < len(lines):
                    link_text = lines[i + 1]
                    # Extract links in brackets
                    links = re.findall(r'\[([^\]]+)\]', link_text)
                    card_data["Link"] = links if links else []
                    i += 2
                    continue
                
                # AP (line after "AP")
                elif line == "AP" and i + 1 < len(lines):
                    ap_match = re.search(r'\d+', lines[i + 1])
                    if ap_match:
                        card_data["Ap"] = int(ap_match.group())
                    i += 2
                    continue
                
                # HP (line after "HP")
                elif line == "HP" and i + 1 < len(lines):
                    hp_match = re.search(r'\d+', lines[i + 1])
                    if hp_match:
                        card_data["Hp"] = int(hp_match.group())
                    i += 2
                    continue
                
                # Block (line after "Block")
                elif line == "Block" and i + 1 < len(lines):
                    block_match = re.search(r'\d+', lines[i + 1])
                    if block_match:
                        card_data["Block"] = int(block_match.group())
                    i += 2
                    continue
                
                # Effect text (between TYPE and Zone, or between COST and Zone)
                # This is the card's effect text - collect all lines until we hit a known section
                elif card_data["Type"] and not card_data["Zones"] and line not in ["Zone", "Trait", "Link", "AP", "HP", "Block", "Source Title", "Where to get it", "CARDS", "PRODUCTS", "FAQ"]:
                    # This might be effect text
                    effect_line = line
                    # Check if it looks like effect text (has actual content)
                    if len(effect_line) > 3 and not re.match(r'^[\d\s]+$', effect_line):
                        # Avoid adding navigation or metadata
                        if not any(skip in effect_line for skip in ["Mobile Suit", "Newtype Rising", "Dual Impact", "Steel Requiem"]):
                            card_data["Effect"].append(effect_line)
                
                i += 1
            
            # Fix effect array by combining parenthetical explanations
            if card_data["Effect"]:
                card_data["Effect"] = self.fix_effect_array(card_data["Effect"])
            
            # Download card image and add path to JSON
            image_path = self._download_card_image(soup, normalized_id, url)
            if image_path:
                card_data["ImagePath"] = image_path
            
            return card_data
            
        except Exception as e:
            print(f"    Error scraping {card_id}: {e}")
            return None
    
    def scrape_all_cards(self, max_cards_per_set: int = None) -> List[Dict[str, Any]]:
        """Scrape all cards from all sets - processes each set individually"""
        print("="*60)
        print("Starting Official Gundam Card Game Scraper")
        print("="*60)
        
        # Get all sets
        sets = self.get_all_sets()
        
        # Process each set individually
        for set_info in sets:
            # Skip "All" or any invalid set entries
            if not set_info.get('param') or set_info.get('name', '').upper() == 'ALL':
                print(f"\n⚠ Skipping invalid set entry: {set_info.get('name', 'Unknown')}")
                continue
            
            set_name = f"{set_info['name']} [{set_info['code']}]"
            print(f"\n{'='*60}")
            print(f"Processing Set: {set_name}")
            print(f"{'='*60}")
            
            # Get card IDs from this set
            card_ids = self.get_card_ids_from_set(set_info['param'], set_name)
            
            if not card_ids:
                print(f"  ⚠ No cards found in this set, skipping...")
                continue
            
            # If testing, limit the number
            if max_cards_per_set:
                card_ids = card_ids[:max_cards_per_set]
                print(f"  (Testing mode: scraping {len(card_ids)} cards from this set)")
            
            # Scrape each card's details from this set
            for i, card_info in enumerate(card_ids, 1):
                print(f"  [{i}/{len(card_ids)}] {card_info['id']} - {card_info['name'][:40]}")
                
                card_data = self.scrape_card_detail(
                    card_info['id'],
                    card_info['name'],
                    set_name
                )
                
                if card_data:
                    self.cards.append(card_data)
                else:
                    print(f"    ✗ Failed to scrape card")
                
                # Be polite - don't hammer the server
                time.sleep(0.5)
            
            # Pause between sets
            print(f"  ✓ Completed {set_info['code']}: {len([c for c in self.cards if c['Set'] == set_info['code']])} cards scraped")
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"✓ Successfully scraped {len(self.cards)} total cards")
        print(f"{'='*60}")
        return self.cards
    
    def save_to_json(self, output_dir: str = None):
        """Save scraped cards to JSON files"""
        output_dir = output_dir or self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        if not self.cards:
            print("No cards to save!")
            return
        
        # Save all cards to a single file
        all_cards_file = os.path.join(output_dir, "all_cards.json")
        with open(all_cards_file, 'w', encoding='utf-8') as f:
            json.dump(self.cards, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved {len(self.cards)} cards to {all_cards_file}")
        
        # Save individual card files
        for card in self.cards:
            card_id = card.get("ID", "unknown").replace("/", "-").replace("_", "-")
            card_file = os.path.join(output_dir, f"{card_id}.json")
            with open(card_file, 'w', encoding='utf-8') as f:
                json.dump(card, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved individual card files to {output_dir}/")
        
        # Print statistics
        stats = {
            "total": len(self.cards),
            "by_set": {},
            "by_type": {},
            "by_color": {}
        }
        
        for card in self.cards:
            set_code = card["Set"]
            stats["by_set"][set_code] = stats["by_set"].get(set_code, 0) + 1
            
            card_type = card["Type"]
            stats["by_type"][card_type] = stats["by_type"].get(card_type, 0) + 1
            
            color = card["Color"]
            stats["by_color"][color] = stats["by_color"].get(color, 0) + 1
        
        print("\n" + "="*60)
        print("Database Statistics")
        print("="*60)
        print(f"Total cards: {stats['total']}")
        print(f"\nBy Set:")
        for set_code in sorted(stats["by_set"].keys()):
            print(f"  {set_code}: {stats['by_set'][set_code]}")
        print(f"\nBy Type:")
        for card_type in sorted(stats["by_type"].keys()):
            print(f"  {card_type}: {stats['by_type'][card_type]}")
        print(f"\nBy Color:")
        for color in sorted(stats["by_color"].keys()):
            print(f"  {color}: {stats['by_color'][color]}")


def main():
    """Main function"""
    print("\n" + "="*60)
    print("Gundam Card Game Official Website Scraper")
    print("="*60 + "\n")
    
    scraper = OfficialGundamScraper()
    
    # For initial testing, scrape 1 card per set to verify it works
    # Change to None to scrape ALL cards
    TEST_MODE = None  # Set to None for full scrape
    
    if TEST_MODE:
        print(f"⚠ TESTING MODE: Scraping {TEST_MODE} card(s) per set")
        print("  Change TEST_MODE to None in the script for full scrape\n")
    
    # Scrape cards
    cards = scraper.scrape_all_cards(max_cards_per_set=TEST_MODE)
    
    # Save to JSON
    scraper.save_to_json()
    
    print("\n" + "="*60)
    print("✓ Scraping Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
