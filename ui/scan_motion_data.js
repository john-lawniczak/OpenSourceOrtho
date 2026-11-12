import { parseStlGeometry } from "./stl.js";
import { sampleAssetUrl, sampleDataset } from "./sample-dataset.js";

const finiteVector = (v, length) => Array.isArray(v) && v.length === length && v.every(Number.isFinite);

export function validateMotionPreview(preview, pair, { specimenId = sampleDataset.specimenId } = {}) {
  const fail = () => { throw new Error("The endpoint motion preview does not match these scans."); };
  if (preview?.schema !== "opensource-ortho-endpoint-motion-preview-v1"
      || preview.specimen_id !== specimenId || preview.arch !== pair[0].arch
      || preview.status !== "estimated-unreviewed"
      || preview.frame !== "display-oriented-bbox-centered-source-xyz"
      || preview.units !== "source-coordinate-units-unverified"
      || preview.interpolation !== "linear-pivot-translation-and-shortest-quaternion-slerp"
      || JSON.stringify(preview.weeks) !== "[1,7]" || preview.sources?.length !== 2) fail();
  pair.forEach((scan, i) => {
    const source = preview.sources[i];
    if (source.filename !== scan.filename || source.sha256 !== scan.sha256
        || JSON.stringify(source.rotation) !== JSON.stringify(scan.rotation)) fail();
  });
  const matrix = preview.target_to_source;
  if (!Array.isArray(matrix) || matrix.length !== 4 || !matrix.every(row => finiteVector(row, 4))
      || JSON.stringify(matrix[3]) !== "[0,0,0,1]") fail();
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
    const dot = matrix[i].slice(0, 3).reduce((sum, value, k) => sum + value * matrix[j][k], 0);
    if (Math.abs(dot - Number(i === j)) > 1e-5) fail();
  }
  const [a, b, c] = matrix;
  const determinant = a[0] * (b[1] * c[2] - b[2] * c[1])
    - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0]);
  if (Math.abs(determinant - 1) > 1e-5) fail();
  const counts = pair.map(scan => {
    if (scan.bytes.byteLength >= 84) {
      const count = new DataView(scan.bytes).getUint32(80, true);
      if (scan.bytes.byteLength === 84 + count * 50) return count;
    }
    const geometry = parseStlGeometry(scan.bytes), count = geometry.attributes.position.count / 3;
    geometry.dispose(); return count;
  });
  if (preview.source_face_count !== counts[0] || preview.target_face_count !== counts[1]) fail();
  if (!Array.isArray(preview.teeth) || !preview.teeth.length || preview.teeth.length > 32) fail();
  const toothIds = new Set(), labels = new Set(), targets = new Set();
  for (const tooth of preview.teeth) {
    const archPattern = preview.arch === "upper" ? /^[12][1-8]$/ : /^[34][1-8]$/;
    if (!archPattern.test(tooth.tooth) || toothIds.has(tooth.tooth) || tooth.reviewed !== false
        || !Number.isInteger(tooth.face_label) || tooth.face_label < 1 || tooth.face_label > 32
        || labels.has(tooth.face_label) || !finiteVector(tooth.pivot, 3)
        || !finiteVector(tooth.translation, 3) || !finiteVector(tooth.quaternion_xyzw, 4)
        || Math.abs(Math.hypot(...tooth.quaternion_xyzw) - 1) > 1e-5
        || !["estimated-draft", "estimated-weak", "held-unmatched"].includes(tooth.status)) fail();
    if (tooth.target_tooth !== null) {
      if (!archPattern.test(tooth.target_tooth) || targets.has(tooth.target_tooth)) fail();
      targets.add(tooth.target_tooth);
    }
    if (tooth.fit && !["median_residual", "p90_residual", "relative_p90", "overlap"]
      .every(key => Number.isFinite(tooth.fit[key]) && tooth.fit[key] >= 0)) fail();
    if (tooth.status.startsWith("estimated") && (!tooth.fit || !tooth.target_tooth)) fail();
    if (tooth.status === "held-unmatched" && (Math.hypot(...tooth.translation) > 0
      || JSON.stringify(tooth.quaternion_xyzw) !== "[0,0,0,1]")) fail();
    toothIds.add(tooth.tooth); labels.add(tooth.face_label);
  }
  if (typeof preview.moving_face_labels_base64 !== "string"
      || preview.moving_face_labels_base64.length > Math.ceil(counts[0] / 3) * 4) fail();
  const decoded = Uint8Array.from(atob(preview.moving_face_labels_base64), char => char.charCodeAt(0));
  if (decoded.length !== counts[0] || decoded.some(label => label !== 0 && !labels.has(label))) fail();
  return { ...preview, faceLabels: decoded };
}

export async function loadMotionPreview(pair, { signal } = {}) {
  const response = await fetch(sampleAssetUrl(`derived/progress-01-motion-${pair[0].arch}.json`), { signal });
  if (!response.ok) throw new Error(`Could not load motion estimates (HTTP ${response.status}).`);
  return validateMotionPreview(await response.json(), pair);
}
