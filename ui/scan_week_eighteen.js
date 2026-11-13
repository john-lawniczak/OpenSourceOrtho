import { sampleAssetUrl, sampleDataset } from "./sample-dataset.js";

// Painting entry points use the selected working surfaces; observations keep originals.
export function suggestedPaintingCapture(arch, visit) {
  return visit === "progress-02" ? (arch === "upper" ? "upper-clean" : "fusion-h-4") : "original";
}

export function weekEighteenCapture(arch, capture = "original") {
  const alternatives = { upper: ["upper-clean"], lower: ["fusion-h-4", "fusion-h-6"] };
  if (!alternatives[arch] || (capture !== "original" && !alternatives[arch].includes(capture))) throw new Error("Invalid week 18 capture.");
  if (capture === "upper-clean") return { folder: "visits/progress-02/captures/upper-clean", filename: "progress-02-upper-clean.stl" };
  return capture === "original" ? { folder: "visits/progress-02", filename: `progress-02-${arch}.stl` }
    : { folder: `visits/progress-02/captures/${capture}`, filename: `2026-11-12_USER_ONE_lower_week-18_${capture}.stl` };
}

export function weekEighteenMetadata(manifest, source, arch, capture = "original") {
  const { folder, filename } = weekEighteenCapture(arch, capture);
  if (!["upper", "lower"].includes(arch) || manifest.specimen_id !== sampleDataset.specimenId
      || source.specimen_id !== sampleDataset.specimenId || source.reported_week !== 18
      || source.progress_record_id !== "progress-02" || (capture !== "original" && source.capture_id !== capture)) throw new Error("Week 18 provenance is inconsistent.");
  const scan = manifest.scans.find(s => s.filename === filename);
  const record = source.surfaces.find(s => s.repo_filename === filename);
  if (!scan || !record || !/^[a-f0-9]{64}$/.test(scan.sha256) || scan.sha256 !== record.sha256
      || scan.role !== "progress" || scan.sequence_index !== 2
      || scan.arch !== (arch === "upper" ? "maxillary" : "mandibular") || scan.arch !== record.arch) {
    throw new Error("Week 18 scan identity is inconsistent.");
  }
  return { arch, capture, filename: `${folder}/${filename}`, sha256: scan.sha256, units: scan.units,
    // Inspection-only painting camera in comparisonGeometry's display frame.
    // These model scans use different axes from the earlier intraoral exports.
    paintingFront: { direction: [0, 1, 0], up: [0, 0, -1] },
    // Display-only scanner-axis assumption, not a fitted cross-visit transform.
    rotation: [1, -1, -1], date: source.scan_acquisition?.date || "Acquisition date unknown",
    label: "Reported week 18", validation: null };
}

export async function loadWeekEighteenScan(arch, { signal, capture = "original" } = {}) {
  const { folder } = weekEighteenCapture(arch, capture);
  async function get(path, binary = false) {
    const response = await fetch(sampleAssetUrl(path), { signal });
    if (!response.ok) throw new Error(`Week 18 scan unavailable (HTTP ${response.status}).`);
    return binary ? response.arrayBuffer() : response.json();
  }
  const [manifest, source] = await Promise.all(["manifest.json", "source-metadata.json"]
    .map(name => get(`${folder}/${name}`)));
  const scan = weekEighteenMetadata(manifest, source, arch, capture);
  const bytes = await get(scan.filename, true);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
  if (hex !== scan.sha256) throw new Error("Week 18 scan integrity check failed.");
  return { ...scan, bytes };
}
