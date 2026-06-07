export const state = {
  theme: "light",
  // The guided wizard is the default, primary experience for non-technical
  // first-time users. The dense technician workspace ("advanced") is opt-in via
  // the Technician view toggle.
  userMode: "simple",
  activeStep: "upload",
  // Guided wizard sub-state (the simplified primary flow). The wizard owns its
  // own step cursor so it is independent of the technician panel navigation.
  guided: {
    step: "upload",
    excludedTeeth: [],
    print: { busy: false, status: "", result: null },
  },
  // When true, the guided wizard is showing the isolated sample demonstration
  // (working state is snapshotted and restored on exit). See sample.js.
  sample: { active: false },
  view: "current",
  dim: "3d",
  file: null,
  files: [],
  scanSources: [],
  scanArchFilter: "both",
  scanRenderStatus: "No uploaded scan is loaded.",
  sampleStatus: "",
  uploadStorageStatus: "",
  scanUnits: "unverified",
  scanArch: "",
  // Latest response from the Python engine (POST /api/evaluate). The UI never
  // computes findings, gaps, timeline, or frames itself.
  lastEval: null,
  engineError: null,
  chat: {
    provider: "local",
    model: "local-educational-helper",
    contextScope: "summary",
    input: "",
    messages: [],
    status: "Ask about this plan. The local helper stays on this machine.",
    busy: false,
    apiKeyPresent: false,
    agentAccessEnabled: false,
    agentEndpoint: "",
  },
  // Latest /api/generate-plan orchestration result, shown in the Review panel.
  generation: {
    busy: false,
    status: "",
    acknowledged: false,
    notes: "",
    landmarks: null,
    landmarksStatus: "",
    result: null,
  },
  detailMode: {
    generation: "basic",
    ai: "basic",
  },
  // Saved plan versions (case store) for the current Plan ID.
  versions: {
    busy: false,
    status: "",
    note: "",
    list: [],
  },
  simpleGoal: "general-alignment",
  simpleAcknowledged: false,
  demoInitialOffsets: {},
  // When true, the 3D viewer loads the bundled demo crown meshes per tooth class.
  useDemoMeshes: false,
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
  printExport: {
    enabled: false,
    export_format: "stl",
    delivery_email: "",
    model_material: "validated dental model resin",
    thermoforming_material: "user-selected aligner sheet material",
    safety_acknowledged: false,
  },
  clinicalControls: {
    fixedTeeth: "",
    attachmentTeeth: "",
    movementExclusions: "",
    iprContacts: {},
  },
  // Empty by default: the guided "teeth that move" list and the technician stage
  // table both derive from rows, so there are no placeholder teeth until the user
  // uploads a scan and builds a plan (or opens the Sample Test Case).
  rows: [],
};

export const iprContactPairs = [
  ["18", "17"], ["17", "16"], ["16", "15"], ["15", "14"], ["14", "13"], ["13", "12"], ["12", "11"], ["11", "21"], ["21", "22"], ["22", "23"], ["23", "24"], ["24", "25"], ["25", "26"], ["26", "27"], ["27", "28"],
  ["48", "47"], ["47", "46"], ["46", "45"], ["45", "44"], ["44", "43"], ["43", "42"], ["42", "41"], ["41", "31"], ["31", "32"], ["32", "33"], ["33", "34"], ["34", "35"], ["35", "36"], ["36", "37"], ["37", "38"],
];

export const availabilityLabels = {
  intraoral_scan: "Intraoral scan",
  segmented_teeth: "Segmented teeth",
  roots: "Roots",
  cbct: "CBCT",
  periodontal_status: "Periodontal status",
  occlusion_scan: "Occlusion scan",
  photos: "Photos",
  radiographs: "Radiographs",
  clinician_notes: "Treatment notes",
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

export async function requestPlanGeneration(payload) {
  const response = await fetch("/api/generate-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["generation request failed"]).join("; "));
  }
  return response.json();
}

export async function savePlanVersion(payload) {
  const response = await fetch("/api/plan/version", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["save failed"]).join("; "));
  }
  return response.json();
}

export async function listCaseVersions(caseId) {
  const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}`);
  if (!response.ok) return { ok: false, versions: [] };
  return response.json();
}

export async function askPlanAssistant(payload) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["chat request failed"]).join("; "));
  }
  return response.json();
}

export async function requestPrintPackage(payload) {
  const response = await fetch("/api/print-package", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["print package request failed"]).join("; "));
  }
  return response.json();
}
