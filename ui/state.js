export const state = {
  activeStep: "upload",
  view: "current",
  file: null,
  scanUnits: "unverified",
  scanArch: "",
  availability: {
    intraoral_scan: true,
    segmented_teeth: false,
    roots: false,
    cbct: false,
    periodontal_status: false,
    occlusion_scan: false,
    photos: false,
    radiographs: false,
    clinician_notes: false,
  },
  caps: {
    linear_mm: 0.25,
    angular_deg: 1.0,
    rotation_deg: 2.0,
    intrusion_extrusion_mm: 0.1,
  },
  rows: [
    { stage: 0, tooth: "11", x: 0.2, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
    { stage: 1, tooth: "11", x: 0.1, y: 0.1, z: 0, tip: 0, torque: 0, rotation: 0 },
  ],
};

export const availabilityLabels = {
  intraoral_scan: "Intraoral scan",
  segmented_teeth: "Segmented teeth",
  roots: "Roots",
  cbct: "CBCT",
  periodontal_status: "Periodontal status",
  occlusion_scan: "Occlusion scan",
  photos: "Photos",
  radiographs: "Radiographs",
  clinician_notes: "Clinician notes",
};

export const toothPositions = {
  18: [128, 148], 17: [170, 118], 16: [218, 94], 15: [270, 78],
  14: [324, 66], 13: [382, 58], 12: [438, 56], 11: [492, 58],
  21: [546, 58], 22: [602, 56], 23: [658, 58], 24: [716, 66],
  25: [770, 78], 26: [822, 94], 27: [870, 118], 28: [912, 148],
  48: [128, 368], 47: [170, 398], 46: [218, 422], 45: [270, 438],
  44: [324, 450], 43: [382, 458], 42: [438, 460], 41: [492, 458],
  31: [546, 458], 32: [602, 460], 33: [658, 458], 34: [716, 450],
  35: [770, 438], 36: [822, 422], 37: [870, 398], 38: [912, 368],
};

export function el(id) {
  return document.getElementById(id);
}

export function numberValue(id) {
  return Number(el(id).value || 0);
}

export function stages() {
  return [...new Set(state.rows.map((row) => row.stage))].sort((a, b) => a - b);
}

export function maxStage() {
  return Math.max(0, ...stages());
}

export function cumulativeRows(stageIndex) {
  const totals = new Map();
  for (const row of state.rows.filter((item) => item.stage <= stageIndex)) {
    const current = totals.get(row.tooth) || { x: 0, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 };
    totals.set(row.tooth, {
      x: current.x + row.x,
      y: current.y + row.y,
      z: current.z + row.z,
      tip: current.tip + row.tip,
      torque: current.torque + row.torque,
      rotation: current.rotation + row.rotation,
    });
  }
  return totals;
}

export function dataGaps() {
  const gaps = [];
  if (!state.availability.roots) gaps.push("roots unavailable");
  if (!state.availability.cbct) gaps.push("CBCT unavailable");
  if (!state.availability.periodontal_status) gaps.push("periodontal status unavailable");
  if (!state.availability.occlusion_scan) gaps.push("occlusion scan unavailable");
  if (!state.availability.clinician_notes) gaps.push("clinician notes unavailable");
  if (state.file && state.scanUnits === "unverified") {
    gaps.push("scan units unverified; geometry scale cannot be trusted until confirmed");
  }
  return gaps;
}

export function findings() {
  if (state.file && state.scanUnits === "unverified") {
    return ["Movement-cap evaluation skipped: scan units unverified"];
  }
  const results = [];
  for (const row of state.rows) {
    const horizontal = Math.hypot(row.x, row.y);
    if (horizontal > state.caps.linear_mm) results.push(`Stage ${row.stage} tooth ${row.tooth}: linear cap`);
    if (Math.abs(row.z) > state.caps.intrusion_extrusion_mm) {
      results.push(`Stage ${row.stage} tooth ${row.tooth}: vertical cap`);
    }
    if (Math.abs(row.tip) > state.caps.angular_deg || Math.abs(row.torque) > state.caps.angular_deg) {
      results.push(`Stage ${row.stage} tooth ${row.tooth}: angular cap`);
    }
    if (Math.abs(row.rotation) > state.caps.rotation_deg) {
      results.push(`Stage ${row.stage} tooth ${row.tooth}: rotation cap`);
    }
  }
  return results;
}
