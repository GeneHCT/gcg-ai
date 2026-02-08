"""
Batch card effect converter
Converts card effects from text to JSON schema format
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class CardEffectConverter:
    """Converts card effects to JSON schema"""
    
    def __init__(self, card_database_dir: str = "card_database",
                 effects_output_dir: str = "card_effects_converted"):
        self.card_database_dir = card_database_dir
        self.effects_output_dir = effects_output_dir
        
        # Create output directory if it doesn't exist
        Path(self.effects_output_dir).mkdir(parents=True, exist_ok=True)
    
    def convert_card(self, card_id: str) -> Optional[Dict]:
        """Convert a single card's effects"""
        # Load card data
        card_path = Path(self.card_database_dir) / f"{card_id}.json"
        if not card_path.exists():
            print(f"Card not found: {card_id}")
            return None
        
        with open(card_path, 'r') as f:
            card_data = json.load(f)
        
        effects_text = card_data.get("Effect", [])
        
        if not effects_text or len(effects_text) == 0:
            print(f"No effects for {card_id}")
            return None
        
        # Convert effects
        converted = self._convert_effects_text(card_id, effects_text, card_data)
        
        return converted
    
    def _convert_effects_text(self, card_id: str, effects_text: List[str], card_data: Dict) -> Dict:
        """Convert effect text to JSON schema"""
        result = {
            "card_id": card_id,
            "effects": [],
            "keywords": [],
            "continuous_effects": [],
            "metadata": {
                "original_text": "; ".join(effects_text),
                "complexity_score": 2,
                "parsing_version": "1.1",
                "last_updated": "2026-02-08",
                "card_type": card_data.get("Type", "UNIT")
            }
        }
        
        effect_counter = 1
        
        for effect_line in effects_text:
            # Skip empty lines or dashes
            if not effect_line or effect_line.strip() == '-':
                continue
            
            # FIX 2: Extract keywords from token specifications BEFORE processing effects
            # Pattern: [Token-Name](...<Keyword>...) Unit token
            # Note: Token spec may have nested parentheses like ((Trait)･...)
            # AND there may be MULTIPLE tokens in one line (e.g., "deploy 1 [Token-A] or 1 [Token-B]")
            # DO NOT add token keywords to main keywords array - they're only for the tokens
            import re
            # Just mark that we've seen token specs (for reference), don't extract keywords to main array
            # Keywords will be extracted when DEPLOY_TOKEN action is parsed
            
            # Parse 【Pilot】 lines as special effects
            if effect_line.strip().startswith('【Pilot】'):
                effect = self._parse_pilot_effect(card_id, effect_counter, effect_line, card_data)
                if effect:
                    result["effects"].append(effect)
                    effect_counter += 1
                continue
            
            # Parse keywords (standalone angle bracket lines OR square bracket keywords)
            if (effect_line.startswith('<') or effect_line.startswith('[')) and ('>' in effect_line or ']' in effect_line) and not any(word in effect_line for word in ['gain', 'gains', 'have', 'has']):
                # Square bracket keywords like [Suppression] should be continuous effects
                if effect_line.startswith('['):
                    effect = self._parse_continuous_effect_line(card_id, effect_counter, effect_line, card_data)
                    if effect:
                        result["continuous_effects"].append(effect)
                        effect_counter += 1
                else:
                    keyword = self._parse_keyword(effect_line)
                    if keyword:
                        result["keywords"].append(keyword)
                continue
            
            # Parse 【Activate】effects with keywords (e.g., "【Activate･Main】<Support 3>")
            if effect_line.startswith('【Activate'):
                import re
                # Check if there's a keyword immediately after the activate bracket
                keyword_match = re.search(r'【Activate[^】]*】\s*<([^>]+)>', effect_line)
                if keyword_match:
                    keyword_text = keyword_match.group(1)
                    parts = keyword_text.split()
                    keyword_name = parts[0].strip().upper().replace('-', '_')
                    
                    value = None
                    if len(parts) > 1:
                        try:
                            value = int(parts[1])
                        except ValueError:
                            pass
                    
                    # Add keyword to result
                    result["keywords"].append({
                        "keyword": keyword_name,
                        "value": value,
                        "description": None
                    })
                # Still parse the effect normally
                effect = self._parse_effect_line(card_id, effect_counter, effect_line, card_data)
                if effect:
                    result["effects"].append(effect)
                    effect_counter += 1
                continue
            
            # Try to parse as effect (triggered, activated, or continuous)
            effect = self._parse_effect_line(card_id, effect_counter, effect_line, card_data)
            if effect:
                if effect.get("effect_type") == "CONTINUOUS":
                    result["continuous_effects"].append(effect)
                else:
                    result["effects"].append(effect)
                effect_counter += 1
        
        # Clean up empty sections
        if not result["keywords"]:
            del result["keywords"]
        if not result["continuous_effects"]:
            del result["continuous_effects"]
        
        return result
    
    def _parse_effect_line(self, card_id: str, counter: int, text: str, card_data: Dict) -> Optional[Dict]:
        """Parse a single effect line - could be triggered, activated, or continuous"""
        effect = {
            "effect_id": f"{card_id}-E{counter}",
            "effect_type": "TRIGGERED",
            "triggers": [],
            "conditions": [],
            "actions": []
        }
        
        # Check if it's a continuous effect (grants abilities/stats without a trigger)
        if self._is_continuous_effect(text):
            return self._parse_continuous_effect_line(card_id, counter, text, card_data)
        
        # Extract triggers
        triggers = self._extract_triggers(text)
        if not triggers:
            # VALIDATION FIX: For Command cards, infer trigger from 【Main】/【Action】in text
            if card_data.get("Type") == "COMMAND":
                import re
                if re.search(r'\b(Choose|Deal|Draw|Rest|Destroy|Place|Deploy)', text):
                    has_dual = '【Main】/【Action】' in text or '【Action】/【Main】' in text
                    if has_dual:
                        triggers = ["MAIN_PHASE", "ACTION_PHASE"]
                    elif re.search(r'【Main[^】]*】', text):
                        triggers = ["MAIN_PHASE"]
                    elif re.search(r'【Action[^】]*】', text):
                        triggers = ["ACTION_PHASE"]
                    else:
                        triggers = ["ACTION_PHASE"]  # last resort
                    effect["triggers"] = triggers
                else:
                    return None
            else:
                # If no triggers found, might be a continuous effect we missed
                return None
        else:
            effect["triggers"] = triggers
        
        # Check for restrictions
        if "Once per Turn" in text:
            effect["restrictions"] = {"once_per_turn": True}
        
        # Check if it's an activated ability
        if "Activate" in triggers[0] if triggers else False:
            effect["effect_type"] = "ACTIVATED"
            
            # Parse cost if present
            cost = self._parse_cost(text)
            if cost:
                effect["cost"] = cost
        
        # Parse conditions
        conditions = self._parse_conditions(text, card_data)
        if conditions:
            effect["conditions"] = conditions
        
        # Parse actions (may include conditional chains with "If you do")
        actions = self._parse_actions(text, card_data)
        if actions:
            effect["actions"] = actions
        
        return effect
    
    def _is_continuous_effect(self, text: str) -> bool:
        """Check if text describes a continuous effect"""
        import re
        
        # FIX 1: Check for multiple trigger brackets FIRST
        # If text has multiple trigger brackets like "【During Pair】【Attack】", it's a triggered effect
        trigger_bracket_pattern = r'【(Deploy|Destroyed|Attack|Burst|Main|Action|When Paired|When Linked|During Pair|During Link|Activate)】'
        trigger_matches = re.findall(trigger_bracket_pattern, text)
        if len(trigger_matches) >= 2:
            # Multiple triggers = definitely a triggered effect, not continuous
            return False
        
        # FIX: Check if 【During Link】/【During Pair】is followed by protection/restriction text
        # If it has "can't be reduced", "can't receive", "gets", etc., it's continuous
        # If it has action verbs like "Choose", "Deal", "Draw", etc., it's triggered
        # If it has "when" trigger words, it's triggered
        # If it has "If" conditions with actions, it's triggered
        if '【During Link】' in text or '【During Pair】' in text:
            # Check if it has "When" trigger (this makes it triggered, not continuous)
            if re.search(r'\bwhen\b', text, re.IGNORECASE):
                return False
            
            # Check if it has "If" condition (conditional effects are triggered, not continuous)
            # But make sure it's not just "if possible" which is continuous
            if re.search(r'\bIf\s+(this|you|there)', text):
                return False
            
            # Check if followed by typical continuous effect patterns (static modifiers)
            continuous_indicators = [
                "can't be reduced",
                "can't receive",
                "can't be destroyed",
                "cannot be"
            ]
            if any(indicator in text for indicator in continuous_indicators):
                return True
            
            # "gets/gains" without "If" condition is continuous
            if ("gets " in text or "gains " in text) and not re.search(r'\bIf\s+(this|you|there)', text):
                return True
            
            # Check if followed by action verbs (it's a triggered effect)
            action_indicators = [
                "Choose",
                "Deal ",
                "Draw ",
                "Rest ",
                "Destroy ",
                "Deploy ",
                "Place ",
                "Add ",
                "Return ",
                "You may"
            ]
            if any(indicator in text for indicator in action_indicators):
                return False
        
        # First check if it has a trigger word like "when" at the START or as main clause (not in parentheses or end clauses)
        # Remove reminder text in parentheses before checking
        text_without_reminder = re.sub(r'\([^)]+\)', '', text)
        # Check for "when" that indicates a trigger (usually at start or after comma)
        # But not "when attacking" which is a condition
        if re.search(r'^When |, when |【When ', text_without_reminder, re.IGNORECASE):
            # But allow "when attacking" / "when defending" as these are conditions, not triggers
            if not re.search(r'when (attacking|defending)', text_without_reminder, re.IGNORECASE):
                return False
        
        # Check if it starts with trigger brackets - these are triggered effects, not continuous
        trigger_patterns = ['【Deploy】', '【Attack】', '【Destroyed】', '【Main】', '【Action】', '【Burst】']
        for pattern in trigger_patterns:
            if text.strip().startswith(pattern):
                return False
        
        continuous_patterns = [
            "While",
            "During your turn",  # Added for time-based continuous effects
            "During your opponent's turn",
            "All your",
            "All (", 
            "All friendly",  # Added for token effects
            "Your Units",
            "Your (", 
            "This Unit gains",
            "This Unit has",
            "This Unit may choose",  # Attack targeting rules
            "This Unit can't",  # Restrictions
            "This Unit can only",  # Attack restrictions
            "This card",  # Added for "This card in your trash gets cost -1"
            "This Base can't",  # Base restrictions
            "Increase this Unit's AP",  # Stat equals count effects
            "Enemy Units choose",  # Attack targeting rules
            "Enemy Units",  # Attack targeting rules
            "gain <",
            "gains <",
            "have <",
            "has <",
            "can't be",
            "cannot be",
            "can only attack",  # Attack restrictions
            "[Suppression]",  # Square bracket keywords
            "<"  # Standalone keywords like <Repair 1>
        ]
        
        # Check if it starts with continuous patterns
        for pattern in continuous_patterns:
            if text.startswith(pattern):
                return True
        
        # Check for patterns within first 70 chars (extended from 50 for "During your turn, while...")
        for pattern in ["gain <", "gains <", "have <", "has <", "may choose", "can't be", "can't receive"]:
            if pattern in text[:70]:
                return True
        
        return False
    
    def _parse_continuous_effect_line(self, card_id: str, counter: int, text: str, card_data: Dict) -> Optional[Dict]:
        """Parse continuous effect"""
        effect = {
            "effect_id": f"{card_id}-E{counter}",
            "effect_type": "CONTINUOUS",
            "description": text,
            "modifiers": []
        }
        
        # Check for name aliasing ("This card's name is also treated as [X]")
        import re
        name_alias_match = re.search(r"This card's name is also treated as \[([^\]]+)\]", text)
        if name_alias_match:
            alias_name = name_alias_match.group(1)
            effect["modifiers"].append({
                "type": "NAME_ALIAS",
                "alias_name": alias_name
            })
            return effect
        
        # Check for restrictions ("can't be set as active or paired")
        if "can't be set as active" in text.lower() or ("can't be" in text.lower() and "paired" in text.lower()):
            restrictions = []
            
            if "can't be set as active" in text.lower():
                restrictions.append({
                    "type": "RESTRICTION",
                    "restriction_type": "CANNOT_BE_ACTIVE"
                })
            
            if "paired with a Pilot" in text.lower() or ("paired" in text.lower() and "can't" in text.lower()):
                restrictions.append({
                    "type": "RESTRICTION",
                    "restriction_type": "CANNOT_BE_PAIRED"
                })
            
            effect["modifiers"] = restrictions
            return effect
        
        # Check for "can't receive effect damage" protection
        if "can't receive" in text.lower() and "effect damage" in text.lower():
            protection = {
                "type": "PROTECTION",
                "protection_type": "PREVENT_EFFECT_DAMAGE"
            }
            
            # Check if it's from enemy only
            if "enemy effect damage" in text.lower():
                protection["source_filter"] = "ENEMY"
            
            # Check if it's from specific card types
            if "from enemy commands" in text.lower():
                protection["source_filter"] = "ENEMY"
                protection["source_card_type"] = "COMMAND"
            
            # Check for timing/condition requirements
            conditions = []
            
            # "During your turn"
            if "during your turn" in text.lower():
                conditions.append({
                    "type": "CHECK_TURN",
                    "turn_owner": "SELF"
                })
            
            # "while there are X or more cards in your trash"
            import re
            trash_cond = re.search(r'while there are (\d+) or more cards in your trash', text, re.IGNORECASE)
            if trash_cond:
                count = int(trash_cond.group(1))
                conditions.append({
                    "type": "COUNT_CARDS",
                    "zone": "TRASH",
                    "owner": "SELF",
                    "operator": ">=",
                    "value": count
                })
            
            if conditions:
                protection["conditions"] = conditions
            
            effect["modifiers"].append(protection)
            return effect
        
        # Check for zone-specific cost modification ("This card in your trash gets cost -X")
        if re.search(r'This card in your trash gets cost ([+-]\d+)', text):
            cost_match = re.search(r'gets cost ([+-])(\d+)', text)
            if cost_match:
                operator = cost_match.group(1)
                value = int(cost_match.group(2))
                if operator == '-':
                    value = -value
                
                effect["modifiers"].append({
                    "type": "MODIFY_COST",
                    "zone": "TRASH",
                    "value": value
                })
                return effect
        
        # Check for attack restrictions
        if "can only attack during" in text.lower():
            effect["modifiers"].append({
                "type": "RESTRICTION",
                "restriction_type": "ATTACK_RESTRICTION",
                "description": text
            })
            return effect
        
        # Check if it's just a standalone keyword
        if text.startswith('<') and '>' in text and len(text) < 100:
            # Extract keyword
            import re
            keyword_match = re.search(r'<([^>]+)>', text)
            if keyword_match:
                keyword_text = keyword_match.group(1)
                parts = keyword_text.split()
                keyword_name = parts[0].strip().upper().replace('-', '_')
                
                value = None
                if len(parts) > 1:
                    try:
                        value = int(parts[1])
                    except ValueError:
                        pass
                
                effect["modifiers"].append({
                    "type": "GRANT_KEYWORD",
                    "target": {"selector": "SELF"},
                    "keyword": keyword_name,
                    "value": value
                })
                return effect
        
        # Parse "While" conditions with stat/keyword grants
        if text.startswith("While"):
            # This is a conditional continuous effect
            effect["condition_description"] = text
            
            # Parse the While condition itself
            conditions = []
            
            # "While you have another (Trait) Unit in play"
            if re.search(r'While you have another \(([^)]+)\) Unit in play', text):
                trait_match = re.search(r'While you have another \(([^)]+)\) Unit in play', text)
                trait = trait_match.group(1)
                conditions.append({
                    "type": "COUNT_CARDS",
                    "zone": "BATTLE_AREA",
                    "owner": "SELF",
                    "card_type": "UNIT",
                    "traits": [trait],
                    "exclude_self": True,
                    "operator": ">=",
                    "value": 1
                })
            # "While this Unit has X or more AP/HP"
            elif re.search(r'While this Unit has (\d+) or more (AP|HP)', text):
                stat_cond_match = re.search(r'While this Unit has (\d+) or more (AP|HP)', text)
                value = int(stat_cond_match.group(1))
                stat = stat_cond_match.group(2).upper()
                conditions.append({
                    "type": "CHECK_STAT",
                    "target": {"selector": "SELF"},
                    "stat": stat,
                    "operator": ">=",
                    "value": value
                })
            
            # "While this Unit is (Trait)"
            elif re.search(r'While this Unit is \(([^)]+)\)', text):
                trait_match = re.search(r'While this Unit is \(([^)]+)\)', text)
                trait = trait_match.group(1)
                conditions.append({
                    "type": "CHECK_CARD_TRAIT",
                    "target": {"selector": "SELF"},
                    "required_traits": [trait]
                })
            
            # "While another friendly (Trait) Link Unit is in play"
            elif re.search(r'While another friendly \(([^)]+)\) Link Unit is in play', text):
                trait_match = re.search(r'While another friendly \(([^)]+)\) Link Unit is in play', text)
                trait = trait_match.group(1)
                conditions.append({
                    "type": "COUNT_CARDS",
                    "zone": "BATTLE_AREA",
                    "owner": "SELF",
                    "card_type": "UNIT",
                    "traits": [trait],
                    "is_link": True,
                    "exclude_self": True,
                    "operator": ">=",
                    "value": 1
                })
            
            if conditions:
                effect["conditions"] = conditions
            
            # Check if it grants something (including "and <Keyword>" patterns)
            # Pattern: "gets AP+1 and <Blocker>" OR "gets AP+1 and <Breach 1>"
            if "and <" in text or "gains <" in text or "gain <" in text or "gets " in text:
                import re
                # Extract ALL keywords from the text
                keyword_matches = re.findall(r'<([^>]+)>', text)
                for keyword_str in keyword_matches:
                    parts = keyword_str.split()
                    keyword_name = parts[0].strip().upper().replace('-', '_')
                    
                    value = None
                    if len(parts) > 1:
                        try:
                            value = int(parts[1])
                        except ValueError:
                            pass
                    
                    effect["modifiers"].append({
                        "type": "GRANT_KEYWORD",
                        "target": {"selector": "SELF"},
                        "keyword": keyword_name,
                        "value": value,
                        "condition": text.split(',')[0]  # Store the While condition
                    })
            
            # Check if it modifies AP or HP (even without keywords)
            if re.search(r'gets (AP|HP)([+-])(\d+)', text):
                stat_match = re.search(r'gets (AP|HP)([+-])(\d+)', text)
                stat = stat_match.group(1).upper()
                operator = stat_match.group(2)
                value = int(stat_match.group(3))
                if operator == '-':
                    value = -value
                
                effect["modifiers"].append({
                    "type": "MODIFY_STAT",
                    "target": {"selector": "SELF"},
                    "stat": stat,
                    "value": value,
                    "condition": text.split(',')[0]
                })
            
            # Check if it modifies cost
            elif "gets cost" in text:
                import re
                cost_match = re.search(r'gets cost ([+-])(\d+)', text)
                if cost_match:
                    operator = cost_match.group(1)
                    value = int(cost_match.group(2))
                    if operator == '-':
                        value = -value
                    
                    effect["modifiers"].append({
                        "type": "MODIFY_COST",
                        "target": {"selector": "SELF"},
                        "value": value,
                        "condition": text.split(',')[0]  # Store the While condition
                    })
            
            return effect
        
        # Parse attack targeting rules ("may choose... as attack target")
        if "may choose" in text.lower() and "attack target" in text.lower():
            effect["effect_type"] = "CONTINUOUS"
            effect["description"] = text
            
            # Parse the targeting restrictions
            import re
            
            # Extract level filter
            level_filter = {}
            level_match = re.search(r'Lv\.(\d+) or lower', text)
            if level_match:
                level_filter = {"operator": "<=", "value": int(level_match.group(1))}
            
            # Extract HP filter
            hp_filter = {}
            hp_match = re.search(r'(\d+) or less HP', text)
            if hp_match:
                hp_filter = {"operator": "<=", "value": int(hp_match.group(1))}
            
            # Extract state filter
            state_filter = None
            if "active enemy Unit" in text.lower():
                state_filter = "ACTIVE"
            elif "rested enemy Unit" in text.lower():
                state_filter = "RESTED"
            
            filters = {}
            if level_filter:
                filters["level"] = level_filter
            if hp_filter:
                filters["hp"] = hp_filter
            if state_filter:
                filters["state"] = state_filter
            
            effect["modifiers"].append({
                "type": "MODIFY_ATTACK_TARGET",
                "target": {"selector": "SELF"},
                "target_restrictions": filters if filters else {},
                "description": "Can choose additional units as attack targets"
            })
            
            return effect
        
        # Parse what it grants
        if "gain <" in text or "gains <" in text or "have <" in text or "has <" in text:
            # Extract keyword being granted
            import re
            keyword_match = re.search(r'<([^>]+)>', text)
            if keyword_match:
                keyword_text = keyword_match.group(1)
                parts = keyword_text.split()
                keyword_name = parts[0].strip().upper().replace('-', '_')
                
                value = None
                if len(parts) > 1:
                    try:
                        value = int(parts[1])
                    except ValueError:
                        pass
                
                # Determine target
                target = {"selector": "SELF"}
                if text.startswith("All your"):
                    target = {"selector": "FRIENDLY_UNIT"}
                    # Check for trait filter
                    traits = self._extract_traits(text)
                    if traits:
                        target["filters"] = {"traits": traits}
                
                effect["modifiers"].append({
                    "type": "GRANT_KEYWORD",
                    "target": target,
                    "keyword": keyword_name,
                    "value": value
                })
        
        # NEW CONTINUOUS EFFECTS FOR REMAINING 18 CARDS
        
        # Token-specific stat modifier
        if "Unit tokens get AP" in text or "friendly Unit tokens get AP" in text:
            ap_match = re.search(r'AP\+(\d+)', text)
            if ap_match:
                modifier = {
                    "type": "MODIFY_STAT",
                    "target": {
                        "selector": "FRIENDLY_UNIT",
                        "filters": {"is_token": True}
                    },
                    "stat": "AP",
                    "value": int(ap_match.group(1))
                }
                
                # Add turn condition
                if "during your opponent's turn" in text.lower():
                    modifier["condition"] = {
                        "type": "CHECK_TURN",
                        "turn_owner": "OPPONENT"
                    }
                
                effect["modifiers"].append(modifier)
        
        # [Suppression] keyword (square brackets)
        if text.startswith('[Suppression]'):
            effect["modifiers"].append({
                "type": "GRANT_KEYWORD",
                "target": {"selector": "SELF"},
                "keyword": "SUPPRESSION",
                "value": None
            })
        
        # Attack targeting rules (enemy must target specific friendly)
        if "as their attack target if possible" in text:
            traits = self._extract_traits(text)
            effect["modifiers"].append({
                "type": "FORCE_ATTACK_TARGET",
                "target": {"selector": "SELF"},
                "redirect_attacks_to": {
                    "selector": "FRIENDLY_UNIT",
                    "filters": {
                        "traits": traits,
                        "state": "RESTED"
                    }
                }
            })
        
        # Attack restriction (can only attack during specific turns)
        if "can only attack during a turn when" in text:
            traits = self._extract_traits(text)
            effect["modifiers"].append({
                "type": "RESTRICT_ATTACK",
                "target": {"selector": "SELF"},
                "condition": {
                    "type": "CHECK_TURN_EVENT",
                    "event": "UNIT_DEPLOYED",
                    "filters": {
                        "traits": traits
                    }
                }
            })
        
        # Stat equals count of unique names in zone
        if "Increase this Unit's AP by an amount equal to" in text:
            unique_count_match = re.search(r'number of .+ with unique names in your trash', text)
            if unique_count_match:
                traits = self._extract_traits(text)
                card_types = []
                if "Pilot cards" in text or "Pilot card" in text:
                    card_types.append("PILOT")
                if "Command cards" in text or "Command card" in text:
                    card_types.append("COMMAND")
                
                effect["modifiers"].append({
                    "type": "STAT_EQUALS_COUNT",
                    "target": {"selector": "SELF"},
                    "stat": "AP",
                    "count_source": {
                        "zone": "TRASH",
                        "owner": "SELF",
                        "card_types": card_types,
                        "traits": traits,
                        "unique_names_only": True
                    }
                })
        
        return effect
    
    def _parse_keyword(self, text: str) -> Optional[Dict]:
        """Parse keyword from text"""
        import re
        
        # Extract keyword name and value
        if '<' not in text or '>' not in text:
            return None
        
        # Check if this keyword is in a filter context (should not be extracted as standalone)
        # Look for patterns like "Choose X with <Keyword>", "enemy Unit with <Keyword>"
        if re.search(r'(Choose|with|enemy|friendly)\s+[^<]{0,30}<', text):
            return None  # This is a filter, not a standalone keyword
        
        # FIX 3: Check if this is a reference to a keyword (should not be extracted as standalone)
        # Look for patterns like "use <Keyword>", "uses <Keyword>", "using <Keyword>"
        if re.search(r'\b(use|uses|using)\s+([^<]{0,30})?<', text):
            return None  # This is a reference, not a standalone keyword
        
        # If part of "increase a ... Unit's" phrase, it's likely a reference
        if re.search(r"increase a .+ Unit's\s+<", text, re.IGNORECASE):
            return None  # This is a reference, not a standalone keyword
        
        start = text.index('<') + 1
        end = text.index('>')
        keyword_text = text[start:end]
        
        # Split keyword and value
        parts = keyword_text.split()
        keyword_name = parts[0].strip().upper().replace('-', '_')
        
        value = None
        if len(parts) > 1:
            try:
                value = int(parts[1])
            except ValueError:
                pass
        
        # Extract description (if in parentheses)
        description = ""
        if '(' in text and ')' in text:
            desc_start = text.index('(') + 1
            desc_end = text.rindex(')')
            description = text[desc_start:desc_end]
        
        return {
            "keyword": keyword_name,
            "value": value,
            "description": description if description else None
        }
    
    def _parse_pilot_effect(self, card_id: str, counter: int, text: str, card_data: Dict) -> Optional[Dict]:
        """
        Parse 【Pilot】 effect - allows Command card to be played as a Pilot.
        
        Format: 【Pilot】[Pilot Name]
        
        When played as a pilot:
        - Takes the name in brackets
        - Uses AP and HP from the Command card
        - Still counts as a Command card type
        - Retains all traits from the Command card
        """
        import re
        
        # Extract pilot name from brackets
        pilot_match = re.search(r'【Pilot】\[([^\]]+)\]', text)
        if not pilot_match:
            return None
        
        pilot_name = pilot_match.group(1)
        
        effect = {
            "effect_id": f"{card_id}-E{counter}",
            "effect_type": "PILOT_ABILITY",
            "description": f"This card can be played as a Pilot named '{pilot_name}'",
            "pilot_name": pilot_name,
            "pilot_stats": {
                "ap": card_data.get("Ap"),
                "hp": card_data.get("Hp"),
                "original_type": card_data.get("Type"),
                "traits": card_data.get("Traits", [])
            }
        }
        
        return effect
    
    def _extract_triggers(self, text: str) -> List[str]:
        """Extract trigger types from text"""
        triggers = []
        
        # Check for pilot-trait-conditional triggers first
        import re
        
        # VALIDATION FIX: Better handling for Command card triggers
        # 【Main】maps to MAIN_PHASE, 【Action】maps to ACTION_PHASE, 【Main】/【Action】to both
        
        # FIX 1: MULTIPLE TRIGGERS PER LINE
        # Extract ALL trigger brackets from the text, not just the first one
        # Pattern: 【During Pair･Lv.3 or Lower Pilot】【Destroyed】
        
        # Check for pilot level conditionals (e.g., "【When Paired･Lv.4 or Higher Pilot】")
        pilot_level_match = re.search(r'【(When Paired|During Pair).*?Lv\.(\d+) or (Higher|Lower) Pilot】', text)
        if pilot_level_match:
            base_trigger = pilot_level_match.group(1)
            
            # Map to trigger type
            if base_trigger == "When Paired":
                triggers.append("ON_PAIRED")
            elif base_trigger == "During Pair":
                triggers.append("WHILE_PAIRED")
            
            # The level check will be handled as a condition
            # BUT DON'T RETURN YET - check for additional triggers after this one
            # Continue to check for more triggers below
        
        # Use .*? for flexible matching between trigger and trait
        pilot_trait_match = re.search(r'【(When Paired|During Pair|When Linked|During Link).*?\(([^】]+)\) Pilot】', text)
        if pilot_trait_match:
            base_trigger = pilot_trait_match.group(1)
            pilot_traits = pilot_trait_match.group(2)
            
            # Map to trigger type
            if base_trigger == "When Paired":
                triggers.append("ON_PAIRED_WITH_TRAIT")
            elif base_trigger == "During Pair":
                triggers.append("WHILE_PAIRED_WITH_TRAIT")
            elif base_trigger == "When Linked":
                triggers.append("ON_LINKED_WITH_TRAIT")
            elif base_trigger == "During Link":
                triggers.append("WHILE_LINKED_WITH_TRAIT")
            
            # Store pilot trait requirement as metadata (will be added to conditions)
            # This is a bit hacky but we'll handle it in _parse_effect_line
            # DON'T RETURN YET - check for additional triggers after this one
        
        # Check for pilot color conditionals (e.g., "【During Pair･Red Pilot】", "【When Paired･Purple Pilot】")
        pilot_color_match = re.search(r'【(When Paired|During Pair).*?(Red|Blue|Green|Purple|White|Yellow) Pilot】', text)
        if pilot_color_match:
            base_trigger = pilot_color_match.group(1)
            pilot_color = pilot_color_match.group(2)
            
            # Map to trigger type
            if base_trigger == "When Paired":
                triggers.append("ON_PAIRED_WITH_COLOR")
            elif base_trigger == "During Pair":
                triggers.append("WHILE_PAIRED_WITH_COLOR")
            
            # DON'T RETURN YET - check for additional triggers after this one
        
        # IMPORTANT: Check for dual-timing pattern FIRST before individual triggers
        # This prevents "【Main】" and "【Action】" from being added separately
        has_dual_timing = '【Main】/【Action】' in text or '【Action】/【Main】' in text
        
        if has_dual_timing:
            # Card can be played at EITHER timing, so add BOTH triggers
            if "MAIN_PHASE" not in triggers:
                triggers.append("MAIN_PHASE")
            if "ACTION_PHASE" not in triggers:
                triggers.append("ACTION_PHASE")
        
        # FIX 1: MULTIPLE TRIGGERS - Now extract ALL standard triggers from the text
        # This handles cases like "【During Pair】【Attack】" or "【During Pair･Lv.3 or Lower Pilot】【Destroyed】"
        trigger_map = {
            "【Deploy】": "ON_DEPLOY",
            "【Destroyed】": "ON_DESTROYED",
            "【Attack】": "ON_ATTACK",
            "【Burst】": "BURST",
            "【Main】": "MAIN_PHASE",
            "【Action】": "ACTION_PHASE",
            "【When Paired】": "ON_PAIRED",
            "【When Linked】": "ON_LINKED",
            "【During Pair】": "WHILE_PAIRED",
            "【During Link】": "WHILE_LINKED",
            "【Activate･Main】": "ACTIVATE_MAIN",
            "【Activate･Action】": "ACTIVATE_ACTION"
        }
        
        # Search for ALL trigger brackets in the text (not just the first one)
        for bracket_text, trigger_name in trigger_map.items():
            # Skip individual 【Main】 or 【Action】 if we already handled dual-timing
            if has_dual_timing and bracket_text in ["【Main】", "【Action】"]:
                continue
            
            if bracket_text in text:
                # Only add if not already added (avoid duplicates from pilot-conditional handling above)
                if trigger_name not in triggers:
                    triggers.append(trigger_name)
        
        # VALIDATION FIX: Ensure 【Main】/【Action】triggers are captured even if not in standard format
        # This helps with Command cards that may have variations in spacing or format
        if not triggers:
            if re.search(r'【Main[^】]*】', text):
                triggers.append("MAIN_PHASE")
            elif re.search(r'【Action[^】]*】', text):
                triggers.append("ACTION_PHASE")
        
        # Check for "At the end of your turn"
        if "At the end of your turn" in text or "At the end of this turn" in text:
            triggers.append("ON_END_PHASE")
        
        # Check for "During this battle"
        if "During this battle" in text:
            triggers.append("DURING_BATTLE")
        
        # Check for "When X is destroyed with damage" patterns (even without brackets)
        if re.search(r'When .+ is destroyed with (battle )?damage', text):
            # This is a custom trigger for destroy-by-damage events
            triggers.append("ON_UNIT_DESTROYED_BY_DAMAGE")
        
        # Check for "When this Unit receives effect damage"
        if re.search(r'When .+ receives? (enemy )?effect damage', text, re.IGNORECASE):
            triggers.append("ON_RECEIVE_EFFECT_DAMAGE")
        
        # Check for "When this Unit's AP is reduced"
        if re.search(r"When this Unit's (AP|HP) is reduced", text, re.IGNORECASE):
            triggers.append("ON_STAT_REDUCED")
        
        # Check for "When friendly Unit receives effect damage"
        if re.search(r'when .+ friendly .+ receives? effect damage', text, re.IGNORECASE):
            triggers.append("ON_FRIENDLY_UNIT_RECEIVE_EFFECT_DAMAGE")
        
        # Check for "When X destroys Y with battle damage"
        if re.search(r'when .+ destroys .+ with battle damage', text, re.IGNORECASE):
            triggers.append("ON_DESTROY_UNIT_WITH_BATTLE_DAMAGE")
        
        # NEW TRIGGERS FOR REMAINING 18 CARDS
        
        # EX Resource trigger
        if "When you place an EX Resource" in text or "When you place an EX Resource" in text:
            triggers.append("ON_PLACE_EX_RESOURCE")
        
        # Pair pilot trigger
        if re.search(r'When you pair a Pilot', text):
            triggers.append("ON_PAIR_PILOT")
        
        # Unit linked trigger (for other units linking)
        if re.search(r'When .+ friendly .+ Unit links', text):
            triggers.append("ON_UNIT_LINKED")
        
        # Rested by effect trigger
        if re.search(r'when .+ is rested by .+ effect', text, re.IGNORECASE):
            triggers.append("ON_RESTED_BY_EFFECT")
        
        # Play from hand trigger
        if "When playing this card from your hand" in text:
            triggers.append("ON_PLAY_FROM_HAND")
        
        # Other unit's battle damage
        if re.search(r'when your .+ Unit deals battle damage', text, re.IGNORECASE):
            triggers.append("ON_OTHER_FRIENDLY_UNIT_DEAL_BATTLE_DAMAGE")
        
        # Draw with effect trigger
        if "When you draw with an effect" in text:
            triggers.append("ON_DRAW_WITH_EFFECT")
        
        # Battle damage trigger (for "When this Unit deals battle damage to...")
        if re.search(r'When this Unit deals battle damage to', text):
            triggers.append("ON_DEAL_BATTLE_DAMAGE")
        
        # When you rest your Base trigger (for replacement effects)
        if "When you rest your Base" in text:
            triggers.append("ON_REST_BASE")
        
        return triggers
    
    def _parse_cost(self, text: str) -> Optional[Dict]:
        """Parse cost from text"""
        # Look for circled numbers or "Exile X"
        if "①" in text:
            return {"cost_type": "RESOURCE", "amount": 1}
        elif "②" in text:
            return {"cost_type": "RESOURCE", "amount": 2}
        elif "③" in text:
            return {"cost_type": "RESOURCE", "amount": 3}
        elif "Exile" in text:
            # Parse exile cost
            # Example: "Exile 3 (Titans) cards from your trash:"
            return None  # TODO: Implement exile cost parsing
        
        return None
    
    def _parse_conditions(self, text: str, card_data: Dict) -> List[Dict]:
        """Parse conditions from text"""
        conditions = []
        import re
        
        # Check for pilot-trait requirements in trigger
        pilot_trait_match = re.search(r'.*?\(([^】]+)\) Pilot】', text)
        if pilot_trait_match:
            pilot_traits_str = pilot_trait_match.group(1)
            # Split by / for multiple traits, and clean up parentheses
            pilot_traits = [t.strip().strip('()') for t in pilot_traits_str.split('/')]
            
            conditions.append({
                "type": "CHECK_PAIRED_PILOT_TRAIT",
                "required_traits": pilot_traits,
                "trait_operator": "ANY" if '/' in pilot_traits_str else "ALL"
            })
        
        # Check for pilot color requirements (e.g., "【During Pair･Red Pilot】")
        pilot_color_match = re.search(r'.*?(Red|Blue|Green|Purple|White|Yellow) Pilot】', text)
        if pilot_color_match:
            pilot_color = pilot_color_match.group(1).lower()
            conditions.append({
                "type": "CHECK_PAIRED_PILOT_COLOR",
                "required_color": pilot_color
            })
        
        # Check for "If you have X or more other Units in play"
        other_units_match = re.search(r'If you have (\d+) or more other Units in play', text, re.IGNORECASE)
        if other_units_match:
            count = int(other_units_match.group(1))
            conditions.append({
                "type": "COUNT_CARDS",
                "zone": "BATTLE_AREA",
                "owner": "SELF",
                "card_type": "UNIT",
                "exclude_self": True,
                "operator": ">=",
                "value": count
            })
        # Check for "If you have another" conditions
        elif "If you have another" in text:
            # Extract trait from parentheses
            traits = self._extract_traits(text)
            if traits:
                conditions.append({
                    "type": "COUNT_CARDS",
                    "zone": "BATTLE_AREA",
                    "owner": "SELF",
                    "card_type": "UNIT",
                    "traits": traits,
                    "exclude_self": True,
                    "operator": ">=",
                    "value": 1
                })
        # NEW: Check for "If you have no ... Unit tokens in play"
        elif "If you have no" in text and "Unit token" in text:
            # Extract trait from parentheses
            traits = self._extract_traits(text)
            if traits:
                conditions.append({
                    "type": "COUNT_CARDS",
                    "zone": "BATTLE_AREA",
                    "owner": "SELF",
                    "card_type": "UNIT",
                    "traits": traits,
                    "is_token": True,
                    "operator": "==",
                    "value": 0
                })
        
        # NEW: Check for "If there are X or more cards in your trash" (general version)
        if re.search(r'If there are? (\d+) or more cards in your trash', text, re.IGNORECASE):
            trash_match = re.search(r'If there are? (\d+) or more cards in your trash', text, re.IGNORECASE)
            count = int(trash_match.group(1))
            conditions.append({
                "type": "COUNT_CARDS",
                "zone": "TRASH",
                "owner": "SELF",
                "operator": ">=",
                "value": count
            })
        
        # Check for "if there are X or more cards in your trash"
        trash_match = re.search(r'if there are (\d+) or more \(([^)]+)\) cards in your trash', text, re.IGNORECASE)
        if trash_match:
            count = int(trash_match.group(1))
            trait = trash_match.group(2)
            conditions.append({
                "type": "COUNT_CARDS",
                "zone": "TRASH",
                "owner": "SELF",
                "traits": [trait],
                "operator": ">=",
                "value": count
            })
        
        # Check for "If you place a (X) card with this effect"
        mill_check = re.search(r'If you place a \(([^)]+)\) card with this effect', text)
        if mill_check:
            trait = mill_check.group(1)
            conditions.append({
                "type": "CHECK_MILLED_TRAITS",
                "traits": [trait],
                "count": ">=1"
            })
        
        # Check for "while this Unit is attacking"
        if "while this unit is attacking" in text.lower():
            conditions.append({
                "type": "CHECK_UNIT_STATE",
                "state": "ATTACKING"
            })
        
        # Check for "During your turn" timing condition (at start of effect text)
        if text.lower().startswith("during your turn"):
            conditions.append({
                "type": "CHECK_TURN",
                "turn_owner": "SELF"
            })
        
        # Check for "enemy Link Unit is destroyed with damage"
        if re.search(r'enemy Link Unit is destroyed with (battle )?damage', text):
            conditions.append({
                "type": "CHECK_DESTROYED_UNIT",
                "target": "ENEMY",
                "is_link": True,
                "destroyed_by": "DAMAGE"
            })
        
        # Check for "If this is an (X) Unit" - checks if the linked/paired unit has a trait
        trait_check = re.search(r'If this is an? \(([^)]+)\) Unit', text)
        if trait_check:
            trait = trait_check.group(1)
            conditions.append({
                "type": "CHECK_CARD_TRAIT",
                "target": {"selector": "LINKED_UNIT"},
                "required_traits": [trait]
            })
        
        # Check for "enemy effect damage" - damage from enemy card effects
        if "enemy effect damage" in text.lower():
            conditions.append({
                "type": "CHECK_DAMAGE_SOURCE",
                "damage_type": "EFFECT",
                "source_owner": "ENEMY"
            })
        
        # Check for "reduced by an enemy effect"
        if "reduced by an enemy effect" in text.lower():
            conditions.append({
                "type": "CHECK_EFFECT_SOURCE",
                "source_owner": "ENEMY"
            })
        
        # Check for "effect damage from enemy Commands"
        if "effect damage from enemy commands" in text.lower():
            conditions.append({
                "type": "CHECK_DAMAGE_SOURCE",
                "damage_type": "EFFECT",
                "source_owner": "ENEMY",
                "source_card_type": "COMMAND"
            })
        
        # Check for "friendly (Trait) Unit receives effect damage"
        friendly_damage_match = re.search(r'friendly \(([^)]+)\) Unit[s]? receives? effect damage', text, re.IGNORECASE)
        if friendly_damage_match:
            traits_str = friendly_damage_match.group(1)
            traits = [t.strip() for t in traits_str.split('/')]
            conditions.append({
                "type": "CHECK_UNIT_TRAIT",
                "target": {"selector": "FRIENDLY_UNIT"},
                "required_traits": traits,
                "trait_operator": "ANY" if '/' in traits_str else "ALL"
            })
        
        # Check for paired pilot trait conditions (old format without in trigger)
        if "･(" in text and ") Pilot】" in text and not pilot_trait_match:
            # This is the old format we already handle
            start = text.index("･(") + 2
            end = text.index(") Pilot】")
            pilot_trait = text[start:end]
            
            conditions.append({
                "type": "CHECK_CARD_STATE",
                "target": {"selector": "PAIRED_PILOT"},
                "paired_pilot_traits": [pilot_trait]
            })
        
        # NEW CONDITIONS FOR REMAINING 18 CARDS
        
        # Pilot level check (for pairing triggers)
        pilot_level_match = re.search(r'Pilot that is Lv\.(\d+) or lower', text)
        if pilot_level_match:
            conditions.append({
                "type": "CHECK_PILOT_LEVEL",
                "operator": "<=",
                "value": int(pilot_level_match.group(1))
            })
        
        # Paired pilot level check (for When Paired triggers)
        paired_level_match = re.search(r'Lv\.(\d+) or Higher Pilot', text)
        if paired_level_match:
            conditions.append({
                "type": "CHECK_PAIRED_PILOT_LEVEL",
                "operator": ">=",
                "value": int(paired_level_match.group(1))
            })
        
        # Card name substring check
        card_name_match = re.search(r'with "([^"]+)" in its card name', text)
        if card_name_match:
            conditions.append({
                "type": "CHECK_CARD_NAME_SUBSTRING",
                "substring": card_name_match.group(1)
            })
        
        # Check for "if you have X in play" (Pilot/Unit type detection)
        in_play_match = re.search(r'if you have .+ \(([^)]+)\) (Pilot|Unit) in play', text, re.IGNORECASE)
        if in_play_match:
            traits = self._extract_traits(text)
            card_type = in_play_match.group(2).upper()
            conditions.append({
                "type": "COUNT_CARDS",
                "zone": "BATTLE_AREA",
                "owner": "SELF",
                "card_type": card_type,
                "traits": traits,
                "operator": ">=",
                "value": 1
            })
        
        # Turn-based (opponent's turn) for continuous effects
        if "during your opponent's turn" in text.lower():
            conditions.append({
                "type": "CHECK_TURN",
                "turn_owner": "OPPONENT"
            })
        
        # Check for "if this is a X Unit" (color check for paired unit)
        color_unit_match = re.search(r'if this is an? (red|blue|green|purple|white|yellow) Unit', text, re.IGNORECASE)
        if color_unit_match:
            color = color_unit_match.group(1).lower()
            conditions.append({
                "type": "CHECK_PAIRED_UNIT_COLOR",
                "required_color": color
            })
        
        return conditions
    
    def _extract_traits(self, text: str) -> List[str]:
        """Extract traits from parentheses"""
        traits = []
        
        # Find all text in parentheses that are traits
        import re
        
        # Strategy: Find (trait) patterns but exclude token specifications
        # Token specs follow pattern: [TokenName]((Trait)･AP･HP)
        # We want to extract (trait) from general text but not from token specs
        
        # First, remove all token specifications from text
        text_without_tokens = re.sub(r'\[[^\]]+\]\([^)]+\) Unit token', '', text)
        
        # Now extract traits from remaining text
        matches = re.findall(r'\(([^)]+)\)', text_without_tokens)
        
        for match in matches:
            # Skip descriptions (long text)
            if len(match) > 30:
                continue
            # Check if it contains "/" (multiple traits)
            if "/" in match:
                traits.extend([t.strip() for t in match.split("/")])
            else:
                traits.append(match.strip())
        
        return traits
    
    def _parse_actions(self, text: str, card_data: Dict) -> List[Dict]:
        """Parse actions from text"""
        actions = []
        import re
        
        # FIX 2: DEPLOY TOKEN with keyword extraction
        # Pattern: "Deploy 1 [Token-Name]((Traits)･AP X･HP Y･<Keyword>) Unit token"
        # Note: Token spec may have nested/double parentheses like ((Trait)･...)
        token_deploy_match = re.search(r'Deploy (\d+) \[([^\]]+)\]\((.+?)\) Unit token', text)
        if token_deploy_match:
            count = int(token_deploy_match.group(1))
            token_name = token_deploy_match.group(2)
            token_spec = token_deploy_match.group(3)
            
            # Parse token specification
            token_data = {
                "name": token_name,
                "ap": 0,
                "hp": 0,
                "traits": [],
                "keywords": []
            }
            
            # Extract traits (first item in parentheses, before ･)
            traits_match = re.search(r'^([^･]+)(?:･|$)', token_spec)
            if traits_match:
                trait_text = traits_match.group(1).strip()
                # Remove parentheses if present
                trait_text = trait_text.strip('()')
                token_data["traits"] = [trait_text]
            
            # Extract AP
            ap_match = re.search(r'AP\s*(\d+)', token_spec)
            if ap_match:
                token_data["ap"] = int(ap_match.group(1))
            
            # Extract HP
            hp_match = re.search(r'HP\s*(\d+)', token_spec)
            if hp_match:
                token_data["hp"] = int(hp_match.group(1))
            
            # FIX 2: Extract keywords from token spec (e.g., <Blocker>)
            keyword_matches = re.findall(r'<([^>]+)>', token_spec)
            for keyword_str in keyword_matches:
                parts = keyword_str.split()
                keyword_name = parts[0].strip().upper().replace('-', '_')
                value = None
                if len(parts) > 1:
                    try:
                        value = int(parts[1])
                    except ValueError:
                        pass
                
                token_data["keywords"].append({
                    "keyword": keyword_name,
                    "value": value
                })
            
            # Determine state (active or rested)
            state = "RESTED" if "rested" in text.lower() else "ACTIVE"
            
            actions.append({
                "type": "DEPLOY_TOKEN",
                "token": token_data,
                "count": count,
                "state": state
            })
        
        # Place top X cards into trash (MILL)
        mill_match = re.search(r'Place the top (\d+) cards? of your deck into your trash', text)
        if mill_match:
            amount = int(mill_match.group(1))
            actions.append({
                "type": "MILL",
                "target": "SELF",
                "amount": amount,
                "destination": "TRASH"
            })
        
        # Deploy from trash with cost payment
        deploy_match = re.search(r'Choose 1 Unit card that is Lv\.(\d+) or lower from your trash\. Pay its cost to deploy it', text)
        if deploy_match:
            max_level = int(deploy_match.group(1))
            actions.append({
                "type": "DEPLOY_FROM_ZONE",
                "source_zone": "TRASH",
                "target": {
                    "selector": "SELF_TRASH",
                    "card_type": "UNIT",
                    "filters": {
                        "level": {
                            "operator": "<=",
                            "value": max_level
                        }
                    }
                },
                "pay_cost": True,
                "destination": "BATTLE_AREA"
            })
        
        # Shield protection
        if "shield area cards can't receive damage" in text.lower():
            # Extract level filter if present
            level_match = re.search(r'from enemy Units that are Lv\.(\d+) or lower', text)
            source_filter = {}
            if level_match:
                source_filter = {
                    "level": {
                        "operator": "<=",
                        "value": int(level_match.group(1))
                    }
                }
            
            duration = "THIS_BATTLE" if "During this battle" in text else "THIS_TURN"
            actions.append({
                "type": "GRANT_PROTECTION",
                "target": "SELF_SHIELDS",
                "protection_type": "PREVENT_DAMAGE",
                "source_filter": source_filter,
                "duration": duration
            })
        
        # Set resource as active
        if "choose 1 of your Resources. Set it as active" in text:
            actions.append({
                "type": "SET_ACTIVE",
                "target": {
                    "selector": "FRIENDLY_RESOURCE",
                    "count": 1,
                    "selection_method": "CHOOSE"
                }
            })
        
        # Stat modifications ("It gets AP-2", "It gets HP+1", etc.)
        stat_mod_match = re.search(r'(It|They|This Unit) gets? (AP|HP)([+-])(\d+)', text, re.IGNORECASE)
        if stat_mod_match:
            stat_type = stat_mod_match.group(2).upper()
            operator = stat_mod_match.group(3)
            value = int(stat_mod_match.group(4))
            
            # Make negative if operator is -
            if operator == '-':
                value = -value
            
            # Determine target from context
            target = self._parse_choose_target(text)
            if not target:
                # Check if "It" or "They" refers to an enemy or friendly unit
                if "choose 1 enemy unit" in text.lower():
                    target = {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"}
                elif "choose 1 of your" in text.lower() or "choose 1 friendly" in text.lower():
                    target = {"selector": "FRIENDLY_UNIT", "count": 1, "selection_method": "CHOOSE"}
                else:
                    target = {"selector": "SELF"}
            
            duration = "THIS_TURN"
            if "during this turn" in text.lower():
                duration = "THIS_TURN"
            elif "during this battle" in text.lower():
                duration = "THIS_BATTLE"
            
            actions.append({
                "type": "MODIFY_STAT",
                "target": target,
                "stat": stat_type,
                "value": value,
                "duration": duration
            })
        
        # Attack targeting grants ("it may choose... as its attack target")
        if "may choose" in text.lower() and "attack target" in text.lower():
            # Extract filters for the target
            target_filters = {}
            
            # Level filter
            level_match = re.search(r'Lv\.(\d+) or lower', text)
            if level_match:
                target_filters["level"] = {"operator": "<=", "value": int(level_match.group(1))}
            
            # HP filter
            hp_match = re.search(r'(\d+) or less (AP|HP)', text)
            if hp_match:
                stat_value = int(hp_match.group(1))
                stat_name = hp_match.group(2).upper()
                target_filters[stat_name.lower()] = {"operator": "<=", "value": stat_value}
            
            # State filter
            if "active enemy Unit" in text.lower():
                target_filters["state"] = "ACTIVE"
            elif "rested enemy Unit" in text.lower():
                target_filters["state"] = "RESTED"
            
            # Determine who gets the ability
            target = self._parse_choose_target(text)
            if not target:
                target = {"selector": "SELF"}
            
            duration = "THIS_TURN"
            if "during this turn" in text.lower():
                duration = "THIS_TURN"
            elif "during this battle" in text.lower():
                duration = "THIS_BATTLE"
            
            actions.append({
                "type": "GRANT_ATTACK_TARGETING",
                "target": target,
                "target_restrictions": target_filters,
                "duration": duration,
                "description": "Can choose additional units as attack targets"
            })
        
        # Exile cards from trash
        exile_match = re.search(r'Choose (\d+) (\w+) Unit cards from your trash\. Exile them', text)
        if exile_match:
            count = int(exile_match.group(1))
            color = exile_match.group(2).lower()
            actions.append({
                "type": "EXILE_CARDS",
                "source_zone": "TRASH",
                "target": {
                    "selector": "SELF_TRASH",
                    "card_type": "UNIT",
                    "filters": {
                        "color": color
                    },
                    "count": count
                },
                "destination": "BANISH"
            })
        
        # Destroy unit
        if "Destroy it" in text or "Destroy them" in text:
            # Check if it's a destroy action (not "can't be destroyed")
            if "can't be destroyed" not in text.lower():
                target = self._parse_choose_target(text)
                if not target:
                    # Check for "instead" pattern (conditional alternative)
                    if "instead" in text.lower():
                        # Parse the alternative target
                        # Pattern: "Choose 1... Lv.X or lower. Destroy it. If..., choose 1... Lv.Y or lower instead."
                        # The "instead" target overrides based on condition
                        # For now, parse the primary target
                        pass
                    # Default to enemy unit
                    target = {
                        "selector": "ENEMY_UNIT",
                        "count": 1,
                        "selection_method": "CHOOSE"
                    }
                actions.append({
                    "type": "DESTROY_CARD",
                    "target": target
                })
        
        # Add to hand
        if "Add this card to your hand" in text or "add this card to your hand" in text:
            actions.append({
                "type": "ADD_TO_HAND",
                "target": {"selector": "SELF"},
                "source": "SHIELDS"  # Usually from shields for Burst effects
            })
        
        # Add shields to hand
        if "Add 1 of your Shields to your hand" in text or "add 1 of your shields to your hand" in text.lower():
            actions.append({
                "type": "ADD_TO_HAND",
                "target": {"selector": "SELF_SHIELDS", "count": 1},
                "source": "SHIELDS"
            })
        
        # Deploy this card
        if "Deploy this card" in text:
            actions.append({
                "type": "DEPLOY_SELF"
            })
        
        # Draw cards (skip if draw is inside "If you do" - handled as conditional_actions)
        if "draw" in text.lower() or "Draw" in text:
            match = re.search(r'[Dd]raw (\d+)', text)
            if match:
                if_you_do_pos = text.find("If you do")
                draw_pos = match.start()
                if if_you_do_pos == -1 or draw_pos < if_you_do_pos:
                    amount = int(match.group(1))
                    actions.append({
                        "type": "DRAW",
                        "target": "SELF",
                        "amount": amount
                    })
        
        # Deal damage
        if "Deal" in text and "damage" in text:
            # Parse damage amount and target
            match = re.search(r'Deal (\d+) damage', text)
            if match:
                amount = int(match.group(1))
                
                # Check if there's a "Choose X" target before this
                target = self._parse_choose_target(text)
                if not target:
                    # Use default damage target parser
                    target = self._parse_damage_target(text)
                
                actions.append({
                    "type": "DAMAGE_UNIT",
                    "target": target,
                    "amount": amount,
                    "damage_type": "EFFECT"  # Damage from card effects is effect damage
                })
        
        # NEW: Handle "【Main】/【Action】" pattern (slash indicates either timing)
        # This is a shorthand meaning the effect can be activated during either Main OR Action phase
        if re.search(r'【Main】/【Action】', text):
            # The effect should already have ACTION_PHASE trigger from _extract_triggers
            # We just need to make sure actions are parsed
            pass
        
        # Rest unit
        if "Rest it" in text or "Rest them" in text or ("Rest " in text and " Unit" in text):
            # Target is implied from "Choose 1 enemy Unit" OR explicit "Rest X"
            target = self._parse_choose_target(text)
            if target:
                actions.append({
                    "type": "REST_UNIT",
                    "target": target
                })
        
        # Grant keyword
        if "gains <" in text or "and <" in text:
            keyword_match = self._extract_granted_keyword(text)
            if keyword_match:
                target = self._parse_choose_target(text)
                if not target:
                    target = {"selector": "SELF"}
                
                actions.append({
                    "type": "GRANT_KEYWORD",
                    "target": target,
                    "keyword": keyword_match["keyword"],
                    "value": keyword_match["value"],
                    "duration": self._parse_duration(text)
                })
        
        # Recover HP
        if "recover" in text.lower() and "HP" in text:
            match = re.search(r'recover[s]? (\d+) HP', text)
            if match:
                amount = int(match.group(1))
                target = self._parse_choose_target(text)
                if not target:
                    target = {"selector": "SELF"}
                
                actions.append({
                    "type": "RECOVER_HP",
                    "target": target,
                    "amount": amount
                })
        
        # Place resource
        if "Place" in text and "Resource" in text:
            state = "RESTED" if "rested" in text else "ACTIVE"
            resource_type = "EX" if "EX" in text else "NORMAL"
            
            actions.append({
                "type": "PLACE_RESOURCE",
                "resource_type": resource_type,
                "state": state
            })
        
        # Mill (place top card into trash)
        # Only parse if NOT in a conditional "If you do" section
        if "place the top card of your deck into your trash" in text.lower():
            if_you_do_pos = text.find("If you do")
            mill_phrase_pos = text.lower().find("place the top card of your deck into your trash")
            
            # Only add as a primary action if it's before "If you do" or there's no "If you do"
            if if_you_do_pos == -1 or mill_phrase_pos < if_you_do_pos:
                actions.append({
                    "type": "MILL",
                    "amount": 1,
                    "source": "DECK",
                    "destination": "TRASH"
                })
        
        # Discard
        # Only parse if NOT preceded by "If you do" (those will be handled separately)
        if "discard" in text.lower() and "If you do" not in text.split("discard")[0]:
            match = re.search(r'discard (\d+)', text, re.IGNORECASE)
            if match:
                # Make sure this discard isn't after "If you do"
                discard_pos = text.lower().find("discard")
                if_you_do_pos = text.find("If you do")
                
                if if_you_do_pos == -1 or discard_pos < if_you_do_pos:
                    actions.append({
                        "type": "DISCARD",
                        "target": "SELF",
                        "amount": int(match.group(1))
                    })
        
        # Handle "If you do" and "Then" chains
        # Rule 5-20-1: "If you do" - succeeding only if preceding resolves
        # Rule 5-20-2: "Then" - succeeding runs even if preceding fails
        if "If you do" in text:
            parts = text.split("If you do")
            if len(parts) == 2:
                conditional_text = parts[1].strip().rstrip('.')
                primary_text = parts[0].strip()

                # Split by "Then," - part after "Then" always runs (Rule 5-20-2)
                then_actions = []
                if " Then," in conditional_text or " then," in conditional_text:
                    then_match = re.search(r'\s+[Tt]hen,?\s*(.+)$', conditional_text)
                    if then_match:
                        then_part = then_match.group(1).strip()
                        conditional_text = conditional_text[:then_match.start()].strip()
                        discard_match = re.search(r'discard (\d+)', then_part, re.IGNORECASE)
                        if discard_match:
                            then_actions.append({
                                "type": "DISCARD",
                                "target": "SELF",
                                "amount": int(discard_match.group(1))
                            })

                conditional_actions = []
                if "place the top card of your deck into your trash" in conditional_text.lower():
                    conditional_actions.append({
                        "type": "MILL",
                        "amount": 1,
                        "source": "DECK",
                        "destination": "TRASH"
                    })
                if "draw" in conditional_text.lower():
                    match = re.search(r'draw (\d+)', conditional_text, re.IGNORECASE)
                    if match:
                        conditional_actions.append({
                            "type": "DRAW",
                            "target": "SELF",
                            "amount": int(match.group(1))
                        })
                if "discard" in conditional_text.lower() and not then_actions:
                    match = re.search(r'discard (\d+)', conditional_text, re.IGNORECASE)
                    if match:
                        conditional_actions.append({
                            "type": "DISCARD",
                            "target": "SELF",
                            "amount": int(match.group(1))
                        })

                if conditional_actions:
                    if "rest this base" in primary_text.lower():
                        actions.append({
                            "type": "REST_CARD",
                            "target": {"selector": "SELF"},
                            "optional": True,
                            "conditional_actions": conditional_actions
                        })
                    else:
                        for i in range(len(actions) - 1, -1, -1):
                            act = actions[i]
                            if act["type"] == "DAMAGE_UNIT" and "deal" in primary_text.lower():
                                act["conditional_actions"] = conditional_actions
                                break
                            elif act["type"] == "DRAW" and "draw" in primary_text.lower():
                                act["conditional_actions"] = conditional_actions
                                break
                            elif act["type"] == "DISCARD" and "discard" in primary_text.lower():
                                act["conditional_actions"] = conditional_actions
                                break

                for ta in then_actions:
                    actions.append(ta)
        
        # NEW ACTIONS FOR REMAINING 18 CARDS
        
        # Override cost/level (play as if it has 0 cost)
        if "play this card as if it has 0 cost" in text or "as if it has 0 Lv. and cost" in text:
            actions.append({
                "type": "OVERRIDE_PLAY_COST",
                "cost": 0,
                "level": 0 if "0 Lv." in text else None
            })
        
        # Stat equals count of unique names in zone
        unique_count_match = re.search(r'number of .+ with unique names in your trash', text)
        if unique_count_match:
            traits = self._extract_traits(text)
            card_types = []
            if "Pilot cards" in text or "Pilot card" in text:
                card_types.append("PILOT")
            if "Command cards" in text or "Command card" in text:
                card_types.append("COMMAND")
            
            actions.append({
                "type": "STAT_EQUALS_COUNT",
                "stat": "AP",
                "count_source": {
                    "zone": "TRASH",
                    "owner": "SELF",
                    "card_types": card_types,
                    "traits": traits,
                    "unique_names_only": True
                }
            })
        
        # Return card to hand
        if "Return it to its owner's hand" in text or "return the enemy Unit to its owner's hand" in text:
            # Check if there's a target already parsed
            target = self._parse_choose_target(text)
            if not target:
                # Might be referring to a unit from battle damage trigger
                target = {"selector": "ENEMY_UNIT", "context": "DAMAGED_UNIT"}
            
            actions.append({
                "type": "RETURN_TO_HAND",
                "target": target
            })
        
        # Destroy card (for non-optional destroy in specific contexts)
        if re.search(r'destroy that enemy Unit', text, re.IGNORECASE):
            actions.append({
                "type": "DESTROY_CARD",
                "target": {"selector": "ENEMY_UNIT", "context": "DAMAGED_UNIT"}
            })
        
        # Replace rest target (for replacement effects)
        if "you may rest this Unit instead" in text:
            actions.append({
                "type": "REPLACE_REST_TARGET",
                "original_target": "BASE",
                "new_target": "SELF",
                "optional": True
            })
        
        return actions
    
    def _parse_damage_target(self, text: str) -> Dict:
        """Parse damage target from text"""
        target = {"selector": "ENEMY_UNIT", "count": 1, "selection_method": "CHOOSE"}
        
        # Check for "all Units"
        if "all Units" in text or "all enemy Units" in text:
            target["selection_method"] = "ALL"
        
        # Check for filters
        if "rested" in text:
            target["filters"] = {"state": "RESTED"}
        
        if "Lv." in text:
            import re
            match = re.search(r'Lv\.(\d+) or lower', text)
            if match:
                level = int(match.group(1))
                if "filters" not in target:
                    target["filters"] = {}
                target["filters"]["level"] = {"operator": "<=", "value": level}
        
        if "or less HP" in text:
            import re
            match = re.search(r'(\d+) or less HP', text)
            if match:
                hp = int(match.group(1))
                if "filters" not in target:
                    target["filters"] = {}
                target["filters"]["hp"] = {"operator": "<=", "value": hp}
        
        return target
    
    def _parse_choose_target(self, text: str) -> Optional[Dict]:
        """Parse 'Choose 1' target from text"""
        if "Choose 1" not in text and "Choose 1 to" not in text and "choose 1" not in text and "choose 1 to" not in text:
            return None
        
        import re
        
        # Check for range count first (e.g., "Choose 1 to 2")
        range_match = re.search(r'[Cc]hoose (\d+) to (\d+)', text)
        if range_match:
            target = {
                "count": {"min": int(range_match.group(1)), "max": int(range_match.group(2))},
                "selection_method": "CHOOSE"
            }
        else:
            target = {"count": 1, "selection_method": "CHOOSE"}
        
        # Determine selector
        if "enemy Unit" in text:
            target["selector"] = "ENEMY_UNIT"
        elif "of your" in text or "friendly" in text:
            target["selector"] = "FRIENDLY_UNIT"
            
            # Check for trait filter
            traits = self._extract_traits(text)
            if traits:
                target["filters"] = {"traits": traits}
        else:
            target["selector"] = "FRIENDLY_UNIT"
        
        # Check for level filter
        level_match = re.search(r'Lv\.(\d+) or lower', text)
        if level_match:
            level = int(level_match.group(1))
            if "filters" not in target:
                target["filters"] = {}
            target["filters"]["level"] = {"operator": "<=", "value": level}
        
        # Check for HP filter
        hp_match = re.search(r'(?:with )?(\d+) or less HP', text)
        if hp_match:
            hp = int(hp_match.group(1))
            if "filters" not in target:
                target["filters"] = {}
            target["filters"]["hp"] = {"operator": "<=", "value": hp}
        
        # Check for AP filter
        ap_match = re.search(r'(?:with )?(\d+) or less AP', text)
        if ap_match:
            ap = int(ap_match.group(1))
            if "filters" not in target:
                target["filters"] = {}
            target["filters"]["ap"] = {"operator": "<=", "value": ap}
        
        # Check for keyword filter
        keyword_match = re.search(r'with <([^>]+)>', text)
        if keyword_match:
            keyword = keyword_match.group(1).upper().replace('-', '_').replace(' ', '_')
            if "filters" not in target:
                target["filters"] = {}
            target["filters"]["keywords"] = [keyword]
        
        # Check for state filter
        if "rested" in text.lower():
            if "filters" not in target:
                target["filters"] = {}
            target["filters"]["state"] = "RESTED"
        elif "active" in text.lower() and "enemy" in text.lower():
            if "filters" not in target:
                target["filters"] = {}
            target["filters"]["state"] = "ACTIVE"
        
        return target
    
    def _extract_granted_keyword(self, text: str) -> Optional[Dict]:
        """Extract keyword being granted"""
        if "gains <" not in text and "and <" not in text:
            return None
        
        # Find the keyword pattern
        import re
        if "gains <" in text:
            start = text.index("gains <") + 7
        elif "and <" in text:
            start = text.index("and <") + 5
        else:
            return None
        
        end = text.index(">", start)
        keyword_text = text[start:end]
        
        parts = keyword_text.split()
        keyword_name = parts[0].strip().upper().replace('-', '_')
        
        value = None
        if len(parts) > 1:
            try:
                value = int(parts[1])
            except ValueError:
                pass
        
        return {"keyword": keyword_name, "value": value}
    
    def _parse_duration(self, text: str) -> str:
        """Parse duration from text"""
        if "during this turn" in text:
            return "THIS_TURN"
        elif "during this battle" in text:
            return "THIS_BATTLE"
        else:
            return "PERMANENT"
    
    def save_effect(self, card_id: str, effect_data: Dict):
        """Save converted effect to file"""
        output_path = Path(self.effects_output_dir) / card_id
        
        with open(output_path, 'w') as f:
            json.dump(effect_data, f, indent=2)
        
        print(f"✓ Converted {card_id}")
    
    def batch_convert(self, card_ids: List[str]):
        """Convert multiple cards"""
        success = 0
        skipped = 0
        
        for card_id in card_ids:
            effect_data = self.convert_card(card_id)
            
            if effect_data:
                self.save_effect(card_id, effect_data)
                success += 1
            else:
                skipped += 1
        
        print(f"\n✓ Conversion complete:")
        print(f"  Success: {success}")
        print(f"  Skipped: {skipped}")


if __name__ == "__main__":
    import sys
    
    converter = CardEffectConverter()
    
    # Test with simple cards
    test_cards = [
        "GD01-007", "GD01-008", "GD01-009", "GD01-012",
        "GD01-014", "GD01-024", "GD01-025", "GD01-028",
        "GD01-029", "GD01-032", "GD01-033", "GD01-038",
        "GD01-043", "GD01-044", "GD01-045", "GD01-048",
        "GD01-049", "GD01-052", "GD01-053", "GD01-055"
    ]
    
    if len(sys.argv) > 1:
        # Convert specified cards
        card_ids = sys.argv[1:]
        converter.batch_convert(card_ids)
    else:
        # Convert test cards
        print("Converting test cards...")
        converter.batch_convert(test_cards)
