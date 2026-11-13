// Resolve documented scanner conventions by content hash, never by filename.
// Unknown STL axes remain a view heuristic; no source coordinates are rewritten.
import { sampleAssetUrl } from "./sample-dataset.js";
import { scanFrontPose } from "./scan_view_pose.js";

let catalog;
async function orientations() {
  if (!catalog) catalog = Promise.all(["manifest.json", "derived/progress-01-comparison.json"].map(async name => {
    const response = await fetch(sampleAssetUrl(name));
    if (!response.ok) throw new Error("Orientation catalog unavailable");
    return response.json();
  })).catch(() => { catalog = null; return null; });
  return catalog;
}

export async function sourceRotation(sha256, arch) {
  const records = await orientations();
  const scan = records?.[0].scans.find(item => item.sha256 === sha256
    && item.arch === (arch === "upper" ? "maxillary" : "mandibular"));
  const rotation = records?.[1].display.rotation_diagonals[scan?.filename];
  return Array.isArray(rotation) && rotation.length === 3 && rotation.every(v => v === 1 || v === -1)
    && rotation.reduce((a, b) => a * b, 1) === 1 ? rotation : [1, 1, 1];
}

export async function sourceViewContext(bytes, arch) {
  if (!["upper", "lower"].includes(arch)) return {};
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const sha256 = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
  const rotation = await sourceRotation(sha256, arch);
  return { arch, front: scanFrontPose(arch, rotation) };
}

export function visibleScanView(meshes) {
  if (meshes.length === 1) return meshes[0].userData.scanView || {};
  // Multiple arches must open from the front, never the bounding box's thin axis.
  return meshes.length > 1 ? { front: { direction: [0,0,1], up: [0,1,0] } } : {};
}
