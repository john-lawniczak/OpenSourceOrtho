// Persist working inputs, not credentials, pending model requests or transient previews.
const KEYS = ["rows", "files", "file", "scanDates", "scanSources", "caseRecords", "fixtureMeshAssets",
  "registrations", "derivedAnatomy", "scanUnits", "scanArch", "scanArchFilter", "availability",
  "caps", "clinicalControls", "printExport", "simpleGoal", "simpleAcknowledged", "manualEdit",
  "userMode", "activeStep", "returnStep", "view", "dim", "showToothLabels", "showScale"];
const FIELDS = ["planTitle", "planId", "wearInterval", "exaggeration", "scanUnits", "scanArch", "simpleGoal",
  "capLinear", "capAngular", "capRotation", "capVertical", "fixedTeeth", "attachmentTeeth", "movementExclusions",
  "generationNotes", "printEmail", "segmentMissingTeeth", "printFormat", "modelMaterial", "thermoformingMaterial",
  "sheetThickness", "trimMargin", "versionNote"];
const CHECKS = ["simpleAcknowledged", "generationAck", "printEnabled", "printSafety", "alignerShellEnabled"];

export function captureWorkspace(state, document) {
  if (state.sample.active || state.goalPreview || state.goalBusy) return null;
  const values = Object.fromEntries(KEYS.filter(key => state[key] !== undefined).map(key => [key, state[key]]));
  values.guided = { step: state.guided.step, excludedTeeth: state.guided.excludedTeeth };
  values.segmentation = Object.fromEntries(["proposal", "edits", "applied", "missingTeeth"].map(key => [key, state.segmentation[key]]));
  values.generation = { notes: state.generation.notes, landmarks: state.generation.landmarks, landmarksStatus: state.generation.landmarksStatus };
  return structuredClone({ schema: 1, values,
    fields: Object.fromEntries(FIELDS.map(id => [id, document.getElementById(id)?.value || ""])),
    checks: Object.fromEntries(CHECKS.map(id => [id, Boolean(document.getElementById(id)?.checked)])) });
}
export function restoreWorkspace(record, state, document) {
  if (!record || record.schema !== 1 || !record.values || !record.fields || !record.checks) throw new Error("Saved profile progress is not supported. It has not been replaced.");
  for (const key of KEYS) if (record.values[key] !== undefined) state[key] = record.values[key];
  for (const key of ["guided", "segmentation", "generation"]) Object.assign(state[key], record.values[key]);
  for (const id of FIELDS) if (document.getElementById(id)) document.getElementById(id).value = record.fields[id] ?? "";
  for (const id of CHECKS) if (document.getElementById(id)) document.getElementById(id).checked = record.checks[id] === true;
  state.sample = { active: false };
}
