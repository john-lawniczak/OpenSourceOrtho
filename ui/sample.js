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
// The 3D preview shows the real STL scans (static) in OVERLAY view with a planned
// movement layer animating crowded -> aligned across stages as the slider drags;
// per-tooth movement over a whole-arch shell is necessarily schematic.

import { el, state } from "./state.js";
import { canonicalScanSources, demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";

// State keys the sample overwrites and therefore must save/restore.
const SNAPSHOT_STATE_KEYS = [
  "rows", "files", "file", "scanSources", "useDemoMeshes", "demoInitialOffsets",
  "view", "activeStep", "userMode", "scanArchFilter", "simpleGoal",
  "simpleAcknowledged", "dim", "sampleStatus", "scanRenderStatus",
];
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
  };
  for (const key of SNAPSHOT_STATE_KEYS) saved.state[key] = state[key];
  for (const field of SNAPSHOT_FIELDS) saved.fields[field] = el(field).value;
  state.segmentation = { busy: false, status: "", proposal: null, edits: {}, applied: null };
  state.proximity = { enabled: false, busy: false, status: "", map: null, registration: null };

  // Isolated walkthrough plan: a simulated crowding correction over 4 stages
  // (0 = the starting point), paired with the two real test-case STL scans so the
  // 3D preview renders the exact bundled models, not bundled placeholder crowns.
  state.rows = syntheticCrowdingRows(4, { includeBaseline: true });
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = false;
  state.scanSources = canonicalScanSources;
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
    "A simulated walkthrough so you can see how a plan animates. Not a real patient and not a medical device.";
  el("planTitle").value = "Sample test case";
  el("planId").value = "sample-test-case";
  el("wearInterval").value = "10";
  el("exaggeration").value = "16";
  el("simpleAcknowledged").checked = true;
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
  state.sample.active = false;
  saved = null;
}
