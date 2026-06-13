// DOM-free direct-control authoring helpers for the technician workspace.
//
// These controls author review-gated geometric proposals into the same staged
// row format as the existing stage table. They do not approve treatment or
// manufacturing readiness; callers must keep the UI caveat visible.

import { archFromTooth } from "./core.js";

export const DIRECT_CONTROL_STAGE = 1;

export const CONTROL_AXES = {
  translation: ["x", "y"],
  intrusion_extrusion: ["z"],
  rotation: ["rotation"],
  crown_tip: ["tip"],
  crown_torque: ["torque"],
  crown_angulation: ["tip", "torque"],
};

export const CONTROL_LIMITS = {
  x: 4,
  y: 4,
  z: 2,
  tip: 15,
  torque: 15,
  rotation: 20,
};

export const CONTROL_STEPS = {
  x: 0.1,
  y: 0.1,
  z: 0.05,
  tip: 0.5,
  torque: 0.5,
  rotation: 0.5,
};

export function emptyDirectRow(tooth, stage = DIRECT_CONTROL_STAGE) {
  return { stage, tooth: String(tooth), x: 0, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 };
}

export function controlGate({ unitsConfirmed, segmentedTeeth, rootsAvailable, reviewedAnatomy } = {}) {
  const blockers = [];
  if (!unitsConfirmed) blockers.push("scan units must be confirmed in millimeters");
  if (!segmentedTeeth) blockers.push("reviewed segmentation is required for direct tooth controls");
  const warnings = [];
  if (!rootsAvailable || !reviewedAnatomy) {
    warnings.push("root/bone response cannot be assessed from the current records");
  }
  return { allowed: blockers.length === 0, blockers, warnings };
}

export function clampControl(axis, value, limits = CONTROL_LIMITS) {
  const limit = limits[axis] ?? 0;
  if (!Number.isFinite(value)) return 0;
  return Math.max(-limit, Math.min(limit, value));
}

export function applyDirectControl(
  rows,
  tooth,
  axis,
  delta,
  { stage = DIRECT_CONTROL_STAGE, limits = CONTROL_LIMITS } = {},
) {
  const current = Array.isArray(rows) ? rows : [];
  if (!tooth || !(axis in CONTROL_LIMITS)) return current.map((row) => ({ ...row }));
  const next = current.map((row) => ({ ...row }));
  let row = next.find((candidate) => candidate.stage === stage && String(candidate.tooth) === String(tooth));
  if (!row) {
    row = emptyDirectRow(tooth, stage);
    next.push(row);
  }
  row[axis] = clampControl(axis, Number(row[axis] || 0) + Number(delta || 0), limits);
  return next;
}

export function setDirectControl(
  rows,
  tooth,
  axis,
  value,
  { stage = DIRECT_CONTROL_STAGE, limits = CONTROL_LIMITS } = {},
) {
  const current = Array.isArray(rows) ? rows : [];
  if (!tooth || !(axis in CONTROL_LIMITS)) return current.map((row) => ({ ...row }));
  const next = current.map((row) => ({ ...row }));
  let row = next.find((candidate) => candidate.stage === stage && String(candidate.tooth) === String(tooth));
  if (!row) {
    row = emptyDirectRow(tooth, stage);
    next.push(row);
  }
  row[axis] = clampControl(axis, Number(value || 0), limits);
  return next;
}

export function proposeArchResponse(rows, tooth, expansionMm, options = {}) {
  const arch = archFromTooth(tooth);
  const gate = controlGate(options);
  const warnings = [...gate.blockers, ...gate.warnings];
  if (!arch) warnings.push("selected tooth does not map to an FDI arch");
  if (!Number.isFinite(expansionMm) || expansionMm === 0) {
    warnings.push("no arch expansion or contraction amount was provided");
  }
  if (!gate.allowed || !arch || !Number.isFinite(expansionMm) || expansionMm === 0) {
    return { rows: Array.isArray(rows) ? rows.map((row) => ({ ...row })) : [], proposed: [], warnings };
  }

  const candidates = [...new Set((rows || [])
    .map((row) => String(row.tooth || ""))
    .filter((value) => archFromTooth(value) === arch))].sort();
  const proposedTeeth = candidates.length ? candidates : [String(tooth)];
  const signFor = (value) => (String(value)[0] === "1" || String(value)[0] === "4" ? -1 : 1);
  let next = rows;
  const proposed = [];
  for (const value of proposedTeeth) {
    const amount = Number((expansionMm * signFor(value)).toFixed(3));
    next = applyDirectControl(next, value, "x", amount);
    proposed.push({ tooth: value, axis: "x", amount_mm: amount });
  }
  warnings.push("arch response is a same-arch geometric proposal; contacts/spacing require deterministic review after restaging");
  return { rows: next, proposed, warnings };
}
