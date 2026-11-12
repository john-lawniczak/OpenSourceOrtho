import { assignmentEvidenceText } from "./assignment_evidence.js";

export function fitConsistencyText(tooth) {
  const identity = assignmentEvidenceText(tooth);
  const evidence=tooth?.fit?.consistency;
  if(!evidence || evidence.unavailable)return `${identity} Fit consistency checks unavailable.`.trim();
  return `${identity} Round-trip shift ${evidence.round_trip_shift.toFixed(3)} scan units / ${evidence.round_trip_rotation_deg.toFixed(2)}°. Resampling change ${evidence.sampling_shift.toFixed(3)} scan units / ${evidence.sampling_rotation_deg.toFixed(2)}°. These are consistency checks, not accuracy bounds.`.trim();
}
