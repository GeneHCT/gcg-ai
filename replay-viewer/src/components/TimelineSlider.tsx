import type { ReplayFrame } from "../types";

type TimelineSliderProps = {
  frames: ReplayFrame[];
  index: number;
  onChange: (index: number) => void;
};

export function TimelineSlider({ frames, index, onChange }: TimelineSliderProps) {
  const frame = frames[index];
  const max = Math.max(frames.length - 1, 0);

  return (
    <footer className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-700 bg-slate-950/95 px-3 py-2 shadow-2xl backdrop-blur">
      <div className="mx-auto max-w-[1500px]">
        <div className="mb-1.5 flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-300">Timeline Slider</p>
            <p className="text-xs text-slate-300">
              Frame {index + 1} / {frames.length} - Turn {frame?.turn ?? 0}, {frame?.phase ?? "unknown"} - {frame?.label ?? ""}
            </p>
          </div>
          <div className="flex gap-1.5">
            <button
              className="rounded-md border border-slate-600 px-2 py-1 text-xs font-semibold text-slate-200 disabled:opacity-40"
              type="button"
              disabled={index === 0}
              onClick={() => onChange(Math.max(0, index - 1))}
            >
              Previous
            </button>
            <button
              className="rounded-md border border-slate-600 px-2 py-1 text-xs font-semibold text-slate-200 disabled:opacity-40"
              type="button"
              disabled={index === max}
              onClick={() => onChange(Math.min(max, index + 1))}
            >
              Next
            </button>
          </div>
        </div>
        <input
          className="h-1.5 w-full cursor-pointer accent-cyan-400"
          type="range"
          min={0}
          max={max}
          value={index}
          onChange={(event) => onChange(Number(event.target.value))}
        />
      </div>
    </footer>
  );
}
