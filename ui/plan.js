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
    },
    scans: scanPayload(),
    mesh_assets: [],
    tooth_meshes: [],
    // Contiguous-reindexed stage buckets (see core.stageBuckets) so the exported
    // plan satisfies the Python TreatmentPlan contiguity invariant.
    stages: stageBuckets(state.rows).map((bucket) => ({
      index: bucket.index,
      deltas: bucket.rows.map(deltaPayload),
    })),
  };
}

function scanPayload() {
  if (!state.file) return [];
  return [{
    asset: {
      id: `ui-${state.file.name.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`,
      format: "stl",
      provenance: "patient-derived",
      units: state.scanUnits,
      vertex_count: 0,
      face_count: 0,
      reference: state.file.name,
    },
    arch: state.scanArch || null,
    source: "intraoral-scan",
  }];
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
