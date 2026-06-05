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

export function degToRad(deg) {
  return (deg * Math.PI) / 180;
}

// Classify an FDI tooth into a crown class by its last digit. Shared by the 3D
// proxy geometry and the demo mesh URL mapping so both agree on tooth type.
export function toothKind(tooth) {
  const digit = String(tooth).slice(-1);
  if (digit === "1" || digit === "2") return "incisor";
  if (digit === "3") return "canine";
  if (digit === "4" || digit === "5") return "premolar";
  return "molar";
}

// Displacement vector for a pose, scaled by an honesty-flagged exaggeration so
// sub-mm movement is visible next to ~10 mm teeth. The caller labels the factor.
export function displacement(pose, exaggeration = 1) {
  return {
    x: (pose.translate_x_mm || 0) * exaggeration,
    y: (pose.translate_y_mm || 0) * exaggeration,
    z: (pose.translate_z_mm || 0) * exaggeration,
  };
}

// Rotation as axis-angle applications about the APPROXIMATE per-tooth frame.
// Returns [] when rotation is not renderable or no frame is available, so a
// viewer never invents an orientation. The tip/torque/rotation -> axis[0/1/2]
// mapping is an approximate visualization convention, not anatomy.
export function rotationApplications(pose, frame) {
  if (!pose || !pose.rotation_renderable || !frame || !Array.isArray(frame.axes)) {
    return [];
  }
  const pairs = [
    [frame.axes[0], pose.rotate_tip_deg],
    [frame.axes[1], pose.rotate_torque_deg],
    [frame.axes[2], pose.rotate_rotation_deg],
  ];
  return pairs
    .filter(([axis, deg]) => Array.isArray(axis) && deg)
    .map(([axis, deg]) => ({ axis, angleRad: degToRad(deg) }));
}

// Monotonic token so a slow async result can be discarded if a newer one started.
export function createLatest() {
  let token = 0;
  return {
    next: () => (token += 1),
    isCurrent: (value) => value === token,
  };
}
