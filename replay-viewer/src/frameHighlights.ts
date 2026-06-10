import type { ReplayCard, ReplayFrame, ReplayMove } from "./types";

export type HighlightRole = "attacking" | "blocking" | "defending" | "deploying" | "pairing";

export type CardHighlight = {
  role: HighlightRole;
  instanceId?: string;
  cardId: string;
  ownerId?: number;
};

function unitRefHighlight(
  unit: ReplayMove["unit"],
  role: HighlightRole,
): CardHighlight | null {
  if (!unit?.cardId) {
    return null;
  }
  return {
    role,
    instanceId: unit.instanceId,
    cardId: unit.cardId,
    ownerId: unit.ownerId,
  };
}

function cardRefHighlight(
  card: ReplayMove["card"],
  role: HighlightRole,
  ownerId?: number,
): CardHighlight | null {
  if (!card?.cardId) {
    return null;
  }
  return {
    role,
    instanceId: card.instanceId,
    cardId: card.cardId,
    ownerId,
  };
}

function addHighlight(highlights: CardHighlight[], highlight: CardHighlight | null) {
  if (!highlight) {
    return;
  }
  const exists = highlights.some(
    (entry) =>
      entry.role === highlight.role &&
      entry.instanceId === highlight.instanceId &&
      entry.cardId === highlight.cardId &&
      entry.ownerId === highlight.ownerId,
  );
  if (!exists) {
    highlights.push(highlight);
  }
}

function deriveHighlightsFromMove(move: ReplayMove | null | undefined, frame: ReplayFrame): CardHighlight[] {
  const highlights: CardHighlight[] = [];
  if (!move?.type) {
    return highlights;
  }

  switch (move.type) {
    case "attack_player":
      addHighlight(highlights, unitRefHighlight(move.unit, "attacking"));
      break;
    case "attack_unit":
      addHighlight(highlights, unitRefHighlight(move.unit, "attacking"));
      addHighlight(highlights, unitRefHighlight(move.target, "defending"));
      break;
    case "block":
      addHighlight(highlights, unitRefHighlight(move.unit, "blocking"));
      break;
    case "play_unit":
    case "play_base":
    case "play_command":
      addHighlight(highlights, cardRefHighlight(move.card, "deploying", frame.activePlayer));
      break;
    case "play_pilot":
      addHighlight(highlights, cardRefHighlight(move.card, "deploying", frame.activePlayer));
      addHighlight(highlights, unitRefHighlight(move.target, "pairing"));
      break;
    default:
      break;
  }

  return highlights;
}

function deriveHighlightsFromSummary(summary: string, frame: ReplayFrame): CardHighlight[] {
  const highlights: CardHighlight[] = [];
  const move = frame.cause.move ?? frame.cause.action;

  if (summary.startsWith("Attack Step:")) {
    addHighlight(highlights, unitRefHighlight(move?.unit, "attacking"));
    addHighlight(highlights, unitRefHighlight(move?.target, "defending"));
  } else if (summary.startsWith("Block Step:") && summary.includes("blocks!")) {
    const blockerName = summary.replace("Block Step: ", "").replace(" blocks!", "");
    for (const player of Object.values(frame.players)) {
      const blocker = player.field.find((unit) => unit.name === blockerName);
      if (blocker) {
        addHighlight(highlights, {
          role: "blocking",
          instanceId: blocker.instanceId,
          cardId: blocker.cardId,
          ownerId: blocker.ownerId ?? player.playerId,
        });
        break;
      }
    }
  } else if (summary.startsWith("Damage Step:") && summary.includes(" vs ")) {
    addHighlight(highlights, unitRefHighlight(move?.unit, "attacking"));
    addHighlight(highlights, unitRefHighlight(move?.target, "defending"));
  }

  return highlights;
}

export function getFrameHighlights(frame: ReplayFrame): CardHighlight[] {
  const stored = frame.cause.highlights;
  if (stored && stored.length > 0) {
    return stored;
  }

  const move = frame.cause.move ?? frame.cause.action;
  const highlights = deriveHighlightsFromMove(move, frame);
  for (const highlight of deriveHighlightsFromSummary(frame.cause.summary, frame)) {
    addHighlight(highlights, highlight);
  }
  return highlights;
}

export function getCardHighlightRole(
  card: ReplayCard,
  highlights: CardHighlight[],
): HighlightRole | undefined {
  for (const highlight of highlights) {
    if (highlight.instanceId) {
      if (highlight.instanceId === card.instanceId) {
        return highlight.role;
      }
      continue;
    }
    if (highlight.cardId !== card.cardId) {
      continue;
    }
    if (
      highlight.ownerId !== undefined &&
      card.ownerId !== undefined &&
      highlight.ownerId !== card.ownerId
    ) {
      continue;
    }
    return highlight.role;
  }
  return undefined;
}
