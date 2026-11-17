// Transfer draft colors only onto exact retained H6 face records; never restore removed faces.
import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { readRepairBundle } from "../ui/surface_repair_bundle.js";
import { meshHash } from "../ui/surface_repair_mesh.js";
import { RegionEdits } from "../ui/region_edits.js";

const H6_HASH = "3b6667103e8262750afe58f569938fe5acf8265f3f050995dd45a3b6a3a49208";

export function retainedLabels(original, seed, edited, retainedCount, existing) {
  const faces = new Map();
  for (let i = 0; i < seed.length; i++) {
    const key = original.subarray(84 + i * 50, 134 + i * 50).toString("base64");
    faces.set(key, faces.has(key) && faces.get(key) !== seed[i] ? 0 : seed[i]);
  }
  const result = new Uint8Array(existing);
  for (let i = 0; i < retainedCount; i++) {
    const key = edited.subarray(84 + i * 50, 134 + i * 50).toString("base64");
    if (!faces.has(key)) throw new Error(`Retained face ${i} does not match original H6 bytes.`);
    if (!result[i]) result[i] = faces.get(key);
  }
  return result;
}

export async function paintBundle(bundle, original, correction) {
  const source = original.buffer.slice(original.byteOffset, original.byteOffset + original.byteLength);
  if (await meshHash(source) !== H6_HASH) throw new Error("Expected the exact original H6 scan.");
  const count = original.readUInt32LE(80);
  if (original.length !== 84 + count * 50) throw new Error("Invalid original STL length.");
  if (correction.reviewed !== false || correction.provenance !== "automatic-draft") throw new Error("Expected an unreviewed seed.");
  const seed = RegionEdits.restore(correction, H6_HASH, count, "lower");
  const { scan, edits } = await readRepairBundle(bundle);
  if (scan.arch !== "lower" || scan.repair.sourceSha256 !== H6_HASH) throw new Error("Bundle is not an edited H6 copy.");
  const result = retainedLabels(original, seed.labels, Buffer.from(scan.bytes), scan.repair.originalFaceCount, edits.labels);
  const next = new RegionEdits(result, "lower");
  next.provenance = "automatic-draft";
  const note = "AUTOMATIC DRAFT: H4-derived H6 tooth colors matched to exact retained faces of this cleaned copy. All geometry, six-trim history and existing nonzero labels preserved. Check every number and boundary, especially suspected model chip FDI 32, partial FDI 41 coverage and protruding H6 material. Physical model reported unchanged between captures. JMStudio export units reported as mm; exact-file calibration unverified. No missing surfaces reconstructed.";
  const output = { ...bundle, labels: next.export(scan.sha256, false), notes: [bundle.notes, note].filter(Boolean).join("\n\n") };
  await readRepairBundle(output);
  return { output, report: { source_sha256: H6_HASH, edited_sha256: scan.sha256,
    face_count: result.length, trim_count: scan.repair.trims?.length || 0,
    retained_original_faces: scan.repair.originalFaceCount,
    existing_labeled_faces: edits.labels.reduce((n, id) => n + Number(id !== 0), 0),
    labeled_faces: result.reduce((n, id) => n + Number(id !== 0), 0),
    tooth_ids: [...new Set(result)].filter(Boolean).sort((a,b) => a-b),
    geometry_bytes_unchanged: output.stlBase64 === bundle.stlBase64,
    repair_history_unchanged: JSON.stringify(output.scan) === JSON.stringify(bundle.scan),
    reviewed: false } };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [bundlePath, stlPath, correctionPath, outputPath] = process.argv.slice(2);
  if (!outputPath) throw new Error("Usage: node tools/paint_edited_h6.mjs edited-bundle original-h6.stl seed.json NEW-output.json");
  const { output, report } = await paintBundle(JSON.parse(await readFile(bundlePath, "utf8")),
    await readFile(stlPath), JSON.parse(await readFile(correctionPath, "utf8")));
  await writeFile(outputPath, JSON.stringify(output), { flag: "wx" });
  console.log(JSON.stringify(report, null, 2));
}
