// Pure, DOM-free UI logic. No `document`, no `fetch`, no `state` import - so it
// is unit-testable under Node (`node --test ui`) without a browser or jsdom.

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

// Group stage rows by their stage number and reindex to a contiguous 0..n-1
// sequence so exported plans satisfy the Python contiguity invariant even when
// the UI stage numbers have gaps (e.g. 0, 2, 5 -> 0, 1, 2).
export function stageBuckets(rows) {
  const uniqueStages = [...new Set(rows.map((row) => row.stage))].sort((a, b) => a - b);
  return uniqueStages.map((stage, index) => ({
    index,
    rows: rows.filter((row) => row.stage === stage),
  }));
}

// Cumulative translation per tooth from an engine frame (never recomputed here).
export function framePoseTotals(frame) {
  const totals = new Map();
  if (!frame || !Array.isArray(frame.poses)) return totals;
  for (const pose of frame.poses) {
    totals.set(pose.tooth, {
      x: pose.translate_x_mm,
      y: pose.translate_y_mm,
      z: pose.translate_z_mm,
    });
  }
  return totals;
}

// Monotonic token so a slow async result can be discarded if a newer one started.
export function createLatest() {
  let token = 0;
  return {
    next: () => (token += 1),
    isCurrent: (value) => value === token,
  };
}
