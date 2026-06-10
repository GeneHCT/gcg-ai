import { buildResourceAreaFromCounts } from "../resourceUtils";
import type { ReplayCard, ReplayPlayer } from "../types";

export function getResourceCards(player: ReplayPlayer): ReplayCard[] {
  if (player.resourceArea.length > 0) {
    return player.resourceArea;
  }
  return buildResourceAreaFromCounts(
    player.playerId,
    player.totalResources ?? 0,
    player.activeResources ?? 0,
    player.exResources ?? 0,
  );
}

export function ResourceStrip({ player }: { player: ReplayPlayer }) {
  const resources = getResourceCards(player);
  const resourceAreaCount = Math.max(0, (player.totalResources ?? 0) - (player.exResources ?? 0));

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900/75 p-1.5">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-300">Resource Area</h3>
        <span className="text-[10px] text-slate-400">
          {player.activeResources ?? 0}/{resourceAreaCount} in area
          {(player.exResources ?? 0) > 0 ? ` · EX ${player.exResources}` : ""}
        </span>
      </div>
      {resources.length > 0 || (player.exResources ?? 0) > 0 ? (
        <div className="flex flex-wrap items-end gap-1">
          {resources.map((resource) => (
            <div
              key={resource.instanceId}
              className={[
                "rounded-sm border border-amber-300/70 bg-gradient-to-br from-amber-300/50 to-amber-600/40 shadow-sm",
                resource.rested ? "h-2.5 w-5" : "h-5 w-2.5",
              ].join(" ")}
              title={resource.rested ? "Rested resource" : "Active resource"}
            />
          ))}
          {Array.from({ length: player.exResources ?? 0 }, (_, index) => (
            <div
              key={`ex-${player.playerId}-${index}`}
              className="h-5 w-2.5 rounded-sm border border-emerald-300/80 bg-gradient-to-br from-emerald-300/60 to-emerald-600/50 shadow-sm"
              title="EX resource"
            />
          ))}
        </div>
      ) : (
        <div className="flex h-6 items-center justify-center rounded border border-dashed border-slate-700 text-[10px] text-slate-500">
          Empty
        </div>
      )}
    </section>
  );
}
