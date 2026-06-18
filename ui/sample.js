// Sample test case: an isolated, self-contained walkthrough that reuses the real
// guided wizard UI (same step chips: upload -> teeth & time -> details -> review
// -> 3D preview -> print) so a first-time viewer sees exactly what a guided user
// sees, pre-filled with the bundled test-case records. It starts at step 1 so the
// user walks the whole flow: (1) the two test-case STL scans are already loaded,
// (2) a Balanced 10-day pace with every tooth selected, (4) a plain summary and
// timeline, (5) the 3D preview rendered from the exact test-case STL models.
//
// Opening it snapshots the user's working state and restores it on exit, so
// nothing the sample does leaks into the user's own plan, uploads, or editors.
//
// The 3D preview shows the real STL scans in OVERLAY view. On entry the sample
// also runs the on-device auto-segmenter on the bundled scans and applies the
// per-tooth draft (see prepareSampleSegmentation), so the planned layer animates
// the scan's own crowns moving crowded -> aligned across stages as the slider
// drags. If segmentation is unavailable, movement falls back to markers/arrows.

import { el, state } from "./state.js";
import { applySegmentation, proposeSegmentation } from "./segment.js";
import { canonicalScanSources, demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";

// State keys the sample overwrites and therefore must save/restore.
const SNAPSHOT_STATE_KEYS = [
  "rows", "files", "file", "scanSources", "caseRecords", "fixtureMeshAssets", "registrations", "derivedAnatomy",
  "recordUploadStatus", "useDemoMeshes", "demoInitialOffsets",
  "view", "activeStep", "userMode", "scanArchFilter", "simpleGoal",
  "simpleAcknowledged", "dim", "sampleStatus", "scanRenderStatus", "availability",
];

const ROOT_BONE_FIXTURE_URL = "./example-scans/canonical-orthocad-001/root-bone-fixture.json";
// DOM field values the sample overwrites and must restore.
const SNAPSHOT_FIELDS = ["planTitle", "planId", "wearInterval", "exaggeration", "scanUnits", "scanArch", "simpleGoal"];

let saved = null;

export function sampleActive() {
  return Boolean(saved);
}

export function enterSample() {
  if (saved) return;
  saved = {
    state: {},
    fields: {},
    acknowledged: el("simpleAcknowledged").checked,
    guidedStep: state.guided.step,
    excludedTeeth: [...state.guided.excludedTeeth],
    // segmentation is a nested object mutated in place, so snapshot the whole
    // object and give the sample a fresh one - otherwise a segmentation applied
    // inside the sample would leak into the user's real plan on exit.
    segmentation: state.segmentation,
    // Proximity is likewise a nested, scan-specific object; snapshot it and give the
    // sample a fresh one so a bite overlay computed inside the sample never leaks.
    proximity: state.proximity,
    manualEdit: state.manualEdit,
  };
  for (const key of SNAPSHOT_STATE_KEYS) saved.state[key] = state[key];
  for (const field of SNAPSHOT_FIELDS) saved.fields[field] = el(field).value;
  state.segmentation = { busy: false, status: "", proposal: null, edits: {}, applied: null };
  state.proximity = { enabled: false, busy: false, status: "", map: null, registration: null, registeredView: false };
  state.manualEdit = { selectedTooth: null, status: "", undoStack: [] };
  // Fresh data manifest for the sample plan (the user's object is snapshotted
  // above and restored on exit): only the bundled intraoral scans are "available"
  // until the sample's segmentation is applied (prepareSampleSegmentation).
  state.availability = {
    ...state.availability,
    intraoral_scan: true, segmented_teeth: false, roots: false, cbct: false,
    periodontal_status: false, occlusion_scan: false, photos: false,
    radiographs: false, clinician_notes: false,
  };

  // Isolated walkthrough plan: a simulated crowding correction over 4 stages
  // (0 = the starting point), paired with the two real test-case STL scans so the
  // 3D preview renders the exact bundled models, not bundled placeholder crowns.
  state.rows = syntheticCrowdingRows(4, { includeBaseline: true });
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = false;
  state.scanSources = canonicalScanSources;
  state.caseRecords = [];
  state.fixtureMeshAssets = [];
  state.registrations = [];
  state.derivedAnatomy = null;
  state.recordUploadStatus = "";
  state.files = [];
  state.file = null;
  state.scanArchFilter = "both";
  state.view = "overlay";
  state.dim = "3d";
  state.simpleGoal = "crowding";
  // Every tooth in the plan is included (none held still) so step 2 reads as
  // "all teeth selected".
  state.guided.excludedTeeth = [];
  // Reuse the guided wizard (not a separate screen) so the sample shows the same
  // step chips and panels; the sample flag drives the banner and isolation.
  state.userMode = "simple";
  state.sample.active = true;
  // Start at step 1 so a first-time user walks the whole flow from the top.
  state.guided.step = "upload";
  state.simpleAcknowledged = true;
  state.sampleStatus =
    "Loading the root/bone-aware sample fixture, then segmenting the bundled scans into "
    + "individual 3D teeth on this machine (a few seconds)... "
    + "Not a real patient and not a medical device.";
  el("planTitle").value = "Sample test case";
  el("planId").value = "sample-test-case";
  el("wearInterval").value = "10";
  // x8 keeps the segmented real crowns visibly moving without flinging them off
  // the arch (the schematic demo uses higher values, but those are placeholder
  // pegs - real crowns at true scan scale read as broken above ~x8).
  el("exaggeration").value = "8";
  el("scanUnits").value = "mm";
  el("simpleAcknowledged").checked = true;
}

export async function applySampleRootBoneFixture() {
  if (!state.sample.active) return false;
  try {
    const response = await fetch(ROOT_BONE_FIXTURE_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const fixture = await response.json();
    if (!state.sample.active) return false;
    state.caseRecords = fixture.case_records || [];
    state.fixtureMeshAssets = fixture.mesh_assets || [];
    state.registrations = fixture.registrations || [];
    state.derivedAnatomy = fixture.derived_anatomy || null;
    state.availability = { ...state.availability, ...(fixture.availability_patch || {}) };
    state.recordUploadStatus =
      "Sample root/bone fixture loaded: redacted CBCT metadata, accepted fixture registration, and safe derived landmarks.";
    return true;
  } catch (error) {
    state.recordUploadStatus = `Sample root/bone fixture unavailable: ${error.message}`;
    return false;
  }
}

// Prepare the sample's moving teeth: run the on-device auto-segmenter on the two
// bundled scans and apply the resulting per-tooth draft, so the 3D preview moves
// the scan's own crowns stage by stage instead of marker arrows. Pre-applying a
// model-generated draft is sample-only behaviour: the sample is an isolated,
// clearly-labelled simulation (a user's own plan still requires explicit review
// and apply in the segmentation panel), and exit restores the user's state.
// Returns true when per-tooth movement is ready, false on fallback.
export async function prepareSampleSegmentation() {
  if (!state.sample.active) return false;
  const seg = state.segmentation;
  await proposeSegmentation();
  // The user may exit (or restart) the sample while the segmenter runs; apply
  // only when THIS sample run's segmentation is still the active one.
  if (!state.sample.active || state.segmentation !== seg) return false;
  if (!seg.proposal) {
    state.sampleStatus =
      "A simulated walkthrough. Per-tooth segmentation is unavailable, so planned movement is shown "
      + "with markers and arrows. Not a real patient and not a medical device.";
    return false;
  }
  applySegmentation();
  if (!seg.applied) return false;
  // The sample plan now carries per-tooth meshes; reflect that in its data
  // manifest (replace, never mutate - the user's object is snapshotted).
  state.availability = { ...state.availability, segmented_teeth: true };
  seg.status =
    "Sample: an auto-segmentation draft was applied for you so the 3D preview can move each tooth. "
    + "In your own plan you review and apply segmentation yourself.";
  state.sampleStatus =
    "A simulated root/bone-aware walkthrough: each tooth is segmented from the bundled scans, "
    + "trusted fixture axes make rotation/anatomical-frame review available, and CBCT boundary priors "
    + "can inform segmentation. Drag the stage slider or press Play. "
    + "Not a real patient and not a medical device.";
  return true;
}

export function exitSample() {
  if (!saved) return;
  for (const key of SNAPSHOT_STATE_KEYS) state[key] = saved.state[key];
  for (const field of SNAPSHOT_FIELDS) el(field).value = saved.fields[field];
  el("simpleAcknowledged").checked = saved.acknowledged;
  state.guided.step = saved.guidedStep;
  state.guided.excludedTeeth = saved.excludedTeeth;
  state.segmentation = saved.segmentation;
  state.proximity = saved.proximity;
  state.manualEdit = saved.manualEdit;
  state.sample.active = false;
  saved = null;
}
