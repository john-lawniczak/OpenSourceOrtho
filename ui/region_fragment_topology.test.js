import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { manifoldFacePairs, disconnectedPatches } from "./region_fragment_topology.js";

test("patches exclude context, vertex-only contacts and each label's largest region", () => {
  const positions = new Float32Array([
    0,0,0, 1,0,0, 1,1,0, 0,0,0, 1,1,0, 0,1,0,
    1,1,0, 2,1,0, 2,2,0, 5,0,0, 6,0,0, 5,1,0,
    7,0,0, 8,0,0, 7,1,0,
  ]);
  const labels = new Uint8Array([11,11,11,12,0]), before = labels.slice();
  assert.deepEqual(disconnectedPatches(labels, manifoldFacePairs(positions)), [{ label: 11, faces: [2] }]);
  assert.deepEqual(labels, before);
  assert.deepEqual(disconnectedPatches(new Uint8Array(5), manifoldFacePairs(positions)), []);
});

test("nonmanifold edges do not join regions; equal-size ties keep the first component", () => {
  const positions = new Float32Array([
    0,0,0, 1,0,0, 0,1,0, 0,0,0, 1,0,0, 0,-1,0,
    0,0,0, 1,0,0, 0,0,1,
  ]);
  assert.equal(manifoldFacePairs(positions).length, 0);
  assert.deepEqual(disconnectedPatches([21,21,21], manifoldFacePairs(positions)), [
    { label: 21, faces: [1] }, { label: 21, faces: [2] },
  ]);
});

test("saved USER_ONE upper patches match the 116 right / 144 left source audit", () => {
  const base = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/", import.meta.url);
  const raw = readFileSync(new URL("initial-upper.stl", base));
  const record = JSON.parse(readFileSync(new URL("annotations/initial-upper-painted-2026-11-12T184456Z.json", base)));
  const report = JSON.parse(readFileSync(new URL("annotations/initial-upper-painted-2026-11-12T184456Z-report.json", base)));
  const positions = new Float32Array(record.face_count * 9);
  for (let face = 0; face < record.face_count; face++) for (let i = 0; i < 9; i++) positions[face * 9 + i] = raw.readFloatLE(84 + face * 50 + 12 + i * 4);
  const labels = new Uint8Array(Buffer.from(record.labels_base64, "base64"));
  const groups = disconnectedPatches(labels, manifoldFacePairs(positions));
  for (const tooth of report.teeth) {
    const patches = groups.filter(g => g.label === tooth.fdi);
    assert.equal(patches.length, tooth.connected_components - 1);
    assert.equal(patches.reduce((n, g) => n + g.faces.length, 0), tooth.faces_outside_largest_component);
  }
  assert.equal(groups.filter(g => g.label < 20).reduce((n, g) => n + g.faces.length, 0), 116);
  assert.equal(groups.filter(g => g.label > 20).reduce((n, g) => n + g.faces.length, 0), 144);
});
