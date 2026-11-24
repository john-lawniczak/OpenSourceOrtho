import { sampleAssetUrl, sampleDataset } from "./sample-dataset.js";

export const weekTwentyOneFolder = "visits/progress-03";

export function weekTwentyOneMetadata(manifest, source, arch) {
  if (!["upper", "lower"].includes(arch) || manifest.specimen_id !== sampleDataset.specimenId
      || source.specimen_id !== sampleDataset.specimenId || source.reported_week !== 21
      || source.progress_record_id !== "progress-03" || source.coordinate_frame?.export_label !== "shell_occlusion") {
    throw new Error("Week 21 provenance is inconsistent.");
  }
  const scans = ["upper", "lower"].map(name => {
    const filename = `progress-03-${name}.stl`;
    const scan = manifest.scans.find(item => item.filename === filename);
    const record = source.surfaces.find(item => item.repo_filename === filename);
    if (!scan || !record || !/^[a-f0-9]{64}$/.test(scan.sha256) || scan.sha256 !== record.sha256
        || scan.arch !== (name === "upper" ? "maxillary" : "mandibular") || record.arch !== scan.arch
        || scan.role !== "progress" || scan.sequence_index !== 3
        || ![scan.bounds?.min_xyz, scan.bounds?.max_xyz].every(v => Array.isArray(v) && v.length === 3 && v.every(Number.isFinite))) {
      throw new Error("Week 21 scan identity is inconsistent.");
    }
    return scan;
  });
  const center = [0, 1, 2].map(axis => (Math.min(...scans.map(s => s.bounds.min_xyz[axis]))
    + Math.max(...scans.map(s => s.bounds.max_xyz[axis]))) / 2);
  const scan = scans[arch === "upper" ? 0 : 1];
  return { arch, capture: "original", filename: `${weekTwentyOneFolder}/${scan.filename}`,
    sha256: scan.sha256, units: scan.units, rotation: [1, 1, 1], reportedWeek: 21,
    preserveOcclusion: true, sharedFrameCenter: [center[0], center[2], -center[1]],
    paintingFront: { direction: [0, 0, 1], up: [0, 1, 0] },
    date: source.scan_acquisition.date, label: "Reported week 21", validation: null,
    surfaceDescription: `original intraoral ${arch}` };
}

export async function loadWeekTwentyOneScan(arch, { signal } = {}) {
  async function get(name, binary = false) {
    const response = await fetch(sampleAssetUrl(`${weekTwentyOneFolder}/${name}`), { signal });
    if (!response.ok) throw new Error(`Week 21 scan unavailable (HTTP ${response.status}).`);
    return binary ? response.arrayBuffer() : response.json();
  }
  const [manifest, source] = await Promise.all([get("manifest.json"), get("source-metadata.json")]);
  const scan = weekTwentyOneMetadata(manifest, source, arch);
  const bytes = await get(`progress-03-${arch}.stl`, true);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
  if (hex !== scan.sha256) throw new Error("Week 21 scan integrity check failed.");
  return { ...scan, bytes };
}
