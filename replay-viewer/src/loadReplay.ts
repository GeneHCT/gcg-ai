import { parseSimulationLog } from "./logParser";
import type { ReplayFile } from "./types";

function validateReplay(value: unknown): ReplayFile {
  const replay = value as ReplayFile;
  if (!replay || replay.schemaVersion !== 1 || !Array.isArray(replay.frames)) {
    throw new Error("Expected a replay file with schemaVersion 1 and a frames array.");
  }
  if (replay.frames.length === 0) {
    throw new Error("Replay contains no frames.");
  }
  return replay;
}

function looksLikeJsonReplay(text: string): boolean {
  const trimmed = text.trimStart();
  return trimmed.startsWith("{") || trimmed.startsWith("[");
}

export function loadReplayFromText(text: string, filename: string): ReplayFile {
  if (looksLikeJsonReplay(text)) {
    return validateReplay(JSON.parse(text));
  }

  if (
    filename.endsWith(".log") ||
    text.includes("GAME START") ||
    text.includes("→ Action #") ||
    text.includes("→ Move #")
  ) {
    return validateReplay(parseSimulationLog(text));
  }

  throw new Error(
    "Unsupported replay file. Upload a simulator .log file or structured replay .json file.",
  );
}
