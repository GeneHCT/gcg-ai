import { getFrameHighlights } from "../frameHighlights";
import type { ReplayFrame } from "../types";
import { PlayerBoard } from "./PlayerBoard";

export function BoardView({ frame }: { frame: ReplayFrame }) {
  const player = frame.players["0"];
  const opponent = frame.players["1"];
  const highlights = getFrameHighlights(frame);

  return (
    <main className="min-h-0 flex-1 space-y-2 overflow-hidden pb-16">
      {opponent ? (
        <PlayerBoard player={opponent} label="Opponent - Player 1" side="top" highlights={highlights} />
      ) : null}
      {player ? (
        <PlayerBoard player={player} label="Player - Player 0" side="bottom" highlights={highlights} />
      ) : null}
    </main>
  );
}
