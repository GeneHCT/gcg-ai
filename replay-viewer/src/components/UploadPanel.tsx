import { loadReplayFromText } from "../loadReplay";
import type { ReplayFile } from "../types";

type UploadPanelProps = {
  error: string | null;
  onReplayLoaded: (replay: ReplayFile, sourceName: string) => void;
  onError: (message: string | null) => void;
  compact?: boolean;
};

export function UploadPanel({ error, onReplayLoaded, onError, compact = false }: UploadPanelProps) {
  async function handleFile(file: File) {
    try {
      const parsed = loadReplayFromText(await file.text(), file.name);
      onReplayLoaded(parsed, file.name);
      onError(null);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to load replay file.");
    }
  }

  async function loadSample() {
    try {
      const response = await fetch("/sample-replay.json");
      if (!response.ok) {
        throw new Error("Sample replay could not be loaded.");
      }
      onReplayLoaded(loadReplayFromText(await response.text(), "sample-replay.json"), "sample-replay.json");
      onError(null);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to load sample replay.");
    }
  }

  const controls = (
    <>
      <label className="cursor-pointer shrink-0 rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400">
        Upload replay
        <input
          className="hidden"
          type="file"
          accept="application/json,.json,.log,text/plain"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              void handleFile(file);
            }
          }}
        />
      </label>
      <button
        className="shrink-0 rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-400 hover:text-cyan-200"
        type="button"
        onClick={() => void loadSample()}
      >
        Load sample
      </button>
    </>
  );

  if (compact) {
    return (
      <div className="flex shrink-0 items-center gap-2">
        {controls}
        {error ? <p className="max-w-xs truncate text-xs text-red-300">{error}</p> : null}
      </div>
    );
  }

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900/80 p-2 shadow-xl">
      <div className="flex flex-wrap items-center gap-2">
        {controls}
        <p className="text-xs text-slate-400">
          Upload a simulator .log or structured replay .json, then scrub with the slider or arrow keys.
        </p>
      </div>
      {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}
    </section>
  );
}
