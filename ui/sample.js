// Sample test case: an isolated, self-contained demonstration that reuses the
// real guided wizard UI (same step chips: upload -> teeth & time -> details ->
// review -> 3D preview -> print) so a viewer sees exactly what a guided user
// sees, pre-filled with demo data. Opening it snapshots the user's working state
// and restores it on exit, so nothing the sample does leaks into the user's own
// plan, uploads, or editors.
//
// The demo uses bundled demo crowns in OVERLAY view (a static "before" ghost
// plus a moving "planned" set) so dragging the stage slider visibly animates the
// teeth from crowded toward aligned across stages 0-3.

import { el, state } from "./state.js";
import { demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";

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
  };
  for (const key of SNAPSHOT_STATE_KEYS) saved.state[key] = state[key];
  for (const field of SNAPSHOT_FIELDS) saved.fields[field] = el(field).value;

  // Isolated demo plan: simulated crowding correction over 4 stages (0 = the
  // crowded starting point), rendered with bundled demo crowns - no patient scan
  // - so the movement is the obvious, dominant thing on screen.
  state.rows = syntheticCrowdingRows(4, { includeBaseline: true });
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = true;
  state.files = [];
  state.file = null;
  state.scanSources = [];
  state.scanArchFilter = "both";
  state.view = "overlay";
  state.dim = "3d";
  state.simpleGoal = "crowding";
  // Reuse the guided wizard (not a separate screen) so the sample shows the same
  // step chips and panels; the sample flag drives the banner and isolation.
  state.userMode = "simple";
  state.sample.active = true;
  state.guided.step = "preview";
  state.simpleAcknowledged = true;
  state.sampleStatus =
    "A simulated sample so you can see how a plan animates. Not a real patient and not a medical device.";
  el("planTitle").value = "Sample test case";
  el("planId").value = "sample-test-case";
  el("wearInterval").value = "14";
  el("exaggeration").value = "16";
  el("simpleAcknowledged").checked = true;
}

export function exitSample() {
  if (!saved) return;
  for (const key of SNAPSHOT_STATE_KEYS) state[key] = saved.state[key];
  for (const field of SNAPSHOT_FIELDS) el(field).value = saved.fields[field];
  el("simpleAcknowledged").checked = saved.acknowledged;
  state.guided.step = saved.guidedStep;
  state.sample.active = false;
  saved = null;
}
