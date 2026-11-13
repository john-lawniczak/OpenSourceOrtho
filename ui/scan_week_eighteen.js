import { sampleAssetUrl, sampleDataset } from "./sample-dataset.js";

export function weekEighteenMetadata(manifest, source, arch) {
  if (!["upper", "lower"].includes(arch) || manifest.specimen_id !== sampleDataset.specimenId
      || source.specimen_id !== sampleDataset.specimenId || source.reported_week !== 18
      || source.progress_record_id !== "progress-02") throw new Error("Week 18 provenance is inconsistent.");
  const filename = `progress-02-${arch}.stl`;
  const scan = manifest.scans.find(s => s.filename === filename);
  const record = source.surfaces.find(s => s.repo_filename === filename);
  if (!scan || !record || !/^[a-f0-9]{64}$/.test(scan.sha256) || scan.sha256 !== record.sha256
      || scan.role !== "progress" || scan.sequence_index !== 2
      || scan.arch !== (arch === "upper" ? "maxillary" : "mandibular") || scan.arch !== record.arch) {
    throw new Error("Week 18 scan identity is inconsistent.");
  }
  return { arch, filename: `visits/progress-02/${filename}`, sha256: scan.sha256, units: scan.units,
    // Display-only scanner-axis assumption, not a fitted cross-visit transform.
    rotation: [1, -1, -1], date: source.scan_acquisition?.date || "Acquisition date unknown",
    label: "Reported week 18", validation: null };
}

export async function loadWeekEighteenScan(arch, { signal } = {}) {
  async function get(path, binary = false) {
    const response = await fetch(sampleAssetUrl(path), { signal });
    if (!response.ok) throw new Error(`Week 18 scan unavailable (HTTP ${response.status}).`);
    return binary ? response.arrayBuffer() : response.json();
  }
  const [manifest, source] = await Promise.all(["manifest.json", "source-metadata.json"]
    .map(name => get(`visits/progress-02/${name}`)));
  const scan = weekEighteenMetadata(manifest, source, arch);
  const bytes = await get(scan.filename, true);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
  if (hex !== scan.sha256) throw new Error("Week 18 scan integrity check failed.");
  return { ...scan, bytes };
}
