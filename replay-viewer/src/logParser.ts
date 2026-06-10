import { enrichCard, lookupCardByName } from "./cardLookup";
import { applyResourceCounts } from "./resourceUtils";
import type { ReplayCard, ReplayFile, ReplayFrame, ReplayPlayer } from "./types";

const HAND_CARD_RE =
  /^\s+\[\d+\] (.+) \(ID: ([^,]+), Lv(\d+), Cost(\d+)\)(?:, AP(\d+)\/HP(\d+))?/;
const SHIELD_CARD_RE = /^\s+\[\d+\] (.+) \(ID: ([^)]+)\)/;
const UNIT_RE =
  /^\s+\[\d+\] (.+?)(?: \(ID: ([^)]+)\))? \((ACTIVE|RESTED), AP(\d+), HP(\d+)\/(\d+)\)(?:\s+\[([^\]]+)\])?(?:\s+Pilot: (.+?) \(ID: ([^)]+)\))?/;
const COUNT_RE = (label: string) => new RegExp(`^\\s+${label}: (\\d+)`);
const DRAW_RE = /^\s+Drew: (.+)$/;
const PLAY_PILOT_RE = /PLAY_PILOT:\s+(.+?)\s+->\s+(.+)$/;
const PAIRED_RESULT_RE = /Paired\s+(.+?)\s+with\s+(.+)$/;
const DEPLOYED_BASE_RE = /Deployed base\s+(.+)$/i;

function emptyPlayer(playerId: number): ReplayPlayer {
  return {
    playerId,
    hand: [],
    deck: { count: 0, resourceDeckCount: 10 },
    trash: [],
    shields: [],
    resourceArea: [],
    field: [],
    exiled: [],
    exResources: playerId === 1 ? 1 : 0,
    activeResources: 0,
    totalResources: playerId === 1 ? 1 : 0,
  };
}

function clonePlayers(players: Record<string, ReplayPlayer>): Record<string, ReplayPlayer> {
  return JSON.parse(JSON.stringify(players)) as Record<string, ReplayPlayer>;
}

function placeholderCards(
  count: number,
  zone: string,
  playerId: number,
  label: string,
): ReplayCard[] {
  return Array.from({ length: count }, (_, index) => ({
    instanceId: `p${playerId}:${zone}:${index}`,
    cardId: `${zone.toUpperCase()}-${index + 1}`,
    name: `${label} #${index + 1}`,
    type: "CARD",
    color: "Neutral",
  }));
}

function makeCard(
  playerId: number,
  zone: string,
  index: number,
  cardId: string,
  name: string,
  extra: Partial<ReplayCard> = {},
): ReplayCard {
  return {
    instanceId: `p${playerId}:${zone}:${index}:${cardId}`,
    cardId,
    name,
    type: extra.type ?? "CARD",
    color: extra.color ?? "Neutral",
    ...extra,
  };
}

function makeKnownCard(
  playerId: number,
  zone: string,
  index: number,
  name: string,
  extra: Partial<ReplayCard> = {},
): ReplayCard {
  const known = lookupCardByName(name);
  const enriched = enrichCard(known?.cardId ?? name, name, {
    type: extra.type,
    level: extra.level,
    cost: extra.cost,
    ap: extra.ap,
    hp: extra.hp,
  });
  return makeCard(playerId, zone, index, enriched.cardId, enriched.name, {
    ...extra,
    type: extra.type ?? enriched.type,
    color: extra.color ?? enriched.color,
    level: extra.level ?? enriched.level,
    cost: extra.cost ?? enriched.cost,
    ap: extra.ap ?? enriched.ap,
    hp: extra.hp ?? enriched.hp,
  });
}

function makeExBase(playerId: number, index: number, currentHp = 3): ReplayCard {
  return makeCard(playerId, "shield", index, "EX_BASE", "EX Base", {
    type: "BASE",
    color: "Neutral",
    ap: 0,
    hp: Math.max(currentHp, 3),
    currentHp,
    maxHp: Math.max(currentHp, 3),
  });
}

function makeBaseCard(playerId: number, index: number, name: string, currentHp?: number): ReplayCard {
  const base = makeKnownCard(playerId, "shield", index, name, { type: "BASE" });
  const hp = currentHp ?? base.hp ?? 0;
  return {
    ...base,
    type: "BASE",
    ap: base.ap ?? 0,
    hp,
    currentHp: hp,
    maxHp: base.hp ?? hp,
  };
}

function findUnitByName(player: ReplayPlayer, unitName: string): ReplayCard | undefined {
  return player.field.find((unit) => unit.name === unitName || unit.cardId === unitName);
}

function attachPilotToUnit(player: ReplayPlayer, pilotName: string, unitName: string) {
  const unit = findUnitByName(player, unitName);
  if (!unit) {
    return;
  }
  unit.attachedPilot = makeKnownCard(player.playerId, "pilot", player.field.indexOf(unit), pilotName, {
    type: "PILOT",
  });
}

function adjustHandCount(player: ReplayPlayer, count: number) {
  if (count < player.hand.length) {
    player.hand = player.hand.slice(0, count);
  } else if (count > player.hand.length) {
    player.hand = [
      ...player.hand,
      ...placeholderCards(count - player.hand.length, "hand", player.playerId, "Hand"),
    ];
  }
}

function updateResourceCounts(
  player: ReplayPlayer,
  totalResources: number,
  activeResources?: number,
  exResources?: number,
) {
  const nextExResources = exResources ?? player.exResources ?? 0;
  const previousActive = player.activeResources;
  const nextActiveResources =
    activeResources ?? previousActive ?? Math.max(0, totalResources - nextExResources);
  applyResourceCounts(player, totalResources, nextActiveResources, nextExResources);
}

function enrichByIdOrName(cardId: string | undefined, name: string, type: string) {
  if (cardId) {
    return enrichCard(cardId, name, { type });
  }
  const known = lookupCardByName(name);
  return enrichCard(known?.cardId ?? name, name, { type });
}

function parseInitialPlayerBlock(
  lines: string[],
  startIndex: number,
  playerId: number,
): { player: ReplayPlayer; nextIndex: number } {
  const player = emptyPlayer(playerId);
  let index = startIndex + 1;

  while (index < lines.length) {
    const line = lines[index];
    if (line.startsWith("Player ") && line.includes("Initial State:")) {
      break;
    }
    if (line.startsWith("Starting Player:") || line.startsWith("====")) {
      break;
    }

    const handMatch = line.match(HAND_CARD_RE);
    if (handMatch) {
      const known = enrichCard(handMatch[2], handMatch[1], {
        level: Number(handMatch[3]),
        cost: Number(handMatch[4]),
        ap: handMatch[5] ? Number(handMatch[5]) : undefined,
        hp: handMatch[6] ? Number(handMatch[6]) : undefined,
        type: handMatch[5] ? "UNIT" : undefined,
      });
      player.hand.push(
        makeCard(playerId, "hand", player.hand.length, handMatch[2], known.name, {
          level: known.level,
          cost: known.cost,
          ap: known.ap,
          hp: known.hp,
          type: known.type,
          color: known.color,
        }),
      );
      index += 1;
      continue;
    }

    const shieldMatch = line.match(SHIELD_CARD_RE);
    if (shieldMatch && !line.includes("Lv")) {
      player.shields.push(
        makeCard(playerId, "shield", player.shields.length, shieldMatch[2], shieldMatch[1]),
      );
      index += 1;
      continue;
    }

    const mainDeckMatch = line.match(/^\s+Main Deck: (\d+) cards/);
    if (mainDeckMatch) {
      player.deck.count = Number(mainDeckMatch[1]);
    }

    const resourceDeckMatch = line.match(/^\s+Resource Deck: (\d+) cards/);
    if (resourceDeckMatch) {
      player.deck.resourceDeckCount = Number(resourceDeckMatch[1]);
    }

    const exResourcesMatch = line.match(/^\s+EX Resources: (\d+)/);
    if (exResourcesMatch) {
      player.exResources = Number(exResourcesMatch[1]);
      player.totalResources = player.exResources;
    }

    const basesMatch = line.match(/^\s+Bases: (\d+) \(HP: (\d+)\)/);
    if (basesMatch && Number(basesMatch[1]) > 0) {
      player.shields.push(makeExBase(playerId, player.shields.length, Number(basesMatch[2])));
    }

    index += 1;
  }

  return { player, nextIndex: index };
}

function parseCurrentGameStateBlock(
  lines: string[],
  startIndex: number,
  players: Record<string, ReplayPlayer>,
  pairings: Record<string, Record<string, ReplayCard>>,
): number {
  let index = startIndex + 1;
  let currentPlayerId: number | null = null;

  while (index < lines.length) {
    const line = lines[index];
    if (line.startsWith("====") || line.startsWith("TURN ") || line.startsWith("GAME END")) {
      break;
    }

    const playerMatch = line.match(/^    Player (\d+):/);
    if (playerMatch) {
      currentPlayerId = Number(playerMatch[1]);
      index += 1;
      continue;
    }

    if (currentPlayerId === null) {
      index += 1;
      continue;
    }

    const playerKey = String(currentPlayerId);
    const parsedPlayerId = currentPlayerId;
    const player = players[playerKey] ?? emptyPlayer(currentPlayerId);

    const handMatch = line.match(COUNT_RE("Hand"));
    if (handMatch) {
      adjustHandCount(player, Number(handMatch[1]));
    }

    const deckMatch = line.match(COUNT_RE("Deck"));
    if (deckMatch) {
      player.deck = { ...player.deck, count: Number(deckMatch[1]) };
    }

    const resourcesDetailMatch = line.match(
      /^\s+Resources: (\d+)(?: \(Active: (\d+), EX: (\d+)\))?/,
    );
    if (resourcesDetailMatch) {
      const totalResources = Number(resourcesDetailMatch[1]);
      updateResourceCounts(
        player,
        totalResources,
        resourcesDetailMatch[2] ? Number(resourcesDetailMatch[2]) : undefined,
        resourcesDetailMatch[3] ? Number(resourcesDetailMatch[3]) : undefined,
      );
    }

    const trashMatch = line.match(COUNT_RE("Trash"));
    if (trashMatch) {
      const count = Number(trashMatch[1]);
      player.trash =
        player.trash.length === count
          ? player.trash
          : placeholderCards(count, "trash", currentPlayerId, "Trash");
    }

    const battleCountMatch = line.match(/^\s+Battle Area: (\d+) units/);
    if (battleCountMatch) {
      player.field = [];
    }

    const shieldsMatch = line.match(/^\s+Shields: (\d+) \+ (\d+) bases/);
    if (shieldsMatch) {
      const shieldCount = Number(shieldsMatch[1]);
      const baseCount = Number(shieldsMatch[2]);
      const existingShields = player.shields.filter((card) => card.type !== "BASE");
      const existingBases = player.shields.filter((card) => card.type === "BASE");
      player.shields = [
        ...(existingShields.length === shieldCount
          ? existingShields
          : placeholderCards(shieldCount, "shield", parsedPlayerId, "Shield")),
        ...(existingBases.length === baseCount
          ? existingBases
          : Array.from({ length: baseCount }, (_, baseIndex) =>
              makeExBase(parsedPlayerId, shieldCount + baseIndex),
            )),
      ];
    } else {
      const shieldsOnlyMatch = line.match(/^\s+Shields: (\d+)$/);
      if (shieldsOnlyMatch) {
        const count = Number(shieldsOnlyMatch[1]);
        player.shields = placeholderCards(count, "shield", parsedPlayerId, "Shield");
      }
    }

    const unitMatch = line.match(UNIT_RE);
    if (unitMatch) {
      const unitName = unitMatch[1];
      const enrichedUnit = enrichByIdOrName(unitMatch[2], unitName, "UNIT");
      const loggedPilot = unitMatch[8] && unitMatch[9]
        ? makeCard(
            parsedPlayerId,
            "pilot",
            player.field.length,
            unitMatch[9],
            enrichCard(unitMatch[9], unitMatch[8], { type: "PILOT" }).name,
            {
              ...enrichCard(unitMatch[9], unitMatch[8], { type: "PILOT" }),
              type: "PILOT",
            },
          )
        : undefined;
      if (loggedPilot) {
        pairings[String(parsedPlayerId)][unitName] = loggedPilot;
      }
      const pairing = loggedPilot ?? pairings[String(parsedPlayerId)]?.[unitName];
      player.field.push(
        makeCard(parsedPlayerId, "field", player.field.length, enrichedUnit.cardId, enrichedUnit.name, {
          type: "UNIT",
          color: enrichedUnit.color,
          level: enrichedUnit.level,
          cost: enrichedUnit.cost,
          ap: Number(unitMatch[4]),
          hp: Number(unitMatch[6]),
          currentHp: Number(unitMatch[5]),
          maxHp: Number(unitMatch[6]),
          rested: unitMatch[3] === "RESTED",
          keywords: unitMatch[7] ? { [unitMatch[7]]: true } : undefined,
          attachedPilot: pairing ?? undefined,
        }),
      );
    }

    players[playerKey] = player;
    index += 1;
  }

  return index;
}

function phaseSlug(phaseLabel: string): string {
  return phaseLabel.toLowerCase().replace(/\s+phase$/, "").replace(/\s+/g, "_");
}

function pushFrame(
  frames: ReplayFrame[],
  players: Record<string, ReplayPlayer>,
  frame: Omit<ReplayFrame, "id" | "players">,
) {
  frames.push({
    ...frame,
    id: frames.length,
    players: clonePlayers(players),
  });
}

export function parseSimulationLog(text: string): ReplayFile {
  const lines = text.split(/\r?\n/);
  const metadata: Record<string, unknown> = { source: "simulation_log" };
  const players: Record<string, ReplayPlayer> = {
    "0": emptyPlayer(0),
    "1": emptyPlayer(1),
  };

  let turn = 1;
  let phase = "start";
  let activePlayer = 0;
  const frames: ReplayFrame[] = [];
  let initialStateCaptured = false;
  const pairings: Record<string, Record<string, ReplayCard>> = { "0": {}, "1": {} };
  let pendingPilotPair: { playerId: number; pilotName: string; unitName: string } | null = null;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];

    if (line.startsWith("Timestamp:")) {
      metadata.createdAt = line.slice("Timestamp:".length).trim();
    }
    if (line.startsWith("Seed:")) {
      metadata.seed = Number(line.slice("Seed:".length).trim());
    }

    const initialPlayerMatch = line.match(/^Player (\d+) Initial State:/);
    if (initialPlayerMatch) {
      const playerId = Number(initialPlayerMatch[1]);
      const parsed = parseInitialPlayerBlock(lines, index, playerId);
      players[String(playerId)] = parsed.player;
      index = parsed.nextIndex - 1;
      continue;
    }

    if (!initialStateCaptured && line.startsWith("Starting Player:")) {
      activePlayer = Number(line.match(/Player (\d+)/)?.[1] ?? 0);
      pushFrame(frames, players, {
        turn: 1,
        phase: "start",
        activePlayer,
        decisionPlayer: null,
        label: "Game start",
        cause: { type: "game_start", summary: "Initial setup from simulation log" },
      });
      initialStateCaptured = true;
      continue;
    }

    const turnMatch = line.match(/^TURN (\d+) - Player (\d+)'s Turn/);
    if (turnMatch) {
      turn = Number(turnMatch[1]);
      activePlayer = Number(turnMatch[2]);
      continue;
    }

    const activePlayerMatch = line.match(/^Active Player: Player (\d+)/);
    if (activePlayerMatch) {
      activePlayer = Number(activePlayerMatch[1]);
      continue;
    }

    const resourcesDetailMatch = line.match(
      /^\s+Resources: (\d+)(?: \(Active: (\d+), EX: (\d+)\))?/,
    );
    if (resourcesDetailMatch) {
      const player = players[String(activePlayer)];
      updateResourceCounts(
        player,
        Number(resourcesDetailMatch[1]),
        resourcesDetailMatch[2] ? Number(resourcesDetailMatch[2]) : undefined,
        resourcesDetailMatch[3] ? Number(resourcesDetailMatch[3]) : undefined,
      );
      continue;
    }

    const activeHandMatch = line.match(/^\s+Hand: (\d+) cards/);
    if (activeHandMatch) {
      adjustHandCount(players[String(activePlayer)], Number(activeHandMatch[1]));
      continue;
    }

    const activeBaseMatch = line.match(/^\s+Bases: (\d+) active \(Total HP: (\d+)\)/);
    if (activeBaseMatch) {
      const player = players[String(activePlayer)];
      const baseCount = Number(activeBaseMatch[1]);
      const totalHp = Number(activeBaseMatch[2]);
      const shields = player.shields.filter((card) => card.type !== "BASE");
      const bases = player.shields.filter((card) => card.type === "BASE");
      player.shields = [
        ...shields,
        ...(bases.length === baseCount
          ? bases.map((base, baseIndex) => ({
              ...base,
              currentHp: Math.max(0, Math.floor(totalHp / Math.max(baseCount, 1))),
              maxHp: base.maxHp ?? base.hp ?? Math.max(0, totalHp),
              instanceId: base.instanceId || `p${activePlayer}:shield:base:${baseIndex}`,
            }))
          : Array.from({ length: baseCount }, (_, baseIndex) =>
              makeExBase(activePlayer, shields.length + baseIndex, Math.max(0, totalHp)),
            )),
      ];
      continue;
    }

    const drawMatch = line.match(DRAW_RE);
    if (drawMatch) {
      const player = players[String(activePlayer)];
      const drawnCard = makeKnownCard(activePlayer, "hand", player.hand.length, drawMatch[1]);
      player.hand.push(drawnCard);
      pushFrame(frames, players, {
        turn,
        phase,
        activePlayer,
        decisionPlayer: null,
        label: `Turn ${turn} - Draw`,
        cause: {
          type: "draw",
          summary: `Player ${activePlayer} drew ${drawnCard.name}`,
          effects: [{ drawnCard }],
        },
      });
      continue;
    }

    const phaseMatch = line.match(/^>>> PHASE: ([A-Z ]+) PHASE/);
    if (phaseMatch) {
      phase = phaseSlug(phaseMatch[1]);
      pushFrame(frames, players, {
        turn,
        phase,
        activePlayer,
        decisionPlayer: null,
        label: `Turn ${turn} - ${phaseMatch[1]} Phase`,
        cause: {
          type: "phase",
          summary: `Entered ${phaseMatch[1].toLowerCase()} phase`,
        },
      });
      continue;
    }

    const moveMatch = line.match(/^→ (?:Action|Move) #(\d+): (.+)/);
    if (moveMatch) {
      let result: string | null = null;
      const nextLine = lines[index + 1] ?? "";
      if (nextLine.startsWith("    Result: ")) {
        result = nextLine.slice("    Result: ".length).trim();
        index += 1;
      }

      const playPilotMatch = moveMatch[2].match(PLAY_PILOT_RE);
      if (playPilotMatch) {
        pendingPilotPair = {
          playerId: activePlayer,
          pilotName: playPilotMatch[1],
          unitName: playPilotMatch[2],
        };
      }

      const pairedMatch = result?.match(PAIRED_RESULT_RE);
      if (pairedMatch || (result?.startsWith("Paired ") && pendingPilotPair)) {
        const playerId = pendingPilotPair?.playerId ?? activePlayer;
        const pilotName = pairedMatch?.[1] ?? pendingPilotPair?.pilotName ?? "";
        const unitName = pairedMatch?.[2] ?? pendingPilotPair?.unitName ?? "";
        const pilot = makeKnownCard(playerId, "pilot", 0, pilotName, { type: "PILOT" });
        pairings[String(playerId)][unitName] = pilot;
        attachPilotToUnit(players[String(playerId)], pilotName, unitName);
        pendingPilotPair = null;
      }

      const deployedBaseMatch = result?.match(DEPLOYED_BASE_RE);
      if (deployedBaseMatch) {
        const player = players[String(activePlayer)];
        const shields = player.shields.filter((card) => card.type !== "BASE");
        player.shields = [...shields, makeBaseCard(activePlayer, shields.length, deployedBaseMatch[1])];
      }

      pushFrame(frames, players, {
        turn,
        phase,
        activePlayer,
        decisionPlayer: activePlayer,
        label: `Move #${moveMatch[1]}`,
        cause: {
          type: "move",
          summary: moveMatch[2],
          move: { summary: moveMatch[2] },
          action: { summary: moveMatch[2] },
          result,
        },
      });
      continue;
    }

    if (line === "Current Game State:") {
      parseCurrentGameStateBlock(lines, index, players, pairings);
      pushFrame(frames, players, {
        turn,
        phase,
        activePlayer,
        decisionPlayer: null,
        label: `Turn ${turn} snapshot`,
        cause: {
          type: "state_summary",
          summary: "Current game state summary from simulation log",
        },
      });
      continue;
    }

    if (line.trim() === "GAME END") {
      parseCurrentGameStateBlock(lines, index, players, pairings);
      pushFrame(frames, players, {
        turn,
        phase: "end",
        activePlayer,
        decisionPlayer: null,
        label: "Game end",
        cause: {
          type: "game_end",
          summary: lines[index + 2]?.startsWith("Result:")
            ? lines[index + 2].slice("Result:".length).trim()
            : "Game ended",
        },
      });
      break;
    }
  }

  if (frames.length === 0) {
    throw new Error("No replay frames could be parsed from this simulation log.");
  }

  return {
    schemaVersion: 1,
    metadata,
    frames,
  };
}
