import type { ReplayCard, ReplayPlayer } from "./types";

export function buildResourceAreaFromCounts(
  playerId: number,
  totalResources: number,
  activeResources: number,
  exResources: number,
): ReplayCard[] {
  const areaCount = Math.max(0, totalResources - exResources);
  const activeCount = Math.min(activeResources, areaCount);

  return Array.from({ length: areaCount }, (_, index) => ({
    instanceId: `p${playerId}:resource:${index}`,
    cardId: "RESOURCE",
    name: "Resource",
    type: "RESOURCE",
    color: "Yellow",
    rested: index >= activeCount,
  }));
}

export function applyResourceCounts(
  player: ReplayPlayer,
  totalResources: number,
  activeResources: number,
  exResources: number,
) {
  player.totalResources = totalResources;
  player.activeResources = activeResources;
  player.exResources = exResources;
  player.resourceArea = buildResourceAreaFromCounts(
    player.playerId,
    totalResources,
    activeResources,
    exResources,
  );
}
