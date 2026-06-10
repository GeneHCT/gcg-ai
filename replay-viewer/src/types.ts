export type ReplayCard = {
  instanceId: string;
  cardId: string;
  name: string;
  type: string;
  color: string;
  level?: number;
  cost?: number;
  ap?: number;
  hp?: number;
  currentHp?: number;
  maxHp?: number;
  rested?: boolean;
  ownerId?: number;
  keywords?: Record<string, unknown>;
  attachedPilot?: ReplayCard | null;
};

export type DeckZone = {
  count: number;
  resourceDeckCount?: number;
};

export type ReplayPlayer = {
  playerId: number;
  hand: ReplayCard[];
  deck: DeckZone;
  trash: ReplayCard[];
  shields: ReplayCard[];
  bases?: ReplayCard[];
  resourceArea: ReplayCard[];
  field: ReplayCard[];
  exiled: ReplayCard[];
  exResources?: number;
  activeResources?: number;
  totalResources?: number;
};

export type HighlightRole = "attacking" | "blocking" | "defending" | "deploying" | "pairing";

export type CardHighlight = {
  role: HighlightRole;
  instanceId?: string;
  cardId: string;
  ownerId?: number;
};

export type ReplayMove = {
  type?: string;
  summary?: string;
  card?: Partial<ReplayCard> | null;
  unit?: Partial<ReplayCard> | null;
  target?: Partial<ReplayCard> | null;
  ability?: {
    effectId?: string;
    effectType?: string;
  } | null;
};

export type ReplayCause = {
  type: string;
  summary: string;
  move?: ReplayMove | null;
  action?: ReplayMove | null;
  result?: string | null;
  effects?: Array<Record<string, unknown>>;
  highlights?: CardHighlight[];
};

export type ReplayFrame = {
  id: number;
  turn: number;
  phase: string;
  activePlayer: number;
  decisionPlayer?: number | null;
  label: string;
  cause: ReplayCause;
  players: Record<string, ReplayPlayer>;
};

export type ReplayFile = {
  schemaVersion: number;
  metadata?: Record<string, unknown>;
  frames: ReplayFrame[];
};
