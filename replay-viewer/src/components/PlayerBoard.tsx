import { useState } from "react";
import { lookupCard } from "../cardLookup";
import { getCardHighlightRole } from "../frameHighlights";
import type { CardHighlight, HighlightRole, ReplayCard, ReplayPlayer } from "../types";
import { CardTile } from "./CardTile";
import { ResourceStrip } from "./ResourceStrip";
import { ZoneModal } from "./ZoneModal";

type BoardSide = "top" | "bottom";

function colorClass(color: string | undefined) {
  const map: Record<string, string> = {
    blue: "border-blue-400",
    red: "border-red-400",
    green: "border-emerald-400",
    yellow: "border-yellow-400",
    white: "border-slate-200",
    black: "border-zinc-400",
    neutral: "border-slate-500",
  };
  return map[(color || "neutral").toLowerCase()] ?? map.neutral;
}

function CountPile({
  title,
  count,
  subtitle,
  onClick,
  clickable = false,
}: {
  title: string;
  count: number;
  subtitle?: string;
  onClick?: () => void;
  clickable?: boolean;
}) {
  const Tag = clickable ? "button" : "div";
  return (
    <Tag
      className={[
        "mx-auto flex h-16 w-14 flex-col items-center justify-center rounded-lg border border-dashed border-slate-600 bg-slate-950/70 text-center",
        clickable ? "cursor-pointer transition hover:border-cyan-400 hover:bg-slate-900" : "",
      ].join(" ")}
      onClick={onClick}
      type={clickable ? "button" : undefined}
    >
      <div className="text-lg font-black leading-none text-slate-100">{count}</div>
      <div className="text-[9px] uppercase tracking-wide text-slate-300">{title}</div>
      {subtitle ? <div className="text-[8px] text-slate-500">{subtitle}</div> : null}
    </Tag>
  );
}

function ShieldList({ cards, reverseOrder = false }: { cards: ReplayCard[]; reverseOrder?: boolean }) {
  const displayCards = reverseOrder ? [...cards].reverse() : cards;

  return (
    <section className="min-h-0 rounded-lg border border-slate-700 bg-slate-900/75 p-1.5">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-300">Shields</h3>
        <span className="rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px] leading-none text-slate-300">
          {cards.length}
        </span>
      </div>
      {displayCards.length > 0 ? (
        <div className="space-y-0.5">
          {displayCards.map((card) => {
            const known = lookupCard(card.cardId);
            const name = known?.name ?? card.name;
            const color = known?.color ?? card.color;
            return (
              <div
                key={card.instanceId}
                className={[
                  "truncate rounded border-l-2 bg-slate-950/50 px-1.5 py-0.5 text-[10px] text-slate-100",
                  colorClass(color),
                ].join(" ")}
                title={`${card.cardId} ${name}`}
              >
                {name}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex h-12 items-center justify-center rounded-lg border border-dashed border-slate-700 text-[10px] text-slate-500">
          Empty
        </div>
      )}
    </section>
  );
}

function isDeployedBaseMarker(card: ReplayCard) {
  return (
    card.type?.toUpperCase() === "BASE" &&
    (card.currentHp !== undefined || card.maxHp !== undefined || "isExBase" in card)
  );
}

function DeployedBaseArea({
  bases,
  getHighlightRole,
}: {
  bases: ReplayCard[];
  getHighlightRole: (card: ReplayCard) => HighlightRole | undefined;
}) {
  const activeBase = bases[0] ?? null;

  return (
    <section className="min-h-0 rounded-lg border border-slate-700 bg-slate-900/75 p-1.5">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-300">
          Deployed Base Area
        </h3>
        <span className="rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px] leading-none text-slate-300">
          {activeBase ? 1 : 0}
        </span>
      </div>
      {activeBase ? (
        <CardTile card={activeBase} detailed highlightRole={getHighlightRole(activeBase)} />
      ) : (
        <div className="flex h-14 items-center justify-center rounded-lg border border-dashed border-slate-700 text-[10px] text-slate-500">
          None
        </div>
      )}
    </section>
  );
}

function Zone({
  title,
  cards = [],
  wide = false,
  detailed = false,
  getHighlightRole,
}: {
  title: string;
  cards?: ReplayCard[];
  wide?: boolean;
  detailed?: boolean;
  getHighlightRole: (card: ReplayCard) => HighlightRole | undefined;
}) {
  return (
    <section className="min-h-0 rounded-lg border border-slate-700 bg-slate-900/75 p-1.5">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="text-[9px] font-bold uppercase tracking-[0.14em] text-slate-300">{title}</h3>
        <span className="rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px] leading-none text-slate-300">
          {cards.length}
        </span>
      </div>
      {cards.length > 0 ? (
        <div
          className={
            wide
              ? `flex ${detailed ? "max-h-28" : "max-h-24"} gap-1 overflow-x-auto overflow-y-hidden pr-1`
              : "grid max-h-32 grid-cols-3 gap-1 overflow-y-auto pr-1"
          }
        >
          {cards.map((card) => (
            <div key={card.instanceId} className={wide ? `${detailed ? "w-32" : "w-24"} shrink-0` : ""}>
              <CardTile
                card={card}
                compact={!detailed}
                detailed={detailed}
                highlightRole={getHighlightRole(card)}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="flex h-12 items-center justify-center rounded-lg border border-dashed border-slate-700 text-[10px] text-slate-500">
          Empty
        </div>
      )}
    </section>
  );
}

export function PlayerBoard({
  player,
  label,
  side,
  highlights = [],
}: {
  player: ReplayPlayer;
  label: string;
  side: BoardSide;
  highlights?: CardHighlight[];
}) {
  const [modal, setModal] = useState<{ title: string; cards: ReplayCard[] } | null>(null);
  const resourceAreaCount = Math.max(0, (player.totalResources ?? 0) - (player.exResources ?? 0));
  const deployedBases = player.bases ?? player.shields.filter(isDeployedBaseMarker);
  const shieldCards = player.bases ? player.shields : player.shields.filter((card) => !isDeployedBaseMarker(card));
  const isTopPlayer = side === "top";
  const getHighlightRole = (card: ReplayCard) => getCardHighlightRole(card, highlights);

  const shieldColumn = (
    <div className="col-span-2 space-y-1.5">
      {isTopPlayer ? (
        <>
          <ShieldList cards={shieldCards} reverseOrder />
          <DeployedBaseArea bases={deployedBases} getHighlightRole={getHighlightRole} />
        </>
      ) : (
        <>
          <DeployedBaseArea bases={deployedBases} getHighlightRole={getHighlightRole} />
          <ShieldList cards={shieldCards} />
        </>
      )}
    </div>
  );

  const centerColumn = isTopPlayer ? (
    <div className="col-span-7 flex flex-col gap-1.5">
      <ResourceStrip player={player} />
      <Zone title="Hand" cards={player.hand} wide detailed getHighlightRole={getHighlightRole} />
      <Zone title="Field" cards={player.field} getHighlightRole={getHighlightRole} />
    </div>
  ) : (
    <div className="col-span-7 space-y-1.5">
      <Zone title="Field" cards={player.field} getHighlightRole={getHighlightRole} />
      <Zone title="Hand" cards={player.hand} wide detailed getHighlightRole={getHighlightRole} />
      <ResourceStrip player={player} />
    </div>
  );

  return (
    <>
      <div className="space-y-1.5 rounded-xl border border-slate-800/80 bg-slate-950/30 p-1.5">
        <div className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-900/90 px-2 py-1">
          <h2 className="text-sm font-black text-slate-50">{label}</h2>
          <div className="flex gap-1 text-[10px] text-slate-300">
            <span className="rounded-full bg-slate-800 px-2 py-0.5">
              Res {player.activeResources ?? 0}/{resourceAreaCount}
            </span>
            <span className="rounded-full bg-slate-800 px-2 py-0.5">EX {player.exResources ?? 0}</span>
          </div>
        </div>
        <div className="grid grid-cols-12 gap-1.5">
          {shieldColumn}
          {centerColumn}
          <div className="col-span-3 flex flex-col items-center gap-1.5">
            <CountPile
              title="Deck"
              count={player.deck.count}
              subtitle={`Res ${player.deck.resourceDeckCount ?? 0}`}
            />
            <CountPile
              title="Trash"
              count={player.trash.length}
              clickable
              onClick={() => setModal({ title: "Trash", cards: player.trash })}
            />
            <CountPile
              title="Exiled"
              count={player.exiled.length}
              clickable
              onClick={() => setModal({ title: "Exiled", cards: player.exiled })}
            />
          </div>
        </div>
      </div>
      {modal ? <ZoneModal title={modal.title} cards={modal.cards} onClose={() => setModal(null)} /> : null}
    </>
  );
}
