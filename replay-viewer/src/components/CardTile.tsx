import { lookupCard } from "../cardLookup";
import type { HighlightRole, ReplayCard } from "../types";

const HIGHLIGHT_CLASSES: Record<HighlightRole, string> = {
  attacking: "ring-2 ring-orange-400 shadow-[0_0_10px_rgba(251,146,60,0.55)]",
  blocking: "ring-2 ring-violet-400 shadow-[0_0_10px_rgba(167,139,250,0.55)]",
  defending: "ring-2 ring-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.55)]",
  deploying: "ring-2 ring-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.55)]",
  pairing: "ring-2 ring-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.55)]",
};

const HIGHLIGHT_LABELS: Record<HighlightRole, string> = {
  attacking: "Attacking",
  blocking: "Blocking",
  defending: "Defending",
  deploying: "Deployed",
  pairing: "Pairing",
};

const COLOR_CLASSES: Record<string, string> = {
  blue: "border-blue-300 bg-blue-500/25 text-blue-50",
  red: "border-red-300 bg-red-500/25 text-red-50",
  green: "border-emerald-300 bg-emerald-500/25 text-emerald-50",
  yellow: "border-yellow-300 bg-yellow-500/25 text-yellow-50",
  white: "border-slate-200 bg-slate-100/20 text-slate-50",
  black: "border-zinc-400 bg-zinc-700/60 text-zinc-50",
  neutral: "border-slate-500 bg-slate-700/60 text-slate-50",
};

function colorClass(color: string | undefined) {
  const normalized = (color || "neutral").trim().toLowerCase();
  return COLOR_CLASSES[normalized === "-" ? "neutral" : normalized] ?? COLOR_CLASSES.neutral;
}

function displayType(type: string | undefined) {
  const normalized = (type || "").toUpperCase();
  if (!normalized || normalized === "CARD") {
    return null;
  }
  return normalized;
}

export function CardTile({
  card,
  compact = false,
  detailed = false,
  highlightRole,
}: {
  card: ReplayCard;
  compact?: boolean;
  detailed?: boolean;
  highlightRole?: HighlightRole;
}) {
  const known = lookupCard(card.cardId);
  const resolvedCard: ReplayCard = {
    ...card,
    name: known?.name ?? card.name,
    type: known?.type ?? card.type,
    color: known?.color ?? card.color,
    level: card.level ?? known?.level,
    cost: card.cost ?? known?.cost,
    ap: card.ap ?? known?.ap,
    hp: card.hp ?? known?.hp,
  };

  const isUnit = resolvedCard.type?.toUpperCase() === "UNIT";
  const isBase = resolvedCard.type?.toUpperCase() === "BASE";
  const hp = resolvedCard.currentHp ?? resolvedCard.hp;
  const maxHp = resolvedCard.maxHp ?? resolvedCard.hp;
  const typeLabel = displayType(resolvedCard.type);
  const showCombatStats = isUnit || isBase || resolvedCard.ap !== undefined || hp !== undefined;
  const showLevelCost = resolvedCard.level !== undefined || resolvedCard.cost !== undefined;
  const levelCost =
    showLevelCost ? `Lv${resolvedCard.level ?? 0}/C${resolvedCard.cost ?? 0}` : null;
  const attachedPilot = resolvedCard.attachedPilot;
  const attachedPilotName = attachedPilot
    ? (lookupCard(attachedPilot.cardId)?.name ?? attachedPilot.name)
    : null;

  return (
    <article
      className={[
        "rounded-md border p-1.5 shadow-sm",
        colorClass(resolvedCard.color),
        highlightRole ? HIGHLIGHT_CLASSES[highlightRole] : "",
        resolvedCard.rested ? "rotate-2 opacity-70" : "",
        detailed ? "min-h-[4rem]" : compact ? "min-h-12" : "min-h-16",
      ].join(" ")}
      title={`${resolvedCard.cardId} ${resolvedCard.name}${highlightRole ? ` (${HIGHLIGHT_LABELS[highlightRole]})` : ""}`}
    >
      <div className="flex items-start justify-between gap-1 text-[8px] font-semibold uppercase tracking-wide opacity-80">
        <span className="truncate">
          {resolvedCard.cardId}
          {levelCost ? <span className="ml-1 normal-case opacity-90">{levelCost}</span> : null}
        </span>
        <span className="shrink-0">
          {highlightRole ? <span className="text-cyan-200">{HIGHLIGHT_LABELS[highlightRole]}</span> : null}
          {highlightRole && resolvedCard.rested ? <span className="mx-1">·</span> : null}
          {resolvedCard.rested ? <span>Rested</span> : null}
        </span>
      </div>
      <h4 className="mt-0.5 line-clamp-2 text-[10px] font-bold leading-tight">{resolvedCard.name}</h4>
      <div className="mt-1 flex flex-wrap gap-1 text-[8px]">
        {showCombatStats ? (
          <span className="rounded bg-black/25 px-1 py-0.5">
            AP {resolvedCard.ap ?? 0} / HP {hp ?? 0}
            {maxHp !== undefined ? `/${maxHp}` : ""}
          </span>
        ) : null}
        {typeLabel ? <span className="rounded bg-black/25 px-1 py-0.5">{typeLabel}</span> : null}
      </div>
      {attachedPilotName ? (
        <div className="mt-1 truncate rounded bg-black/30 px-1 py-0.5 text-[8px]">
          Pilot: <span className="font-semibold">{attachedPilotName}</span>
        </div>
      ) : null}
    </article>
  );
}
