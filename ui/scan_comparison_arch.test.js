import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "./vendor/three.module.js";
import { arrangeComparisonArches } from "./scan_comparison_arch.js";

function arch(name) {
  const group = new THREE.Group();
  const meshes = [0, 1].map(() => new THREE.Mesh(new THREE.BoxGeometry(60, 18, 38)));
  meshes.forEach(mesh => { mesh.geometry.computeBoundingSphere(); group.add(mesh); });
  return { arch:name, group, meshes };
}

test("combined display keeps source vertices and movement scale intact", () => {
  const entries = [arch("upper"), arch("lower")];
  const before = entries.map(e => Array.from(e.meshes[0].geometry.attributes.position.array));
  assert.ok(Number.isFinite(arrangeComparisonArches(entries)));
  for (const [i, entry] of entries.entries()) {
    assert.deepEqual(Array.from(entry.meshes[0].geometry.attributes.position.array), before[i]);
    assert.ok(Math.abs(entry.group.matrixWorld.determinant()-1) < 1e-12);
    const start = new THREE.Vector3(2, 3, 4), delta = new THREE.Vector3(.1, -.2, .3);
    const a = entry.group.localToWorld(start.clone());
    const b = entry.group.localToWorld(start.clone().add(delta));
    assert.ok(Math.abs(a.distanceTo(b)-delta.length()) < 1e-12);
  }
  const upper = new THREE.Box3().setFromObject(entries[0].meshes[0]);
  const lower = new THREE.Box3().setFromObject(entries[1].meshes[0]);
  assert.ok(upper.min.y > lower.max.y, "Crowns share the scene with upper above lower");
  const upperCrownDirection = new THREE.Vector3(0, 1, 0).transformDirection(entries[0].group.matrixWorld);
  assert.ok(upperCrownDirection.y < -.999, "Upper crowns point down");
  entries.forEach(e => e.meshes.forEach(m => { m.geometry.dispose(); m.material.dispose(); }));
});
