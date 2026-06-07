# ExBurst Partial and Unsupported Card Audit

Generated from the latest full run in `logs/exburst_conversion.log` on 2026-06-07. Cross-reference source: `exburst_cards_normalized.json`.

Setup-only RP Resource, Resource, EX Resource, and EX Base cards are excluded from this audit because they are basic game setup features, not card effects to parse.

## Summary

- Run window: 2026-06-07 14:52:02 to 2026-06-07 15:17:02
- LLM model: `deepseek/deepseek-chat-v3-0324`
- Selection: ALL
- Total input cards: 844
- Converted cards with effects in source run: 705
- Ignored cards in source run: 28
- No-effect cards: 111
- Skipped cards: 0
- Runtime: 1499.43s
- Setup cards excluded from audit: 77 processed in this log + 28 already ignored
- Audited non-setup converted cards: 628
- Supported: 524
- Partial: 29
- Unsupported: 75
- Active support scope: 29 partial + 75 unsupported = 104 cards
- Validation issues in active support scope: 118

## Remaining Issue Themes

### Pilot/Pairing Runtime
- Issues: 55
- Cards: 55
- Examples: EB01-076, EB01-084, GD01-101, GD01-103, GD01-106, GD01-110, GD01-112, GD01-113, GD01-114, GD01-116, GD01-119, GD01-122
- Next step: Separate pilot AP/HP metadata from effect actions, then add pair/link state checks and pilot-specific hooks incrementally.

### Cost/Payment Hooks
- Issues: 10
- Cards: 10
- Examples: GD01-002, GD02-110, GD03-058, GD03-085, GD03-130, GD04-021, GD04-050, GD04-075, GD04-129, ST10-014
- Next step: Only non-setup cards remain here; model replacement costs or deploy/play cost modifiers as cost hooks when they appear on real cards.

### Stat Modifier Shape
- Issues: 10
- Cards: 9
- Examples: GD03-030, GD03-059, GD04-034, GD04-053, GD04-057, GD04-065, GD04-068, GD04-108, GD04-113
- Next step: Normalize modifier/amount/value variants into stat + modification fields, while routing COST and LEVEL modifiers to cost hooks.

### Action Vocabulary
- Issues: 9
- Cards: 9
- Examples: GD01-117, GD01-121, GD02-118, GD03-077, GD03-109, GD03-114, GD04-101, GD04-117, ST01-014
- Next step: Add conservative aliases only where the runtime already has an equivalent movement or action primitive.

### Return-To-Hand Action
- Issues: 9
- Cards: 8
- Examples: EB01-044, GD01-068, GD01-117, GD01-122, GD02-118, GD03-077, GD03-122, GD04-072
- Next step: Represent RETURN_LOOKED_TO_HAND and selected-card return flows as explicit movement from the current revealed/selected context.

### LLM Parser Fallback
- Issues: 6
- Cards: 4
- Examples: EB01-075, GD03-070, GD04-037, ST03-013
- Next step: Broaden the parser enum and normalizers for common rejected shapes so recoverable LLM output becomes partial instead of full unsupported fallback.

### Empty Action
- Issues: 5
- Cards: 5
- Examples: EB01-044, GD03-008, GD03-040, GD04-002, GD04-035
- Next step: Infer action type from effect fields/raw text when possible; otherwise keep the card unsupported only for the missing action span.

### Selector Vocabulary
- Issues: 4
- Cards: 3
- Examples: EB01-017, EB01-025, EB01-055
- Next step: Add selector aliases such as ALL_PLAYERS, FRIENDLY_HAND, and ENEMY_SHIELDS only where zones and ownership are already modeled.

### Empty Condition
- Issues: 3
- Cards: 3
- Examples: GD01-065, GD03-125, GD04-049
- Next step: Normalize blank condition objects from the surrounding trigger text, or drop them when the condition carries no executable semantics.

### Unsupported LLM Runtime Mechanic
- Issues: 3
- Cards: 3
- Examples: GD02-098, GD03-124, GD03-125
- Next step: Review representative cards and split true runtime gaps from parser vocabulary aliases.

### Condition Vocabulary
- Issues: 2
- Cards: 2
- Examples: GD01-059, GD01-082
- Next step: Map remaining bespoke conditions to CHECK_* predicates or add a narrow condition primitive for the recurring pattern.

### Keyword Grant Shape
- Issues: 2
- Cards: 2
- Examples: EB01-041, GD03-037
- Next step: Recover the granted keyword from raw text or reject the parser output when the keyword cannot be determined.

## Recommended Next Phase

1. Split pilot metadata from executable effects so AP/HP pairing text no longer forces cards into unsupported status.
2. Normalize stat modifier shapes and cost/level modifiers, routing cost and level changes into a cost-hook path when they appear on real cards.
3. Add narrowly scoped runtime support for return-to-hand flows, action aliases, selector aliases, and keyword grant shape.
4. Expand parser enums and normalizers for the remaining recoverable LLM fallbacks.
5. Rerun only the 104 non-setup affected cards to measure what remains.

## Partial Cards (29)

### EB01-017 - Haro [UNIT]
- Themes: selector_vocabulary
- Issue: unknown_selector: FRIENDLY_PLAYER - Selector is not resolved by the runtime
- Text: 【Destroyed】If this Unit is destroyed with battle damage, you and the player who destroyed this Unit draw 1.

### EB01-025 - Tallgeese II [UNIT]
- Themes: selector_vocabulary
- Issue: unknown_selector: FRIENDLY_PLAYER - Selector is not resolved by the runtime
- Issue: unknown_selector: ENEMY_RESOURCE - Selector is not resolved by the runtime
- Text: 【Deploy ･ Development 2】You may exile the specified number of (G Generation) cards from your trash from the game. If you do, activate the following effect:; ▫️All players place 1 EX Resource.; 【During Pair】While your opponent has an EX Resource, this Unit c...

### EB01-041 - Strike Freedom Gundam (EX) [UNIT]
- Themes: keyword_grant_shape
- Issue: missing_keyword: None - Keyword grant must name the granted keyword
- Text: 【High-Maneuver】(This Unit can't be blocked.); 【Deploy】Choose 1 Unit with 4 or less HP belonging to each enemy player. Return them to their owner's hands.

### EB01-055 - Dom Gross Beil [UNIT]
- Themes: selector_vocabulary
- Issue: unknown_selector: FRIENDLY_SHIELDS - Selector is not resolved by the runtime
- Text: if there are 2 or more enemy players and this Unit is rested, friendly Shields can't receive battle damage from enemy Units.

### GD01-059 - Zee Zulu [UNIT]
- Themes: condition_vocabulary
- Issue: unknown_condition: CHECK_TARGET - Condition is not executed by the runtime
- Text: 【Attack】If you are attacking the enemy player, this Unit gets AP+2 during this battle.

### GD01-065 - Freedom Gundam [UNIT]
- Themes: empty_condition
- Issue: unknown_condition: <empty> - Condition is not executed by the runtime
- Text: <Blocker> (Rest this Unit to change the attack target to it.); 【During Pair】【Once per Turn】When you pair a Pilot with this Unit or one of your white Units, choose 1 enemy Unit. It gets AP-2 during this turn.

### GD01-082 - Gundam Aerial (Mirasoul Flight Unit) [UNIT]
- Themes: condition_vocabulary
- Issue: unknown_condition: CHECK_PAIR_STATUS - Condition is not executed by the runtime
- Text: 【During Pair】【Activate･Action】【Once per Turn】②：Choose 1 enemy Unit. It gets AP-1 during this battle.

### GD01-121 - Midair Modifications [COMMAND]
- Themes: action_vocabulary
- Issue: unknown_action: ACTIVATE_MAIN - Action is not executed by the runtime
- Text: 【Burst】Activate this card's 【Main】.; 【Main】Choose 1 rested Unit with <Blocker>. Set it as active. It can't attack during this turn.

### GD03-008 - Bolinoak Sammahn [UNIT]
- Themes: empty_action
- Issue: unknown_action: <empty> - Action is not executed by the runtime
- Text: 【During Pair】This Unit gains <Repair 2>. (At the end of your turn, this Unit recovers the specified number of HP.)

### GD03-030 - Gundam Kyrios (Tail Unit Flight Mode) [UNIT]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'type': 'MODIFY_STAT', 'target': {'selector': 'SELF'}, 'duration': 'PERMANENT', 'modification': '-1'} - Stat modifier must include stat and modification fields
- Text: While you have a (CB) Link Unit in play, this card in your hand gets cost -1.

### GD03-037 - Bertigo [UNIT]
- Themes: keyword_grant_shape
- Issue: missing_keyword: None - Keyword grant must name the granted keyword
- Text: 【During Link】During your turn, while this Unit is battling an enemy Unit with a 【Destroyed】 effect, it gains <First Strike>. (While this Unit is attacking, it deals damage before the enemy Unit.)

### GD03-040 - Gundam Virsago & Gundam Ashtaron [UNIT]
- Themes: empty_action
- Issue: unknown_action: <empty> - Action is not executed by the runtime
- Text: 【During Link】This Unit gains <High-Maneuver>. (This Unit can't be blocked.)

### GD03-059 - Zedas R [UNIT]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'stat': 'AP', 'amount': 2, 'duration': 'THIS_TURN', 'filters': {'traits': ['Vagan']}, 'type': 'MODIFY_STAT', 'target': {'selector': 'FRIENDLY_UNIT'}} - Stat modifier must include stat and modification fields
- Text: 【Attack】You may choose 1 (Vagan) card from your trash. Exile it from the game. If you do, choose 1 of your (Vagan) Units. It gets AP+2 during this turn.

### GD03-109 - Improved Technique [COMMAND]
- Themes: action_vocabulary
- Issue: unknown_action: ACTIVATE_MAIN - Action is not executed by the runtime
- Text: 【Burst】Activate this card's 【Main】.; 【Main】/【Action】Choose 1 enemy Unit that is Lv.4 or lower. Deal 3 damage to it. If there are 2 or more cards with "Improved Technique" in their card name in your trash, choose 1 enemy Unit instead.

### GD03-114 - Look of Determination [COMMAND]
- Themes: action_vocabulary
- Issue: unknown_action: ACTIVATE_ACTION - Action is not executed by the runtime
- Text: 【Burst】Activate this card's 【Action】.; 【Action】Choose 1 active enemy Unit that is Lv.2 or lower. Destroy it. If there are 10 or more cards in your trash, choose 1 active enemy Unit that is Lv.4 or lower instead.

### GD04-002 - Penelope (Flight Form) [UNIT]
- Themes: empty_action
- Issue: unknown_action: <empty> - Action is not executed by the runtime
- Text: During your turn, all your (Earth Federation) Units get AP+1.; 【Deploy】During this turn, when one of your (Earth Federation) Units destroys an enemy Unit with battle damage, choose 1 enemy Unit with 5 or less HP. Rest it.

### GD04-034 - Gundam Kyrios [UNIT]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'type': 'MODIFY_STAT', 'target': {'selector': 'SELF'}, 'duration': 'PERMANENT', 'stat': 'AP'} - Stat modifier must include stat and modification fields
- Text: <First Strike> (While this Unit is attacking, it deals damage before the enemy Unit.); 【During Link】This Unit gets AP+2 for each of your rested (CB) Units.

### GD04-035 - Ξ Gundam [UNIT]
- Themes: empty_action
- Issue: unknown_action: <empty> - Action is not executed by the runtime
- Text: 【Deploy】Choose 1 of your (Mafty) Units. When it destroys an enemy Unit with battle damage during this turn, if you have 3 or less cards in your hand, draw 1.

### GD04-049 - Gundam DX [UNIT]
- Themes: empty_condition
- Issue: unknown_condition: <empty> - Condition is not executed by the runtime
- Text: <Suppression> (Damage to Shields by an attack is dealt to the first 2 cards simultaneously.); 【During Pair】【Attack】If you are attacking the enemy player, you may choose 7 (Vulture) cards from your trash. Exile them from the game. If you do, choose 1 enemy U...

### GD04-053 - Rey's Blaze Zaku Phantom [UNIT]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'type': 'MODIFY_STAT', 'target': {'selector': 'SELF'}, 'modification': '-1'} - Stat modifier must include stat and modification fields
- Text: 【During Link】【Once per Turn】When this Unit receives damage from an enemy, reduce it by 1.

### GD04-057 - Gundam Nadleeh [UNIT]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'amount': None, 'conditions': [{'type': 'CHECK_STAT', 'target': 'ENEMY_UNIT', 'stat': 'LEVEL', 'operator': '<=', 'value': 6}, {'type': 'COUNT_CARDS', 'zone': 'SELF_TRASH', 'filters': {'card_type': 'UNIT', 'text_contains': 'Gundam Virtue'}}], 'stat': 'AP', 'modification_type': 'REDUCE', 'duration': 'THIS_TURN', 'use_count_from_condition': {'index': 1}, 'type': 'MODIFY_STAT', 'target': {'selector': 'ENEMY_UNIT'}} - Stat modifier must include stat and modification fields
- Text: 【Deploy】Choose 1 enemy Unit that is Lv.6 or lower. During this turn, reduce its AP by an amount equal to the number of Unit cards with "Gundam Virtue" in their card names in your trash.

### GD04-065 - Unicorn Gundam 02 Banshee Norn (Destroy Mode) [UNIT]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'type': 'MODIFY_STAT', 'target': {'selector': 'ENEMY_UNIT'}, 'duration': 'THIS_TURN', 'stat': 'AP'} - Stat modifier must include stat and modification fields
- Text: 【During Link】【Activate･Main】Exile 3 blue cards from your trash：Set this Unit as active. It can't choose the enemy player as its attack target during this turn.; 【Attack】All enemy Units get AP-1 during this turn.

### GD04-068 - Silver Bullet [UNIT]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'type': 'MODIFY_STAT', 'target': {'selector': 'SELF'}, 'modification': '-3'} - Stat modifier must include stat and modification fields
- Text: <Blocker> (Rest this Unit to change the attack target to it.); When this Unit receives effect damage from an enemy, reduce it by 3.

### GD04-070 - Al-Saachez's AEU Enact Custom Moralia Development Experiment Type [UNIT]
- Themes: pilot_pairing_runtime
- Issue: unknown_action: ON_PAIR_PILOT - Action is not executed by the runtime
- Text: 【Deploy】You may pair 1 Pilot card with "Ali al-Saachez" in its card name from your hand with this Unit.

### GD04-101 - Kindhearted [COMMAND]
- Themes: action_vocabulary
- Issue: unknown_action: ACTIVATE_MAIN - Action is not executed by the runtime
- Text: 【Burst】Activate this card's 【Main】.; 【Main】/【Action】During this turn, friendly Units can't be destroyed by enemy effects. Then, draw 1.

### GD04-113 - Damage Control [COMMAND]
- Themes: stat_modifier_shape
- Issue: malformed_stat_modifier: {'type': 'MODIFY_STAT', 'target': {'selector': 'FRIENDLY_UNIT'}, 'duration': 'THIS_BATTLE', 'modification': '-3'} - Stat modifier must include stat and modification fields
- Text: 【Burst】Choose 1 enemy Unit. It gets AP-2 during this turn.; 【Action】Choose 1 of your Units. During this battle, reduce battle damage it receives by 3.

### GD04-117 - Graceful Demeanor [COMMAND]
- Themes: action_vocabulary
- Issue: unknown_action: ACTIVATE_ACTION - Action is not executed by the runtime
- Text: 【Burst】Activate this card's 【Action】.; 【Action】Choose 1 to 2 enemy Units that are Lv.3 or lower. Return them to their owners' hands.

### ST01-014 - Unforeseen Incident [COMMAND]
- Themes: action_vocabulary
- Issue: unknown_action: ACTIVATE_MAIN - Action is not executed by the runtime
- Text: 【Burst】Activate this card's 【Main】.; 【Main】/【Action】Choose 1 enemy Unit. It gets AP-3 during this turn.

### T-014 - Ad Balloon [UNIT TOKEN]
- Themes: pilot_pairing_runtime
- Issue: unknown_action: ON_PAIR_PILOT - Action is not executed by the runtime
- Text: This Unit can't be set as active or paired with a Pilot.

## Unsupported Cards (75)

### EB01-044 - Justice Gundam (EX) [UNIT]
- Themes: empty_action, return_to_hand_action
- Issue: unknown_action: <empty> - Action is not executed by the runtime
- Issue: unsupported_llm_effect: EB01-044-E2 - requires selecting enemy player with most Units and returning their Unit to hand
- Text: 【Blocker】(Rest this Unit to change the attack target to it.); 【Deploy】If there are 2 or more enemy players, choose 1 Unit belonging to an enemy player with the most Units. Return it to its owner's hand.

### EB01-075 - Fierce Enemy Assault [COMMAND]
- Themes: llm_parser_fallback
- Issue: unsupported_llm_effect: EB01-075-E1 - LLM parser failed: InstructorRetryException: 1 validation error for ParsedCard
- Text: 【Main】/【Action】Choose 1 to 2 enemy Units with 2 or less HP. Rest them.

### EB01-076 - Gerbera Strait [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: EB01-076-E3 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly (G Generation) Unit. It recovers 3 HP.; 【Pilot】Lowe Guele (G Generation / Durability).

### EB01-084 - 30cm Cannon (APFSDS Round) [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: EB01-084-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 Unit with【Blocker】. Set it as active. It can't attack during this turn.; 【Pilot】Demeziere Sonnen (G Generation / Attack).

### GD01-002 - Unicorn Gundam (Destroy Mode) [UNIT]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD01-002-E1 - requires cost replacement hook and level modification during play
- Text: When playing this card from your hand, you may destroy 1 of your Link Units with "Unicorn Mode" in its card name that is Lv.5. If you do, play this card as if it has 0 Lv. and cost.; 【Attack】Choose 1 enemy Unit. Rest it.

### GD01-068 - Perfect Strike Gundam [UNIT]
- Themes: return_to_hand_action
- Issue: unsupported_llm_effect: GD01-068-E2 - requires return target to hand action
- Text: <Blocker> (Rest this Unit to change the attack target to it.); 【Deploy】Choose 1 enemy Unit with 1 HP. Return it to its owner's hand.

### GD01-101 - Deep Devotion [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-101-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Main】/【Action】Choose 1 friendly Link Unit. It recovers 3 HP.; 【Pilot】[Lucrezia Noin]

### GD01-103 - The Stubborn Cog [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-103-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 1 active friendly (Earth Federation) Unit and 1 active enemy Unit. Rest them.; 【Pilot】[Daguza Mackle]

### GD01-106 - Fortress Defense [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-106-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Deploy 2 [Zaku Ⅱ]((Zeon)･AP1･HP1) Unit tokens.; 【Pilot】[Dozle Zabi]

### GD01-110 - Rasid's Orders [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-110-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 Unit that is Lv.4 or higher. During this turn, it may choose an active enemy Unit with 6 or less AP as its attack target.; 【Pilot】[Rasid Kurama]

### GD01-112 - Extreme Hatred [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-112-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 2 of your active Units. Rest them. If you do, choose 1 enemy Unit. Deal 3 damage to it.; 【Pilot】[Loni Garvey]

### GD01-113 - The Desert Tiger [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-113-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly (ZAFT) Unit. It gets AP+3 during this turn.; 【Pilot】[Andrew Waldfeld]

### GD01-114 - Assault on Torrington Base [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-114-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 2 friendly Units. They get AP+1 during this turn.; 【Pilot】[Yonem Kirks]

### GD01-116 - Stealth Stratagem [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-116-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 enemy Unit with 2 or less AP. Deal 2 damage to it.; 【Pilot】[Nicol Amarfi]

### GD01-117 - The Witch and the Bride [COMMAND]
- Themes: action_vocabulary, return_to_hand_action
- Issue: unknown_action: ACTIVATE_MAIN - Action is not executed by the runtime
- Issue: unsupported_llm_effect: GD01-117-E2 - requires return target to hand action
- Issue: unsupported_llm_effect: GD01-117-E3 - requires return target to hand action
- Text: 【Burst】Activate this card's 【Main】.; 【Main】/【Action】Choose 1 enemy Unit with 5 or less HP. Return it to its owner's hand.

### GD01-119 - Iron-Fisted Discipline [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD01-119-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 enemy Unit that is Lv.4 or lower. It gets AP-2 during this turn.; 【Pilot】[Chuatury Panlunch]

### GD01-122 - Covert Operative [COMMAND]
- Themes: pilot_pairing_runtime, return_to_hand_action
- Issue: unsupported_llm_effect: GD01-122-E1 - requires return target to hand action
- Issue: unsupported_llm_effect: GD01-122-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 1 enemy Unit with 2 or less HP. Return it to its owner's hand. If you have a Link Unit in play, choose 1 enemy Unit with 4 or less HP instead.; 【Pilot】[Shaddiq Zenelli]

### GD02-098 - Quattro Bajeena [PILOT]
- Themes: unsupported_llm_runtime_mechanic
- Issue: unsupported_llm_effect: GD02-098-E1 - requires name alias modifier
- Text: This card's name is also treated as [Char Aznable].; 【Burst】Add this card to your hand.; 【When Linked】If this is an (AEUG) Unit, draw 1. If you do, discard 1.

### GD02-102 - Mouar’s Determination [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-102-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly (Titans) Unit. It gets AP+2 during this turn.; 【Pilot】[Mouar Pharaoh]

### GD02-105 - Valedictorian [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-105-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 1 of your Unit tokens. It can't receive battle damage from enemy Units during this battle.; 【Pilot】[Xavier Olivette]

### GD02-106 - White Wolf [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-106-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Action】During this battle, your shield area cards can't receive damage from enemy Units that are Lv.3 or lower.; 【Pilot】[Woolf Enneacle]

### GD02-109 - Undying Persistence [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-109-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Main】/【Action】Choose 1 enemy Unit. Deal 1 damage to it.; 【Pilot】[Shiiko Sugai]

### GD02-110 - Awakened Power [COMMAND]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD02-110-E1 - requires cost replacement hook for paying the deployed card's cost
- Text: 【Main】Choose 1 Unit card that is Lv.5 or lower from your trash. Pay its cost to deploy it.

### GD02-113 - Sisterly Care [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-113-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Main】/【Action】If a friendly (Teiwaz) Link Unit is in play, choose 1 enemy Unit with 2 or less AP. Destroy it.; 【Pilot】[Amida Arca]

### GD02-114 - It's Name is Ryusei-Go [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-114-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 damaged friendly Unit. It gets AP+2 during this turn.; 【Pilot】[Norba Shino]

### GD02-115 - Familial Devotion [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-115-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly (Vulture) Unit. It gets AP+2 during this turn.; 【Pilot】[Witz Sou]

### GD02-116 - Comrades Come First [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-116-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】If there are 7 or more cards in your trash, choose 1 friendly (Vulture) Unit. During this turn, it may choose an active enemy Unit that is Lv.4 or lower as its attack target.; 【Pilot】[Roybea Loy]

### GD02-118 - Heart Set on Revenge [COMMAND]
- Themes: action_vocabulary, pilot_pairing_runtime, return_to_hand_action
- Issue: unsupported_llm_effect: GD02-118-E1 - requires return target to hand action
- Issue: unknown_action: RETURN_TO_HAND - Action is not executed by the runtime
- Issue: unsupported_llm_effect: GD02-118-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 1 enemy Unit with 4 or less HP battling a friendly Unit with <Blocker>. Return it to its owner's hand.; 【Pilot】[Ein Dalton]

### GD02-119 - Persistent and Fortudinous [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-119-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】If you have a (Gjallarhorn) Link Unit in play, choose 1 enemy Unit. It gets AP-3 during this battle.; 【Pilot】[Carta Issue]

### GD02-120 - Aspiring Pilot [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD02-120-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 1 of your (AEUG) Units/Bases. It recovers 2 HP.; 【Pilot】[Fa Yuiry]

### GD03-058 - Farsia [UNIT]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD03-058-E1 - requires cost modification in specific zone (trash) which is not supported by current vocabulary
- Text: This card in your trash gets cost -1.

### GD03-070 - Freedom Gundam [UNIT]
- Themes: llm_parser_fallback
- Issue: unsupported_llm_effect: GD03-070-E1 - LLM parser failed: InstructorRetryException: 1 validation error for ParsedCard
- Text: While this Unit is rested, friendly Shields can't receive battle damage from enemy Units.

### GD03-077 - Justice Gundam (METEOR) [UNIT]
- Themes: action_vocabulary, return_to_hand_action
- Issue: unsupported_llm_effect: GD03-077-E1 - requires return target to hand action that preserves owner
- Issue: unknown_action: SELECTED_CARD - Action is not executed by the runtime
- Text: 【When Linked】Choose 1 to 3 enemy Units with 3 or less HP. Return them to their owners' hands.

### GD03-085 - Christina Mackenzie [PILOT]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD03-085-E2 - requires cost replacement hook
- Text: 【Burst】Add this card to your hand.; When playing this card from your hand and pairing it with a Unit with "Gundam NT-1" in its card name, play this card as if it has 0 cost.

### GD03-104 - Reccoa's Shadow [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD03-104-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 enemy Unit with 3 or less HP. Rest it. If a friendly (Jupitris) Link Unit is in play, choose 1 to 2 enemy Units with 3 or less HP instead.; 【Pilot】[Reccoa Londe]

### GD03-107 - Over the River and Through the Woods [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD03-107-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 1 enemy Unit that is Lv.5 or lower. Deal damage to it equal to the number of friendly Unit tokens in play.; 【Pilot】[Hardie Steiner]

### GD03-108 - How Many Miles to the Battlefield? [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD03-108-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Deploy 1 [Hy-Gogg]((Cyclops Team)･AP2･HP1) Unit token.; 【Pilot】[Gabriel Ramirez Garcia]

### GD03-111 - Infiltrator Present [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD03-111-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly (Mafty) Unit. It gets AP+3 during this turn.; 【Pilot】[Emeralda Zubin]

### GD03-115 - Distant Reunion [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD03-115-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 1 friendly Unit paired with an (X-Rounder) Pilot. It can't receive battle damage from enemy Units with 2 or less AP during this battle. If you are Lv.7 or higher, it can't receive battle damage from enemy Units with 5 or less AP instead.; 【Pi...

### GD03-120 - Immortal Colasour [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD03-120-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】During this turn, if a friendly (Superpower Bloc)/(UN) Unit destroys an enemy Unit with battle damage, choose 1 rested friendly (Superpower Bloc)/(UN) Unit. Set it as active. It can't attack during this turn.; 【Pilot】[Patrick Colasour]

### GD03-121 - Unheralded Attack [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD03-121-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Action】Choose 1 friendly Base and 1 enemy Unit with 3 or less HP. Rest them.; 【Pilot】[Katz Kobayashi]

### GD03-122 - Veteran Tactics [COMMAND]
- Themes: pilot_pairing_runtime, return_to_hand_action
- Issue: unsupported_llm_effect: GD03-122-E1 - requires return target to hand action
- Issue: unsupported_llm_effect: GD03-122-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 1 enemy Unit that is Lv.3 or lower. Return it to its owner's hand.; 【Pilot】[Sergei Smirnov]

### GD03-124 - Ribo Colony [BASE]
- Themes: unsupported_llm_runtime_mechanic
- Issue: unsupported_llm_effect: GD03-124-E1 - Cannot represent burst deployment effect with current vocabulary
- Text: 【Burst】Deploy this card.; 【Deploy】Add 1 of your Shields to your hand.; 【Once per Turn】When you pair a Pilot that is Lv.3 or lower with one of your Units, choose 1 enemy Unit with 3 or less HP. Rest it.

### GD03-125 - Peacemillion [BASE]
- Themes: empty_condition, unsupported_llm_runtime_mechanic
- Issue: unsupported_llm_effect: GD03-125-E1 - Deploy action via Burst requires base deployment hook
- Issue: unknown_condition: <empty> - Condition is not executed by the runtime
- Text: 【Burst】Deploy this card.; 【Deploy】Add 1 of your Shields to your hand.; 【Once per Turn】During your turn, when a friendly (Operation Meteor)/(G Team) Unit that is Lv.6 or higher destroys an enemy Unit with battle damage, that friendly Unit may recover 2 HP.

### GD03-130 - Downes [BASE]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD03-130-E2 - requires cost payment hook for deploying from trash
- Text: 【Burst】Deploy this card.; 【Deploy】Add 1 of your Shields to your hand. Then, if it is your turn, you may choose 1 (Vagan) Unit card that is Lv.4 or lower from your trash. Pay its cost to deploy it.

### GD04-021 - Gundam Lfrith Thorn [UNIT]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD04-021-E2 - requires EX Resource payment hook and pairing from trash
- Text: <Breach 3> (When this Unit's attack destroys an enemy Unit, deal the specified amount of damage to the first card in that opponent's shield area.); During your turn, when you play and activate a (Dawn of Fold) Command card using an EX Resource, you may pair...

### GD04-037 - Gundam Kyrios (Trans-Am) [UNIT]
- Themes: llm_parser_fallback
- Issue: unsupported_llm_effect: GD04-037-E1 - LLM parser failed: InstructorRetryException: 2 validation errors for ParsedCard
- Issue: unsupported_llm_effect: GD04-037-E2 - LLM parser failed: InstructorRetryException: 2 validation errors for ParsedCard
- Text: While you have a red (Super Soldier) Pilot in play, this Unit gains <First Strike>. (While this Unit is attacking, it deals damage before the enemy Unit.); While you have a green (Super Soldier) Pilot in play, this Unit gains <Breach 3>. (When this Unit's a...

### GD04-050 - Destiny Gundam [UNIT]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD04-050-E2 - requires cost payment hook for deploying from trash
- Text: <High-Maneuver> (This Unit can't be blocked.); 【During Pair】【Attack】You may choose 1 (Minerva Squad) Unit card from your trash. Pay its cost to deploy it.

### GD04-072 - Unicorn Gundam 02 Banshee Norn (Unicorn Mode) [UNIT]
- Themes: return_to_hand_action
- Issue: unsupported_llm_effect: GD04-072-E1 - requires return target to hand action
- Text: 【When Linked】Choose 1 enemy Unit with 3 or less HP. Return it to its owner's hand.

### GD04-075 - GN-X [UNIT]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD04-075-E1 - requires cost replacement hook
- Text: Reduce the cost of this card in your hand by an amount equal to the number of (UN)/(Superpower Bloc) Command cards in your trash.

### GD04-104 - Shrike Team's Bulwark [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-104-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 to 2 enemy Units that are Lv.2 or lower. Rest them.; 【Pilot】[Junko Jenko]

### GD04-106 - Indiscriminate Violence [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-106-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 1 friendly (Academy) Unit. During this turn, it may choose an active enemy Unit with 5 or less AP as its attack target. If you use an EX Resource to play this card, choose 1 to 2 friendly (Academy) Units instead.; 【Pilot】[Norea Du Noc]

### GD04-108 - Witches from Earth [COMMAND]
- Themes: pilot_pairing_runtime, stat_modifier_shape
- Issue: malformed_stat_modifier: {'conditions': [{'type': 'CHECK_TRAIT', 'value': 'Academy'}], 'duration': 'THIS_TURN', 'type': 'MODIFY_STAT', 'target': {'selector': 'FRIENDLY_UNIT'}, 'modification': '-2'} - Stat modifier must include stat and modification fields
- Issue: malformed_stat_modifier: {'conditions': [{'type': 'CHECK_TRAIT', 'value': 'Academy'}, {'type': 'CHECK_PLAYER_LEVEL', 'operator': '>=', 'value': 1}], 'duration': 'THIS_TURN', 'optional_actions': True, 'type': 'MODIFY_STAT', 'target': {'selector': 'FRIENDLY_UNIT'}, 'modification': '-4'} - Stat modifier must include stat and modification fields
- Issue: unsupported_llm_effect: GD04-108-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly (Academy) Unit. During this turn, reduce the next damage it receives by 2. If you use an EX Resource to play this card, reduce by 4 instead.; 【Pilot】[Sophie Pulone]

### GD04-111 - Trinity [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-111-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 to 3 of your (CB) Units. They get AP+2 during this turn.; 【Pilot】[Johann Trinity]

### GD04-112 - Inspector [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-112-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Deal 1 damage to all Units that are Lv.2 or lower.; 【Pilot】[Gates Capa]

### GD04-116 - Reliable Big Brother [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-116-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】Place the top 2 cards of your deck into your trash. If you do, choose 1 enemy Unit with 4 or less AP. Deal an amount of damage equal to the number of (Minerva Squad) cards placed with this effect to that enemy Unit.; 【Pilot】[Heine Westenfluss]

### GD04-118 - World Distortion [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-118-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Main】/【Action】If 2 or more friendly (UN) Units are in play, choose 1 enemy Unit with 5 or less HP. Return it to its owner's hand.; 【Pilot】[Alejandro Corner]

### GD04-119 - Fighting Alone [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-119-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly Unit paired with a (Newtype) Pilot. It can't receive effect damage from enemy Units during this turn.; 【Pilot】[Gael Chan]

### GD04-120 - Machine Doll Squad [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: GD04-120-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Main】/【Action】Choose 1 friendly (Militia)/(Dianna Counter) Unit. It gets AP+2 during this turn.; 【Pilot】[Miashei Kune]

### GD04-129 - Willgem [BASE]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: GD04-129-E3 - requires cost payment tracking hook for friendly Unit effects
- Text: 【Burst】Deploy this card.; 【Deploy】Add 1 of your Shields to your hand. Then, deal 3 damage to this Base.; 【Once per Turn】During your turn, when you pay ① or more for a friendly Unit's effect, this Base recovers 2 HP.

### ST01-012 - Thoroughly Damaged [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST01-012-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 1 rested enemy Unit. Deal 1 damage to it.; 【Pilot】[Hayato Kobayashi]

### ST01-013 - Kai's Resolve [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST01-013-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 1 friendly Unit. It recovers 3 HP.; 【Pilot】[Kai Shiden]

### ST02-012 - Simultaneous Fire [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST02-012-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】Choose 1 of your Units. It gains <Breach 3> during this turn. (When this Unit's attack destroys an enemy Unit, deal the specified amount of damage to the first card in that opponent's shield area.); 【Pilot】[Trowa Barton]

### ST02-013 - Peaceful Timbre [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST02-013-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Action】During this battle, your shield area cards can't receive damage from enemy Units that are Lv.4 or lower.; 【Pilot】[Quatre Raberba Winner]

### ST03-012 - Indignation [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST03-012-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly Unit. It gets AP+2 during this turn.; 【Pilot】[Angelo Sauper]

### ST03-013 - Close Combat [COMMAND]
- Themes: llm_parser_fallback
- Issue: unsupported_llm_effect: ST03-013-E1 - LLM parser failed: InstructorRetryException: 1 validation error for ParsedCard
- Issue: unsupported_llm_effect: ST03-013-E2 - LLM parser failed: InstructorRetryException: 1 validation error for ParsedCard
- Text: 【Burst】Activate this card's 【Main】.; 【Main】/【Action】Choose 1 enemy Unit. Deal 2 damage to it.

### ST03-014 - The Blue Giant [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST03-014-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 1 friendly Unit. It can't receive battle damage from enemy Units with 2 or less AP during this battle.; 【Pilot】[Ramba Ral]

### ST04-013 - Hawk of Endymion [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST04-013-E2 - pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 enemy Unit with 3 or less HP. Return it to its owner's hand.; 【Pilot】[Mu La Flaga]

### ST04-014 - The Magic Bullet of Dusk [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST04-014-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 friendly Unit that is Lv.2 or lower. It gains <First Strike> during this turn. (While this Unit is attacking, it deals damage before the enemy Unit.); 【Pilot】[Miguel Ayman]

### ST06-011 - Ruthless Tactics [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST06-011-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Main】/【Action】Choose 1 to 2 friendly (Clan) Units. They get AP+2 during this turn.; 【Pilot】[Gaia (GQ)]

### ST06-013 - Fierce Unity [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST06-013-E2 - Pilot metadata/AP/HP pairing support is required
- Text: 【Action】Choose 1 to 2 friendly (Clan) Units. They can't receive battle damage from enemy Units that are Lv.2 or lower during this turn.; 【Pilot】[Ortega (GQ)]

### ST08-012 - Words for Hathaway [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST08-012-E2 - requires pilot metadata/AP/HP pairing support
- Text: 【Main】Choose 1 friendly Link Unit. It gains <Breach 1> during this turn. (When this Unit' s attack destroys an enemy Unit, deal the specified amount of damage to the first card in that opponent' s shield area.); 【Pilot】[Gawman Nobile]

### ST10-014 - Unlocking the Development Diagram [COMMAND]
- Themes: cost_payment_hooks
- Issue: unsupported_llm_effect: ST10-014-E1 - requires cost replacement hook
- Text: When playing this card from your hand, you may discard 1 (G Generation) Unit card. If you do, play this card as if it has 2Lv. and cost.; 【Main】Draw 2.

### ST10-015 - Diffuse Beam Cannon [COMMAND]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: ST10-015-E2 - Pilot metadata/AP/HP pairing behavior not supported by runtime vocabulary
- Text: 【Action】If a friendly (G Generation) Unit is in play, choose 1 enemy Unit. It gets AP-3 during this battle.; 【Pilot】Claire Heathrow ･AP+1 ･HP+0

### T-022 - Wire-Guided Arm [UNIT TOKEN]
- Themes: pilot_pairing_runtime
- Issue: unsupported_llm_effect: T-022-E1 - requires pilot pairing prevention mechanic
- Text: This Unit can't be paired with a Pilot.
