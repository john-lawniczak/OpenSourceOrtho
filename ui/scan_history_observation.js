import { loadWeekEighteenScan, suggestedPaintingCapture } from "./scan_week_eighteen.js";
import { loadWeekTwentyOneScan } from "./scan_week_twenty_one.js";

// History explicitly selects these captures; editor/source defaults stay source-bound.
export async function loadHistoryObservation(arch, { signal, week = 18 } = {}) {
  if (week === 21) return loadWeekTwentyOneScan(arch, { signal });
  if (week !== 18) throw new Error("Choose a recorded observation.");
  const scan = await loadWeekEighteenScan(arch, { signal, capture: suggestedPaintingCapture(arch, "progress-02") });
  scan.historyDisplay = true;
  scan.reportedWeek = 18;
  scan.surfaceDescription = arch === "upper" ? "cleaned upper" : "original H4 lower";
  if (arch !== "lower") return scan;
  const response = await fetch("/api/sample-history/lower-cleaned", { signal });
  // Public/static installations do not contain the contributor's private trim.
  if (response.status === 404) return scan;
  if (!response.ok) throw new Error("Saved week 18 lower cleanup could not be loaded.");
  const record = await response.json();
  if (record.available === false) return scan;
  if (record.source_sha256 !== scan.sha256 || typeof record.stl_base64 !== "string") throw new Error("Week 18 cleanup belongs to another source.");
  const bytes = Uint8Array.from(atob(record.stl_base64), c => c.charCodeAt(0)).buffer;
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hash = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
  if (hash !== record.sha256) throw new Error("Week 18 cleanup integrity check failed.");
  return { ...scan, bytes, sha256: hash, filename: record.filename, sourceSha256: scan.sha256,
    capture: "fusion-h-4-cleaned", surfaceDescription: "cleaned H4 lower" };
}
