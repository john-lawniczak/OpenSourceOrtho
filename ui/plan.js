import { stageBuckets } from "./core.js";
import { el, numberValue, state } from "./state.js";

export function planJson() {
  return {
    id: el("planId").value,
    title: el("planTitle").value,
    numbering_system: "FDI",
    coordinate_frame: { name: "scan-local" },
    data: state.availability,
    settings: {
      movement_caps: { default: state.caps, per_tooth_overrides: {} },
      timeline: { wear_interval_days: numberValue("wearInterval") },
      print_export: {
        ...state.printExport,
        delivery_email: state.printExport.delivery_email || null,
      },
    },
    scans: scanPayload(),
    case_records: state.caseRecords,
    // Per-tooth meshes only appear once the user has reviewed and explicitly
    // applied an auto-segmentation proposal (see segment.js). Drafts are never
    // merged automatically.
    mesh_assets: [
      ...(state.fixtureMeshAssets || []),
      ...(state.segmentation.applied?.mesh_assets || []),
    ],
    tooth_meshes: state.segmentation.applied?.tooth_meshes || [],
    // CBCT registration + reviewed anatomy round-trip when present (e.g. an
    // imported plan/case version). The browser has no CBCT processing flow yet,
    // so these are usually empty; reviewer edits mutate them in place.
    registrations: state.registrations || [],
    derived_anatomy: state.derivedAnatomy || null,
    fixed_teeth: fixedTeeth(),
    movement_exclusions: parseMovementExclusions(state.clinicalControls.movementExclusions),
    attachments: parseToothList(state.clinicalControls.attachmentTeeth).map((tooth) => ({
      tooth,
      type: "vertical_rectangular",
      surface: "buccal",
      stage_start: 0,
      stage_end: null,
      purpose: "UI clinical control",
    })),
    interproximal_reductions: parseIprContacts(state.clinicalControls.iprContacts),
    planned_spacing: [],
    // Contiguous-reindexed stage buckets (see core.stageBuckets) so the exported
    // plan satisfies the Python TreatmentPlan contiguity invariant.
    stages: stageBuckets(state.rows).map((bucket) => ({
      index: bucket.index,
      deltas: bucket.rows.map(deltaPayload),
    })),
  };
}

// Fixed teeth = technician-entered list PLUS any teeth the guided user chose to
// hold still (excluded). Merged here so both flows share one plan contract.
function fixedTeeth() {
  const fromControls = parseToothList(state.clinicalControls.fixedTeeth).map((tooth) => tooth.value);
  const merged = new Set([...fromControls, ...(state.guided.excludedTeeth || [])]);
  return [...merged].map((value) => ({
    tooth: { system: "FDI", value },
    stage_start: 0,
    stage_end: null,
    reason: "UI clinical control",
  }));
}

function parseToothList(value) {
  return String(value || "")
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((value) => ({ system: "FDI", value }));
}

function parseMovementExclusions(value) {
  return String(value || "")
    .split(/[;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [toothValue, axesValue = ""] = item.split(":");
      return {
        tooth: { system: "FDI", value: toothValue.trim() },
        axes: axesValue.split(",").map((axis) => axis.trim()).filter(Boolean),
        stage_start: 0,
        stage_end: null,
        reason: "UI clinical control",
      };
    });
}

function parseIprContacts(value) {
  return Object.entries(value || {})
    .filter(([, amount]) => Number(amount) > 0)
    .map(([contact, amount]) => {
      const [a, b] = String(contact).split("-");
      return {
        tooth_a: { system: "FDI", value: String(a || "").trim() },
        tooth_b: { system: "FDI", value: String(b || "").trim() },
        amount_mm: Number(amount),
        stage_index: 0,
        source: "manual",
        notes: "UI clinical control",
      };
    });
}

function scanPayload() {
  const sources = state.scanSources.length
    ? state.scanSources.map((source) => ({
      name: source.name,
      reference: source.asset?.id || source.url || source.name,
      arch: state.scanArch || source.arch || null,
      asset: source.asset || null,
    }))
    : state.files.map((file) => ({ name: file.name, reference: file.name, arch: state.scanArch || null, asset: null }));
  if (!sources.length) return [];
  return sources.map((source) => ({
    asset: source.asset ? { ...source.asset, units: state.scanUnits } : fallbackScanAsset(source),
    arch: source.arch,
    source: "intraoral-scan",
  }));
}

function fallbackScanAsset(source) {
  return {
    id: `ui-${source.name.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`,
    format: "stl",
    provenance: "patient-derived",
    units: state.scanUnits,
    vertex_count: 0,
    face_count: 0,
    reference: source.reference,
  };
}

function deltaPayload(row) {
  return {
    tooth: { system: "FDI", value: row.tooth },
    translate_x_mm: row.x,
    translate_y_mm: row.y,
    translate_z_mm: row.z,
    rotate_tip_deg: row.tip,
    rotate_torque_deg: row.torque,
    rotate_rotation_deg: row.rotation,
    coordinate_frame: "scan-local",
    source: "manual",
    mesh_asset_id: null,
  };
}
