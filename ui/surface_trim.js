import { binaryStl, meshHash, sourcePositions, validateRepair } from "./surface_repair_mesh.js";

// Keep original face order so labels and estimated ranges can be remapped exactly.
export async function trimSurface(scan, labels, selected, allowPainted = false) {
  if (scan.repair) validateRepair(scan, labels.length);
  const positions = sourcePositions(scan.bytes), count = positions.length / 9;
  if (labels.length !== count) throw new Error("Painting does not match this surface.");
  const removed = new Set(selected);
  if (!removed.size || [...removed].some(f => !Number.isInteger(f) || f < 0 || f >= count)) throw new Error("Brush the surface to remove first.");
  if (!allowPainted && [...removed].some(f => labels[f])) throw new Error("Painted teeth are protected. Clear the selection or explicitly allow removing painted surfaces.");
  if (removed.size === count) throw new Error("Cannot remove the entire scan.");
  if ((scan.repair?.trims?.length || 0) >= 100) throw new Error("This version already has 100 trims.");
  const parentFaces = Uint32Array.from({ length: count }, (_, i) => i).filter(i => !removed.has(i));
  const source = scan.bytes.byteLength === 84 + count * 50 && new DataView(scan.bytes).getUint32(80,true) === count ? scan.bytes : binaryStl(positions);
  const bytes = new ArrayBuffer(84 + parentFaces.length * 50), raw = new Uint8Array(bytes);
  raw.set(new Uint8Array(source, 0, 84)); new DataView(bytes).setUint32(80, parentFaces.length, true);
  parentFaces.forEach((old, i) => raw.set(new Uint8Array(source, 84 + old * 50, 50), 84 + i * 50));
  const retainedIn = (start, end) => parentFaces.reduce((n, f) => n + Number(f >= start && f < end), 0);
  const originalFaceCount = retainedIn(0, scan.repair?.originalFaceCount ?? count);
  let firstFace = originalFaceCount;
  const patches = (scan.repair?.patches || []).flatMap(p => {
    const faceCount = retainedIn(p.firstFace, p.firstFace + p.faceCount);
    const next = { ...p, firstFace, faceCount }; firstFace += faceCount;
    return faceCount ? [next] : [];
  });
  const repair = { ...scan.repair, schema: "ortho-surface-repair-v2",
    sourceSha256: scan.repair?.sourceSha256 || scan.sha256,
    sourceFilename: scan.repair?.sourceFilename || scan.filename,
    sourceVisit: scan.repair?.sourceVisit || scan.visit || null,
    sourceCapture: scan.repair?.sourceCapture || scan.capture || null,
    originalFaceCount, patches,
    trims: [...(scan.repair?.trims || []), { parentSha256: scan.sha256, parentFaceCount: count,
      removedFaceCount: removed.size, allowedPainted: allowPainted, createdAt: new Date().toISOString() }] };
  const { visit, capture, baseline, ...rest } = scan;
  const filename = `${repair.sourceFilename.split('/').at(-1).replace(/\.stl$/i, "")}-edited-${repair.patches.length}-${repair.trims.length}.stl`;
  const next = { ...rest, bytes, sha256: await meshHash(bytes), filename, repair };
  validateRepair(next, parentFaces.length);
  return { scan: next, labels: Uint8Array.from(parentFaces, f => labels[f]), parentFaces };
}

export function restoreSurfaceLabels(previous, currentLabels) {
  const labels = previous.labels.slice();
  // Preserve painting done after a geometry edit on faces which still exist.
  currentLabels.forEach((id, i) => {
    const parent = previous.parentFaces ? previous.parentFaces[i] : i;
    if (parent !== undefined && parent < labels.length) labels[parent] = id;
  });
  return labels;
}
