import type { ReplayCard } from "../types";
import { CardTile } from "./CardTile";

export function ZoneModal({
  title,
  cards,
  onClose,
}: {
  title: string;
  cards: ReplayCard[];
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-3xl overflow-hidden rounded-xl border border-slate-600 bg-slate-900 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-700 px-4 py-2">
          <h3 className="text-sm font-bold text-slate-100">
            {title} ({cards.length})
          </h3>
          <button
            className="rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-200"
            type="button"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <div className="grid max-h-[calc(80vh-3rem)] grid-cols-2 gap-2 overflow-y-auto p-4 md:grid-cols-3">
          {cards.length > 0 ? (
            cards.map((card) => <CardTile key={card.instanceId} card={card} detailed />)
          ) : (
            <p className="col-span-full text-sm text-slate-400">No cards in this zone.</p>
          )}
        </div>
      </div>
    </div>
  );
}
