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
    mesh_assets: [],
    tooth_meshes: [],
    fixed_teeth: parseToothList(state.clinicalControls.fixedTeeth).map((tooth) => ({
      tooth,
      stage_start: 0,
      stage_end: null,
      reason: "UI clinical control",
    })),
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
  if (!state.files.length) return [];
  return state.files.map((file) => ({
    asset: {
      id: `ui-${file.name.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`,
      format: "stl",
      provenance: "patient-derived",
      units: state.scanUnits,
      vertex_count: 0,
      face_count: 0,
      reference: file.name,
    },
    arch: state.scanArch || null,
    source: "intraoral-scan",
  }));
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
