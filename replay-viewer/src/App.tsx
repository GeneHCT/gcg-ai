import { useEffect, useMemo, useState } from "react";
import { ActionSidebar } from "./components/ActionSidebar";
import { BoardView } from "./components/BoardView";
import { TimelineSlider } from "./components/TimelineSlider";
import { UploadPanel } from "./components/UploadPanel";
import type { ReplayFile } from "./types";

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export default function App() {
  const [replay, setReplay] = useState<ReplayFile | null>(null);
  const [sourceName, setSourceName] = useState<string>("No replay loaded");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const frames = replay?.frames ?? [];
  const selectedFrame = frames[selectedIndex];

  const metadata = useMemo(() => {
    if (!replay?.metadata) {
      return "Upload a replay to begin.";
    }
    const seed = replay.metadata.seed ?? "unknown";
    const createdAt = replay.metadata.createdAt ?? "unknown";
    return `Seed ${seed} - Created ${createdAt}`;
  }, [replay]);

  function loadReplay(nextReplay: ReplayFile, nextSourceName: string) {
    setReplay(nextReplay);
    setSourceName(nextSourceName);
    setSelectedIndex(0);
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!frames.length) {
        return;
      }
      if (event.key === "ArrowLeft") {
        setSelectedIndex((current) => clamp(current - 1, 0, frames.length - 1));
      }
      if (event.key === "ArrowRight") {
        setSelectedIndex((current) => clamp(current + 1, 0, frames.length - 1));
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [frames.length]);

  return (
    <div className="h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="mx-auto grid h-full max-w-[1500px] grid-cols-[1fr_300px] gap-3 px-3 py-3">
        <div className="flex min-h-0 flex-col gap-2">
          <header className="rounded-xl border border-slate-700 bg-gradient-to-r from-slate-900 to-slate-800 p-3 shadow-xl">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyan-300">Gundam Card Game</p>
                <h1 className="text-2xl font-black tracking-tight">GCG Replay Viewer</h1>
                <p className="truncate text-xs text-slate-300">{sourceName} - {metadata}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <UploadPanel compact error={error} onError={setError} onReplayLoaded={loadReplay} />
                {selectedFrame ? (
                  <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-right">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-cyan-200">Current</p>
                    <p className="whitespace-nowrap text-sm font-black">
                      Turn {selectedFrame.turn} / {selectedFrame.phase}
                    </p>
                  </div>
                ) : null}
              </div>
            </div>
          </header>

          {selectedFrame ? (
            <BoardView frame={selectedFrame} />
          ) : (
            <section className="flex min-h-0 flex-1 items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/50 p-6 text-center">
              <div>
                <h2 className="text-xl font-black text-slate-100">Upload a replay</h2>
                <p className="mt-2 max-w-xl text-sm text-slate-400">
                  Upload a simulator .log file or replay .json, or load the included sample to inspect the board layout.
                </p>
              </div>
            </section>
          )}
        </div>

        <div className="min-h-0">
          {selectedFrame ? (
            <ActionSidebar frame={selectedFrame} />
          ) : (
            <aside className="rounded-2xl border border-slate-700 bg-slate-900/90 p-4 text-sm text-slate-400">
              The sidebar will show the exact move or effect that produced the selected frame.
            </aside>
          )}
        </div>
      </div>

      {frames.length > 0 ? (
        <TimelineSlider
          frames={frames}
          index={selectedIndex}
          onChange={(nextIndex) => setSelectedIndex(clamp(nextIndex, 0, frames.length - 1))}
        />
      ) : null}
    </div>
  );
}
