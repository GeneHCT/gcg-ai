import { lookupCard } from "../cardLookup";
import type { ReplayCard, ReplayFrame } from "../types";
import { CardTile } from "./CardTile";

function Detail({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-lg bg-slate-950/60 p-2">
      <dt className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-xs text-slate-100">{value === null || value === undefined || value === "" ? "None" : String(value)}</dd>
    </div>
  );
}

function commandCardFromFrame(frame: ReplayFrame): ReplayCard | null {
  const move = frame.cause.move ?? frame.cause.action;
  if (move?.type !== "play_command" || !move.card?.cardId) {
    return null;
  }

  const known = lookupCard(move.card.cardId);
  return {
    instanceId: `command:${move.card.cardId}`,
    cardId: move.card.cardId,
    name: known?.name ?? move.card.name ?? move.card.cardId,
    type: known?.type ?? move.card.type ?? "COMMAND",
    color: known?.color ?? move.card.color ?? "Neutral",
    level: move.card.level ?? known?.level,
    cost: move.card.cost ?? known?.cost,
    ap: move.card.ap ?? known?.ap,
    hp: move.card.hp ?? known?.hp,
  };
}

export function ActionSidebar({ frame }: { frame: ReplayFrame }) {
  const move = frame.cause.move ?? frame.cause.action;
  const commandCard = commandCardFromFrame(frame);

  return (
    <aside className="h-[calc(100vh-5.5rem)] overflow-y-auto rounded-xl border border-slate-700 bg-slate-900/90 p-2 shadow-xl">
      <div className="mb-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-300">Move / Effect</p>
        <h2 className="mt-1 text-base font-black text-slate-50">{frame.label}</h2>
        <p className="mt-1 text-xs leading-5 text-slate-300">{frame.cause.summary}</p>
      </div>

      {commandCard ? (
        <section className="mb-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-2">
          <h3 className="text-[9px] font-bold uppercase tracking-[0.14em] text-cyan-200">Command Played</h3>
          <div className="mt-2">
            <CardTile card={commandCard} detailed highlightRole="deploying" />
          </div>
        </section>
      ) : null}

      <dl className="space-y-1.5">
        <Detail label="Turn" value={frame.turn} />
        <Detail label="Phase" value={frame.phase} />
        <Detail label="Active Player" value={`Player ${frame.activePlayer}`} />
        <Detail label="Decision Player" value={frame.decisionPlayer !== null && frame.decisionPlayer !== undefined ? `Player ${frame.decisionPlayer}` : "None"} />
        <Detail label="Cause Type" value={frame.cause.type} />
        <Detail label="Move Type" value={move?.type} />
        <Detail label="Move Summary" value={move?.summary} />
        <Detail label="Result" value={frame.cause.result} />
        <Detail label="Card" value={move?.card?.name} />
        <Detail label="Unit" value={move?.unit?.name} />
        <Detail label="Target" value={move?.target?.name} />
      </dl>

      {frame.cause.effects && frame.cause.effects.length > 0 ? (
        <section className="mt-2 rounded-lg bg-slate-950/60 p-2">
          <h3 className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-500">Effects</h3>
          <pre className="mt-1 whitespace-pre-wrap text-[10px] text-slate-300">
            {JSON.stringify(frame.cause.effects, null, 2)}
          </pre>
        </section>
      ) : null}
    </aside>
  );
}
