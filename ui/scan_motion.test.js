import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "./vendor/three.module.js";
import { validateMotionPreview } from "./scan_motion_data.js";
import { createMotionSurfaces, motionPose, viewerRegistration } from "./scan_motion_geometry.js";
import { historyFrame } from "./scan_history.js";

const root = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/", import.meta.url);
function fixture(arch = "upper") {
  const preview = JSON.parse(readFileSync(new URL(`derived/progress-01-motion-${arch}.json`, root)));
  const pair = preview.sources.map((source, i) => {
    const bytes = new ArrayBuffer(84 + 50 * (i ? preview.target_face_count : preview.source_face_count));
    new DataView(bytes).setUint32(80, i ? preview.target_face_count : preview.source_face_count, true);
    return { ...source, arch, bytes };
  });
  return { preview, pair };
}

test("real motion artifacts bind both endpoints, source face identities, and draft status", () => {
  for (const arch of ["upper", "lower"]) {
    const { preview, pair } = fixture(arch);
    const motion = validateMotionPreview(preview, pair);
    assert.equal(motion.faceLabels.length, preview.source_face_count);
    for (let week = 2; week <= 6; week++) {
      const frame = historyFrame(week, pair, motion);
      assert.equal(frame.kind, "estimated");
      assert.equal(frame.index, 2);
      assert.equal(frame.fraction, (week - 1) / 6);
      assert.equal(frame.scan, null);
    }
    assert.equal(historyFrame(7, pair, motion).kind, "observed");
    assert.equal(historyFrame(7, pair, motion, true).kind, "estimated");
    assert.equal(historyFrame(1, pair, motion).scan, pair[0]);
  }
});

test("corrupt, mismatched, mirrored, or promoted estimates are rejected", () => {
  for (const corrupt of [
    p => { p.sources[0].sha256 = "0".repeat(64); },
    p => { p.frame = "another-frame"; },
    p => { p.arch = "lower"; },
    p => { p.target_to_source[0][0] *= -1; },
    p => { p.teeth[0].translation[0] = Infinity; },
    p => { p.teeth[0].quaternion_xyzw = [0, 0, 0, 0]; },
    p => { p.teeth[0].reviewed = true; },
    p => { p.teeth[1].face_label = p.teeth[0].face_label; },
    p => { p.moving_face_labels_base64 = "AA=="; },
    p => { p.units = "mm"; },
  ]) {
    const { preview, pair } = fixture();
    corrupt(preview);
    assert.throws(() => validateMotionPreview(preview, pair), /does not match/);
  }
});

test("pose interpolation has exact endpoints, half translation and half rotation", () => {
  const tooth = { pivot: [3, 4, 5], translation: [0.6, -0.4, 0.2],
    quaternion_xyzw: [0, 0, Math.sin(Math.PI / 12), Math.cos(Math.PI / 12)] };
  const first = motionPose(tooth, 0), middle = motionPose(tooth, 0.5), last = motionPose(tooth, 1);
  assert.ok(first.position.distanceTo(new THREE.Vector3(3, 5, -4)) < 1e-10);
  assert.ok(last.position.distanceTo(new THREE.Vector3(3.6, 5.2, -3.6)) < 1e-10);
  assert.ok(middle.position.distanceTo(first.position.clone().lerp(last.position, 0.5)) < 1e-10);
  assert.ok(Math.abs(first.quaternion.angleTo(last.quaternion) - Math.PI / 6) < 1e-10);
  assert.ok(Math.abs(first.quaternion.angleTo(middle.quaternion) - Math.PI / 12) < 1e-10);
  // A rigid pose preserves crown dimensions at every simulated week.
  for (let week = 1; week <= 7; week++) {
    const q = motionPose(tooth, (week - 1) / 6).quaternion;
    const a = new THREE.Vector3(1, 2, 3).applyQuaternion(q);
    const b = new THREE.Vector3(4, 5, 6).applyQuaternion(q);
    assert.ok(Math.abs(a.distanceTo(b) - Math.sqrt(27)) < 1e-10);
  }
});

test("registration changes basis once and preserves translation and handedness", () => {
  const matrix = viewerRegistration([[0, -1, 0, 2], [1, 0, 0, 3], [0, 0, 1, 4], [0, 0, 0, 1]]);
  // Source [1,2,3] -> [-2+2,1+3,3+4] -> viewer [0,7,-4].
  const p = new THREE.Vector3(1, 3, -2).applyMatrix4(matrix);
  assert.ok(p.distanceTo(new THREE.Vector3(0, 7, -4)) < 1e-10);
  assert.ok(Math.abs(matrix.determinant() - 1) < 1e-10);
});

test("simulation partitions original faces exactly and keeps context stationary", () => {
  const geometry = new THREE.BufferGeometry();
  const original = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 0, 0, 3, 0, 0, 2, 1, 0]);
  geometry.setAttribute("position", new THREE.BufferAttribute(original.slice(), 3));
  geometry.computeVertexNormals();
  const tooth = { tooth: "11", face_label: 1, pivot: [2, 0, 0], translation: [0.6, 0, 0], quaternion_xyzw: [0, 0, 0, 1] };
  const material = new THREE.MeshStandardMaterial();
  const motion = createMotionSurfaces(geometry, { teeth: [tooth], faceLabels: new Uint8Array([0, 1]) }, material);
  assert.equal(motion.group.children.reduce((sum, mesh) => sum + mesh.geometry.attributes.position.count, 0), 6);
  const context = motion.group.children[0].geometry.attributes.position.array.slice();
  motion.setFraction(0.5);
  assert.ok(Math.abs(motion.center("11").x - 2.3) < 1e-10);
  assert.deepEqual(motion.group.children[0].geometry.attributes.position.array, context);
  assert.deepEqual(geometry.attributes.position.array, original);
  motion.dispose(); geometry.dispose(); material.dispose();
});
