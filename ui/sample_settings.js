// The sample must neither inherit personal controls nor write them back on exit.
import { el, state } from "./state.js";

const DEFAULT_FIELDS = {
  capLinear: "0.25", capAngular: "1", capRotation: "2", capVertical: "0.1",
  fixedTeeth: "", attachmentTeeth: "", movementExclusions: "", generationNotes: "",
  printEmail: "", segmentMissingTeeth: "", scanArch: "",
};
const CHECKBOXES = ["printEnabled", "printSafety", "alignerShellEnabled", "generationAck"];
const EXTRA_FIELDS = ["printFormat", "modelMaterial", "thermoformingMaterial", "sheetThickness", "trimMargin"];
const STATE_KEYS = ["caps", "clinicalControls", "printExport", "generation"];

export function isolateSampleSettings() {
  const fields = Object.fromEntries([...Object.keys(DEFAULT_FIELDS), ...EXTRA_FIELDS].map(id => [id, el(id).value]));
  const checks = Object.fromEntries(CHECKBOXES.map(id => [id, el(id).checked]));
  const values = Object.fromEntries(STATE_KEYS.map(key => [key, state[key]]));
  for (const [id, value] of Object.entries(DEFAULT_FIELDS)) el(id).value = value;
  for (const id of CHECKBOXES) el(id).checked = false;
  state.clinicalControls = { fixedTeeth: "", attachmentTeeth: "", movementExclusions: "", iprContacts: {} };
  state.generation = { busy: false, status: "", acknowledged: false, notes: "", landmarks: null, landmarksStatus: "", result: null };
  state.printExport = { ...state.printExport, delivery_email: "", enabled: false, safety_acknowledged: false, aligner_shell_enabled: false };
  return () => {
    for (const [id, value] of Object.entries(fields)) el(id).value = value;
    for (const [id, checked] of Object.entries(checks)) el(id).checked = checked;
    Object.assign(state, values);
  };
}
