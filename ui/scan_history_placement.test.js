import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "./vendor/three.module.js";
import { placeHistoryObservation } from "./scan_history_placement.js";
import { historyFrames } from "./scan_history_frames.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";
import { binaryStl } from "./surface_repair_mesh.js";

const geometryPoint = raw => new THREE.Vector3(raw[0], -raw[2], raw[1]);
const close = (a, b) => assert.ok(a.distanceTo(b) < 1e-5, `${a.toArray()} != ${b.toArray()}`);

test("crown frames preserve scan geometry and earlier nodes while canceling their inherited placement", () => {
  for (const frame of historyFrames) {
    const origin = new THREE.Vector3().fromArray(frame.origin);
    const raw = [origin.clone(), origin.clone().add(new THREE.Vector3(3, 2, 1)), origin.clone().add(new THREE.Vector3(-1, 4, 2))];
    const scan = { arch: frame.arch, sha256: frame.source_sha256, historyDisplay: true,
      rotation: [1,-1,-1], bytes: binaryStl(Float32Array.from(raw.flatMap(p => p.toArray()))) };
    const group = new THREE.Group(); group.userData.historyCombined = true;
    group.position.set(7, -9, 13); group.rotation.z = frame.arch === "upper" ? Math.PI : 0;
    const baseline = new THREE.Mesh(new THREE.BoxGeometry(10, 10, 10)); group.add(baseline);
    const mesh = new THREE.Mesh(comparisonGeometry(scan)); group.add(mesh); group.updateMatrixWorld(true);
    const previous = baseline.matrixWorld.clone(), positions = mesh.geometry.attributes.position.array.slice();
    placeHistoryObservation(mesh, group, scan);
    assert.ok(Math.abs(mesh.matrixWorld.determinant() - 1) < 1e-10);
    close(mesh.scale, new THREE.Vector3(1, 1, 1));
    assert.deepEqual(mesh.geometry.attributes.position.array, positions);
    assert.deepEqual(baseline.matrixWorld, previous);
    const center = mesh.geometry.userData.sourceCenter;
    const toWorld = p => geometryPoint(p.toArray()).sub(center).applyMatrix4(mesh.matrixWorld);
    const depthCenter = Math.max(...historyFrames.map(item => item.crown_depth_scan_units)) / 2;
    close(toWorld(origin), new THREE.Vector3(0, frame.arch === "upper" ? .6 : -.6, depthCenter));
    close(toWorld(origin.clone().add(new THREE.Vector3().fromArray(frame.up))).sub(toWorld(origin)),
      new THREE.Vector3(0, frame.arch === "upper" ? -1 : 1, 0));
    assert.ok(Math.abs(toWorld(raw[0]).distanceTo(toWorld(raw[1])) - raw[0].distanceTo(raw[1])) < 1e-5);
    const before = mesh.matrixWorld.clone(); placeHistoryObservation(mesh, group, scan);
    assert.deepEqual(mesh.matrixWorld, before);
    baseline.geometry.dispose(); mesh.geometry.dispose();
  }
});

test("inspection frames reject another source and leave non-history meshes alone", () => {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry()), group = new THREE.Group();
  assert.throws(() => placeHistoryObservation(mesh, group, {historyDisplay:true,arch:"lower",sha256:"other"}), /does not match/);
  placeHistoryObservation(mesh, group, {});
  assert.deepEqual(mesh.position.toArray(), [0,0,0]);
  mesh.geometry.dispose();
});

test("individual arch inspection centers the whole model without changing its dimensions", () => {
  const frame = historyFrames[1], group = new THREE.Group();
  group.position.set(8, -3, 7);
  const geometry = new THREE.BoxGeometry(70, 35, 60);
  geometry.computeBoundingBox(); geometry.userData.sourceCenter = new THREE.Vector3(1, 2, 3);
  const mesh = new THREE.Mesh(geometry); group.add(mesh);
  placeHistoryObservation(mesh, group, {historyDisplay:true,arch:"lower",sha256:frame.source_sha256,rotation:[1,-1,-1]});
  close(new THREE.Box3().setFromObject(mesh).getCenter(new THREE.Vector3()), new THREE.Vector3());
  close(mesh.scale, new THREE.Vector3(1, 1, 1));
  geometry.dispose();
});
