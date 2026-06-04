export const state = {
  activeStep: "upload",
  view: "current",
  dim: "3d",
  file: null,
  scanUnits: "unverified",
  scanArch: "",
  // Latest response from the Python engine (POST /api/evaluate). The UI never
  // computes findings, gaps, timeline, or frames itself.
  lastEval: null,
  engineError: null,
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
  const value = Number(el(id).value);
  return Number.isFinite(value) ? value : 0;
}

export function stages() {
  return [...new Set(state.rows.map((row) => row.stage))].sort((a, b) => a - b);
}

export function maxStage() {
  return Math.max(0, ...stages());
}

export async function evaluatePlan(payload) {
  const response = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["engine request failed"]).join("; "));
  }
  return response.json();
}
