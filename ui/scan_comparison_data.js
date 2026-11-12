// Original endpoint provenance. Motion estimates are loaded separately; no private visit discovery.
import { sampleAssetUrl, sampleDataset } from "./sample-dataset.js";

export function inputValidationText(validation) {
  return validation?.status === "contributor-confirmed"
    && validation.cross_visit_alignment === "validated" && validation.tooth_correspondence === "validated"
    ? "Week 1–7 cross-visit alignment and tooth correspondence: validated, confirmed by the contributor."
    : "No contributor-confirmed alignment and tooth-correspondence record is linked to this pair.";
}

export function observedPairMetadata(manifest, timeline, comparison, arch) {
  if (!["upper", "lower"].includes(arch)) throw new Error("Choose an upper or lower arch.");
  if ([manifest, timeline, comparison].some(record => record.specimen_id !== sampleDataset.specimenId)) {
    throw new Error("The scan records do not belong to the sample case.");
  }
  return ["initial", "progress-01"].map((visit, index) => {
    const filename = `${visit}-${arch}.stl`;
    const scan = manifest.scans.find(item => item.filename === filename);
    const event = timeline.events.find(item => item.event_id === visit);
    const inventory = comparison.scans.find(item => item.filename === filename);
    const rotation = comparison.display.rotation_diagonals[filename];
    if (!scan || !inventory || !event?.files?.includes(filename)
        || scan.sha256 !== inventory.sha256 || !/^[a-f0-9]{64}$/.test(scan.sha256)
        || scan.role !== (index ? "progress" : "initial")
        || (index && scan.sequence_index !== 1)
        || scan.arch !== (arch === "upper" ? "maxillary" : "mandibular")) {
      throw new Error("The observed scan provenance is inconsistent.");
    }
    if (!Array.isArray(rotation) || rotation.length !== 3
        || rotation.some(value => ![-1, 1].includes(value))
        || rotation.reduce((a, b) => a * b, 1) !== 1) {
      throw new Error("The documented display orientation is unavailable.");
    }
    const validation = timeline.comparison?.input_validation;
    const boundValidation = validation?.scans?.[filename] === scan.sha256 ? validation : null;
    return { arch, filename, sha256: scan.sha256, units: scan.units, rotation, validation: boundValidation,
      date: event.date, label: index ? `Reported week ${event.reported_week}`
        : event.reported_week === 1 ? "Week 1 / baseline" : "Pretreatment baseline" };
  });
}

async function fetchAsset(filename, signal, binary = false) {
  const response = await fetch(sampleAssetUrl(filename), { signal });
  if (!response.ok) throw new Error(`Could not load ${filename} (HTTP ${response.status}).`);
  return binary ? response.arrayBuffer() : response.json();
}

export async function loadObservedPair(arch, { signal } = {}) {
  const records = await Promise.all(["manifest.json", "longitudinal-record.json", "derived/progress-01-comparison.json"]
    .map(filename => fetchAsset(filename, signal)));
  const scans = observedPairMetadata(...records, arch);
  return Promise.all(scans.map(async scan => {
    const bytes = await fetchAsset(scan.filename, signal, true);
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    const hex = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("");
    if (hex !== scan.sha256) throw new Error(`The integrity check failed for ${scan.filename}.`);
    return { ...scan, bytes };
  }));
}
