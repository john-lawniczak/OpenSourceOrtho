import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "./vendor/three.module.js";
import { scanViewPose, scanFitDistance, scanFrontPose } from "./scan_view_pose.js";

test("default source-front view restores upper crowns down and lower crowns up", () => {
  for (const [rotation, gumZ, crownZ, expected] of [[[-1,1,-1], 10, 0, -1], [[1,1,1], -10, 0, 1]]) {
    const pose = scanFrontPose(rotation), camera = new THREE.PerspectiveCamera(36, 1, 0.1, 2000);
    camera.up.fromArray(pose.up); camera.position.fromArray(pose.direction).multiplyScalar(100);
    camera.lookAt(0, 0, 0); camera.updateMatrixWorld();
    const gum = new THREE.Vector3(0, gumZ * rotation[2], 0).project(camera);
    const crown = new THREE.Vector3(0, crownZ * rotation[2], 0).project(camera);
    assert.equal(Math.sign(crown.y - gum.y), expected);
    assert.deepEqual(pose.direction, [0,0,1]);
  }
});

test("auto view adapts to different scanner axes without mutating the bounds", () => {
  for (const [size, expected] of [[[80, 60, 40], [0, 0, -1]], [[80, 30, 60], [0, 1, 0]], [[20, 80, 60], [1, 0, 0]]]) {
    const box = new THREE.Box3(new THREE.Vector3(-40, 20, 200), new THREE.Vector3(-40, 20, 200).add(new THREE.Vector3(...size)));
    const original = box.clone(), pose = scanViewPose(box);
    assert.deepEqual(pose.direction, expected); assert.ok(box.equals(original));
    assert.equal(new THREE.Vector3(...pose.direction).dot(new THREE.Vector3(...pose.up)), 0);
  }
});
test("camera fit contains large offset scans in both wide and narrow viewports", () => {
  const box = new THREE.Box3(new THREE.Vector3(-40, 200, 20), new THREE.Vector3(45, 260, 70));
  for (const aspect of [0.5, 2]) {
    const camera = new THREE.PerspectiveCamera(36, aspect, 0.1, 2000);
    const distance = scanFitDistance(camera, box);
    camera.position.copy(box.getCenter(new THREE.Vector3())).add(new THREE.Vector3(0, 0, distance));
    camera.lookAt(box.getCenter(new THREE.Vector3())); camera.updateMatrixWorld();
    for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) {
      const p = new THREE.Vector3(x, y, z).project(camera);
      assert.ok(Math.abs(p.x) < 1 && Math.abs(p.y) < 1, `Clipped corner: ${p.toArray()}`);
    }
  }
});
