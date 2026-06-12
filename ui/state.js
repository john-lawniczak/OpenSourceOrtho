export const state = {
  theme: "light",
  // The guided wizard is the default, primary experience for non-technical
  // first-time users. The dense technician workspace ("advanced") is opt-in via
  // the Technician view toggle.
  userMode: "simple",
  activeStep: "upload",
  // Where the "Back" button in a reference panel (Key Terms, Imaging guide)
  // returns to, so those panels are reachable from either mode without trapping
  // the user. Set when an info step is opened (see goToStep in app.js).
  returnStep: "upload",
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
  recordUploadStatus: "",
  caseRecords: [],
  // CBCT registration transforms and reviewed CBCT-derived anatomy. Usually
  // empty (the browser has no CBCT processing flow); populated when an imported
  // plan carries them, and mutated by the anatomy review controls.
  registrations: [],
  derivedAnatomy: null,
  cbctWorkflow: {
    mask: null,
    status: "",
    busy: false,
    registrationAccepted: false,
    rmseMm: 0.25,
    fitness: 0.9,
  },
  scanUnits: "unverified",
  scanArch: "",
  // Latest response from the Python engine (POST /api/evaluate). The UI never
  // computes findings, gaps, timeline, or frames itself.
  lastEval: null,
  engineError: null,
  chat: {
    provider: "local",
    model: "local-educational-helper",
    connectors: [
      {
        kind: "local",
        label: "Local educational helper",
        model: "local-educational-helper",
        models: ["local-educational-helper"],
        enabled: true,
        shares_patient_data: false,
        requires_api_key: false,
      },
      {
        kind: "openai",
        label: "OpenAI",
        model: "gpt-5.5",
        models: ["gpt-5.5", "gpt-5.4", "gpt-4.1"],
        shares_patient_data: true,
        requires_api_key: true,
        supports_streaming: true,
      },
      {
        kind: "claude-code",
        label: "Claude Code",
        model: "claude-opus-4-8",
        models: ["claude-opus-4-8", "claude-sonnet-4-7", "claude-code-default"],
        shares_patient_data: true,
        requires_api_key: true,
      },
      {
        kind: "mcp",
        label: "MCP-compatible model host",
        model: "mcp-model",
        models: ["mcp-model"],
        shares_patient_data: true,
        requires_api_key: true,
        supports_streaming: true,
        allow_custom_model: true,
      },
      {
        kind: "open-source",
        label: "Open-source local model",
        model: "local-model",
        models: ["local-model", "llama-3.1", "qwen2.5"],
        shares_patient_data: true,
        requires_api_key: false,
        allow_custom_model: true,
      },
    ],
    modelByProvider: {
      local: "local-educational-helper",
      openai: "gpt-5.5",
      "claude-code": "claude-opus-4-8",
      mcp: "mcp-model",
      "open-source": "local-model",
    },
    // The assistant always has the full plan context (no user-facing scope toggle).
    contextScope: "full_plan",
    input: "",
    messages: [],
    status: "Ask about this plan. The local helper stays on this machine.",
    busy: false,
    collapsed: false,
    apiKeyPresent: false,
    agentAccessEnabled: false,
    agentEndpoint: "",
    sessionId: null,
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
  // When true, the 3D viewer draws FDI tooth-number labels over each tooth.
  showToothLabels: false,
  // When true, the 3D viewer draws a true-scale mm reference bar beside a loaded
  // scan (only meaningful once scan units are confirmed mm). scaleStatus is the
  // status strip text, set by the viewer render.
  showScale: false,
  scaleStatus: "",
  stagePlayback: {
    playing: false,
    timer: null,
  },
  // Manual target authoring: the user clicks a tooth in the 3D preview and
  // nudges its final in-plane position. The authored target lives in `rows` as a
  // normal source:"manual" stage delta (see manual_edit.js), so only selection
  // and a status string are held here.
  manualEdit: {
    selectedTooth: null,
    status: "",
    undoStack: [],
  },
  // Advisory auto-segmentation proposal (POST /api/segment). Never auto-applied:
  // `applied` holds only what the user explicitly accepted (and may have corrected).
  segmentation: {
    busy: false,
    status: "",
    proposal: null,
    edits: {},
    applied: null,
    // Comma/space-separated FDI numbers the user marks as absent. Geometry cannot
    // tell which tooth is missing, so this signal anchors the proposed FDI labels
    // around the gap (see segment.js / tooth_values_for_arch).
    missingTeeth: "",
  },
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
    aligner_shell_enabled: false,
    sheet_thickness_mm: 0.6,
    gingival_trim_margin_mm: 2,
  },
  clinicalControls: {
    fixedTeeth: "",
    attachmentTeeth: "",
    movementExclusions: "",
    iprContacts: {},
  },
  // Occlusal proximity overlay (red/amber/green "where the arches meet" map). The
  // map comes from the server (POST /api/occlusion) for a server-local upper+lower
  // scan pair; `enabled` toggles the overlay in the 3D viewer. Geometric proximity,
  // never bite force - and only shown for an as-scanned registration.
  proximity: {
    enabled: false,
    busy: false,
    status: "",
    map: null,
    registration: null,
    // When true (and the registration is an estimated alignment), the viewer moves
    // the lower arch into the registered occlusal frame instead of its scanned pose.
    registeredView: false,
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

export async function streamPlanAssistant(payload, { onDelta, onDone }) {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok || !response.body) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["chat stream failed"]).join("; "));
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const eventText of events) handleStreamEvent(eventText, onDelta, onDone);
  }
  if (buffer.trim()) handleStreamEvent(buffer, onDelta, onDone);
}

function handleStreamEvent(eventText, onDelta, onDone) {
  const lines = eventText.split("\n");
  const kind = lines.find((line) => line.startsWith("event: "))?.slice(7) || "message";
  const dataLine = lines.find((line) => line.startsWith("data: "));
  const data = dataLine ? JSON.parse(dataLine.slice(6)) : {};
  if (kind === "delta") onDelta(data.text || "");
  if (kind === "done") onDone(data);
  if (kind === "error") throw new Error((data.errors || ["chat stream failed"]).join("; "));
}

export async function loadAiConnectors() {
  const response = await fetch("/api/ai/connectors");
  if (!response.ok) return { ok: false, connectors: [] };
  return response.json();
}

export async function requestOcclusion(payload) {
  const response = await fetch("/api/occlusion", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["occlusion request failed"]).join("; "));
  }
  return response.json();
}

export async function requestSegmentation(payload) {
  const response = await fetch("/api/segment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["segmentation request failed"]).join("; "));
  }
  return response.json();
}

export async function requestCbctAnatomyProposal(payload) {
  const response = await fetch("/api/cbct/propose-anatomy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["CBCT proposal request failed"]).join("; "));
  }
  return response.json();
}

export async function requestCbctAnatomyReview(payload) {
  const response = await fetch("/api/cbct/review-anatomy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["CBCT review request failed"]).join("; "));
  }
  return response.json();
}

export async function uploadStlFile(file, { arch } = {}) {
  const headers = {
    "Content-Type": "model/stl",
    "X-Filename": file.name || "uploaded.stl",
  };
  if (arch) headers["X-Arch"] = arch;
  const response = await fetch("/api/upload/stl", {
    method: "POST",
    headers,
    body: file,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["upload failed"]).join("; "));
  }
  return response.json();
}

export async function uploadCaseRecord(file, { kind = "document", modality } = {}) {
  const headers = {
    "Content-Type": file.type || "application/octet-stream",
    "X-Filename": file.name || "record",
    "X-Record-Kind": kind,
  };
  if (modality) headers["X-Modality"] = modality;
  const response = await fetch("/api/upload/record", {
    method: "POST",
    headers,
    body: file,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["record upload failed"]).join("; "));
  }
  return response.json();
}

export async function requestCaseReview(payload) {
  const response = await fetch("/api/case-review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["case review request failed"]).join("; "));
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
