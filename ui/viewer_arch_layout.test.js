import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "./vendor/three.module.js";
import { arrangeScanArches, archDisplayMatrix } from "./viewer_arch_layout.js";

test("week 7 display separates opposing arches and applies the same transform to painted crowns", () => {
  const meshes = ["upper", "lower"].map(arch => {
    const geometry = new THREE.BoxGeometry(60, 18, 50); geometry.translate(0, 9, 0);
    const mesh = new THREE.Mesh(geometry); mesh.userData = { arch, displayArchStack: true };
    return mesh;
  });
  const original = meshes.map(mesh => [...mesh.geometry.attributes.position.array]);
  arrangeScanArches(meshes);
  const boxes = meshes.map(mesh => new THREE.Box3().setFromObject(mesh));
  assert.ok(Math.abs(boxes[0].min.y - 1) < 1e-6);
  assert.ok(Math.abs(boxes[1].max.y + 1) < 1e-6);
  for (const [i, mesh] of meshes.entries()) {
    assert.deepEqual([...mesh.geometry.attributes.position.array], original[i]);
    const tip = new THREE.Vector3(0,18,0).applyMatrix4(archDisplayMatrix(meshes, mesh.userData.arch));
    const base = new THREE.Vector3(0,0,0).applyMatrix4(archDisplayMatrix(meshes, mesh.userData.arch));
    assert.equal(Math.sign(tip.y-base.y), i ? 1 : -1);
  }
});
