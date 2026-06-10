import exburstCards from "../../exburst_cards_normalized.json";
import allCards from "../../card_database/all_cards.json";

type CardRecord = {
  ID: string;
  Name: string;
  Type: string;
  Color: string;
  Level?: number;
  Cost?: number;
  Ap?: number | null;
  Hp?: number | null;
};

function normalizeColor(color: string | undefined) {
  const normalized = (color || "Neutral").trim();
  if (!normalized || normalized === "-") {
    return "Neutral";
  }
  return normalized;
}

export type CardMeta = {
  cardId: string;
  name: string;
  type: string;
  color: string;
  level?: number;
  cost?: number;
  ap?: number;
  hp?: number;
};

function toCardMeta(card: CardRecord): CardMeta {
  return {
    cardId: card.ID,
    name: card.Name,
    type: card.Type,
    color: normalizeColor(card.Color),
    level: card.Level,
    cost: card.Cost,
    ap: card.Ap ?? undefined,
    hp: card.Hp ?? undefined,
  };
}

// ExBurst is the default card source; official card_database fills gaps only.
const CARD_LOOKUP = new Map<string, CardMeta>();
const CARD_LOOKUP_BY_NAME = new Map<string, CardMeta>();
for (const card of exburstCards as CardRecord[]) {
  if (card.ID) {
    const meta = toCardMeta(card);
    CARD_LOOKUP.set(card.ID, meta);
    CARD_LOOKUP_BY_NAME.set(meta.name.toLowerCase(), meta);
  }
}
for (const card of allCards as CardRecord[]) {
  if (card.ID && !CARD_LOOKUP.has(card.ID)) {
    const meta = toCardMeta(card);
    CARD_LOOKUP.set(card.ID, meta);
    if (!CARD_LOOKUP_BY_NAME.has(meta.name.toLowerCase())) {
      CARD_LOOKUP_BY_NAME.set(meta.name.toLowerCase(), meta);
    }
  }
}

export function lookupCard(cardId: string): CardMeta | null {
  return CARD_LOOKUP.get(cardId) ?? null;
}

export function lookupCardByName(name: string): CardMeta | null {
  return CARD_LOOKUP_BY_NAME.get(name.trim().toLowerCase()) ?? null;
}

export function enrichCard(
  cardId: string,
  name: string,
  partial: Partial<CardMeta> = {},
): CardMeta {
  const known = lookupCard(cardId);
  return {
    cardId,
    name: known?.name ?? name,
    type: known?.type ?? partial.type ?? "CARD",
    color: normalizeColor(known?.color ?? partial.color),
    level: partial.level ?? known?.level,
    cost: partial.cost ?? known?.cost,
    ap: partial.ap ?? known?.ap,
    hp: partial.hp ?? known?.hp,
  };
}

export function resolveCardColor(cardId: string, fallback?: string) {
  return normalizeColor(lookupCard(cardId)?.color ?? fallback);
}
