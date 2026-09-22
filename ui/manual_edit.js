// Pure, DOM-free manual target-authoring logic. No `document`, no `fetch`, no
// `state` import - unit-testable under Node (`node --test ui`).
//
// The user selects a tooth in the 3D preview and nudges its FINAL in-plane
// position. An authored target is just a normal `source:"manual"` stage delta
// written into the plan rows: the engine still computes all movement, and
// `Generate Plan` (the existing "authored" generation path) re-stages the target
// into cap-respecting stages. This module never computes movement or stages.
//
// Honesty constraints (see docs/SAFETY.md and planning/transforms.py):
// - Translation ONLY. Rotation is never authored here - the scan-local frame is
//   `rotation_renderable=false`, so tip/torque/rotation are left at zero.
// - In-plane ONLY. Authorable axes are x (mesiodistal-ish) and y (front-back).
//   Vertical z (intrusion/extrusion) is excluded: it is unreliable to judge from
//   a front 3D view and is the highest-risk axis to mis-author.
// - mm values are meaningless until scan units are confirmed, so the caller must
//   gate editing on `scaleConfirmed(scanUnits)`.

// Scan units count as confirmed for mm-valued authoring only when explicitly mm.
export const SCALE_CONFIRMED_UNITS = "mm";

// One nudge = 0.2 mm of planar translation on the target.
export const NUDGE_STEP_MM = 0.2;

// Authoring clamp per axis. This is a UI authoring bound (keeps a stray click
// from typing in a 50 mm target), NOT a clinical or per-stage movement cap - the
// engine's movement_caps rules own those and apply after Generate Plan re-stages.
export const TARGET_LIMIT_MM = 4;
export const TARGET_CAUTION_MM = 1.5;

// Authored targets live in a single stage; Generate Plan re-stages from there.
export const TARGET_STAGE = 1;

// The only axes a manual target may move along.
export const PLANAR_AXES = ["x", "y"];

export function scaleConfirmed(scanUnits) {
  return scanUnits === SCALE_CONFIRMED_UNITS;
}

export function isPlanarAxis(axis) {
  return PLANAR_AXES.includes(axis);
}

export function clampTarget(value, limit = TARGET_LIMIT_MM) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(-limit, Math.min(limit, value));
}

// A zeroed target row for a tooth: a real plan delta with no rotation and no
// vertical component. Shape matches the rows the rest of the UI authors.
export function emptyTargetRow(tooth, stage = TARGET_STAGE) {
  return { stage, tooth: String(tooth), x: 0, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 };
}

function isTargetRow(row, tooth, stage) {
  return row.stage === stage && String(row.tooth) === String(tooth);
}

// The tooth's authored target translation, or zeros if none exists yet.
export function targetFor(rows, tooth, stage = TARGET_STAGE) {
  const row = (rows || []).find((candidate) => isTargetRow(candidate, tooth, stage));
  return { x: row?.x || 0, y: row?.y || 0 };
}

// Resultant in-plane magnitude, for a readout. Never implies biomechanics.
export function targetMagnitudeMm(target) {
  return Math.hypot(target?.x || 0, target?.y || 0);
}

export function targetWarningTier(target, { caution = TARGET_CAUTION_MM, limit = TARGET_LIMIT_MM } = {}) {
  const magnitude = targetMagnitudeMm(target);
  if (magnitude >= limit) return "limit";
  if (magnitude >= caution) return "caution";
  return "ok";
}

export function targetStatusText(target, options = {}) {
  const magnitude = targetMagnitudeMm(target);
  const tier = targetWarningTier(target, options);
  if (tier === "limit") {
    return `At the ${TARGET_LIMIT_MM.toFixed(1)} mm guided edit limit. Use smaller changes or technician review.`;
  }
  if (tier === "caution") {
    return `${magnitude.toFixed(1)} mm total shift. Review warnings after rebuilding the plan.`;
  }
  if (magnitude > 0) return `${magnitude.toFixed(1)} mm total shift.`;
  return "No guided shift yet.";
}

// Return a NEW rows array with `tooth`'s target nudged by `deltaMm` on `axis`.
// Creates the target row if the tooth has none yet. A non-planar axis is a
// no-op (defensive: the UI never exposes z/rotation, but callers may be wrong).
// Rows are not mutated in place so callers can diff/undo if desired.
export function nudgeTarget(rows, tooth, axis, deltaMm, { limit = TARGET_LIMIT_MM, stage = TARGET_STAGE } = {}) {
  const current = Array.isArray(rows) ? rows : [];
  if (!isPlanarAxis(axis) || !tooth) return current.slice();
  const next = current.map((row) => ({ ...row }));
  let row = next.find((candidate) => isTargetRow(candidate, tooth, stage));
  if (!row) {
    row = emptyTargetRow(tooth, stage);
    next.push(row);
  }
  row[axis] = clampTarget((row[axis] || 0) + deltaMm, limit);
  return next;
}

// Return a NEW rows array with the tooth's target row removed (reset to none).
export function clearTarget(rows, tooth, stage = TARGET_STAGE) {
  return (rows || []).filter((row) => !isTargetRow(row, tooth, stage));
}
