// Pure, DOM-free UI logic. No `document`, no `fetch`, no `state` import - so it
// is unit-testable under Node (`node --test ui`) without a browser or jsdom.

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

// Each arch normally has 14 teeth in this app (third molars excluded), mirroring
// the engine's default_arch_order length. A proposed count below this means a
// tooth looks absent - the cue to mark the gap and re-anchor the labels.
export const FULL_ARCH_TEETH = 14;

export function normalizeArchLabel(value) {
  const text = String(value || "").trim().toLowerCase();
  if (text === "upper" || text === "maxillary") return "maxillary";
  if (text === "lower" || text === "mandibular") return "mandibular";
  return null;
}

export function inferArchFromName(name = "") {
  const text = String(name).toLowerCase();
  if (
    text.includes("upper") ||
    text.includes("top") ||
    text.includes("maxilla") ||
    text.includes("maxillary") ||
    /(^|[-_\s])u(\.stl|[-_\s])/.test(text)
  ) {
    return "maxillary";
  }
  if (
    text.includes("lower") ||
    text.includes("bottom") ||
    text.includes("mandible") ||
    text.includes("mandibular") ||
    /(^|[-_\s])l(\.stl|[-_\s])/.test(text)
  ) {
    return "mandibular";
  }
  return null;
}

export function archFromTooth(tooth) {
  const quadrant = String(tooth || "")[0];
  if (quadrant === "1" || quadrant === "2" || quadrant === "5" || quadrant === "6") {
    return "maxillary";
  }
  if (quadrant === "3" || quadrant === "4" || quadrant === "7" || quadrant === "8") {
    return "mandibular";
  }
  return null;
}

// Confidence tier from a 0-100 percentage. Low confidence (often a count
// mismatch) should stand out so the reviewer checks those tooth numbers first.
export function confidenceTier(pct) {
  if (pct < 45) return "low";
  if (pct < 65) return "mid";
  return "high";
}

// Banner (HTML) when a proposed arch is not a full arch. Returns "" when every
// arch is complete. The message depends on whether the reviewer has marked a gap,
// because a count below a full arch is ambiguous: a tooth may be absent OR two
// crowns may have merged into one region (common on the flat upper occlusal
// plane). `markedGapCount` is how many missing teeth the user has entered.
export function countNoteMarkup(teeth, markedGapCount = 0) {
  const byArch = {};
  for (const tooth of teeth || []) byArch[tooth.arch] = (byArch[tooth.arch] || 0) + 1;
  const counts = Object.entries(byArch);
  if (!counts.length || !counts.some(([, n]) => n !== FULL_ARCH_TEETH)) return "";
  const summary = counts.map(([arch, n]) => `${n} ${escapeHtml(arch)}`).join(", ");
  if (markedGapCount > 0) {
    const gapWord = markedGapCount === 1 ? "gap" : "gaps";
    return (
      `<p class="segment-count-note">Proposed ${summary} for your ${markedGapCount} ` +
      `marked ${gapWord}. Review the tooth numbers below, then apply.</p>`
    );
  }
  return (
    `<p class="segment-count-note">Proposed ${summary} — a full arch is ${FULL_ARCH_TEETH} teeth. ` +
    "Some crowns may have merged into one region, or a tooth may be absent. If a tooth " +
    "is missing, enter its FDI number in “Missing teeth” above and use “Re-anchor labels”; " +
    "otherwise review the tooth numbers below.</p>"
  );
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

export function rowsFromPlan(plan) {
  const rows = [];
  for (const stage of plan.stages || []) {
    for (const delta of stage.deltas || []) {
      rows.push({
        stage: stage.index,
        tooth: delta.tooth.value,
        x: delta.translate_x_mm,
        y: delta.translate_y_mm,
        z: delta.translate_z_mm,
        tip: delta.rotate_tip_deg,
        torque: delta.rotate_torque_deg,
        rotation: delta.rotate_rotation_deg,
      });
    }
  }
  return rows;
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

export function closestDatasetTarget(target, key) {
  if (!target) return null;
  if (target.dataset?.[key] !== undefined) return target;
  if (typeof target.closest !== "function") return null;
  const attr = key.replace(/[A-Z]/g, (char) => `-${char.toLowerCase()}`);
  return target.closest(`[data-${attr}]`);
}
