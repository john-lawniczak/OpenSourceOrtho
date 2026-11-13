import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "./vendor/three.module.js";
import { scanViewPose, scanFitDistance, scanFrontPose } from "./scan_view_pose.js";

test("all front presets keep canonical upper crowns down across scanner conventions", () => {
  const box = new THREE.Box3(new THREE.Vector3(-30,-10,-25), new THREE.Vector3(30,10,25));
  for (const [arch, rotation, gumZ, crownZ, expected] of [
    ["upper", [-1,1,-1], 10, 0, -1], // original upper baseline is crown-down in source axes
    ["upper", [1,1,1], 0, 10, -1], // week 7 and similar exports are crown-up
    ["lower", [1,1,1], -10, 0, 1],
  ]) for (const command of ["default", "face", "auto", "side"]) {
    const pose = scanViewPose(box, command, { arch });
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 2000);
    camera.up.fromArray(pose.up); camera.position.fromArray(pose.direction).multiplyScalar(100);
    camera.lookAt(0, 0, 0); camera.updateMatrixWorld();
    const gum = new THREE.Vector3(0, gumZ * rotation[2], 0).project(camera);
    const crown = new THREE.Vector3(0, crownZ * rotation[2], 0).project(camera);
    assert.equal(Math.sign(crown.y - gum.y), expected, `${arch} ${rotation} ${command}`);
    if (command !== "side") assert.deepEqual(pose.direction, [0,0,1]);
    // Raw uploads use the documented signs in the camera, not source vertices.
    const raw = scanFrontPose(arch, rotation);
    assert.equal(Math.sign((crownZ - gumZ) * raw.up[1]), expected);
  }
});

test("occlusal views face crown tips while preserving upper/lower screen orientation", () => {
  const box = new THREE.Box3(new THREE.Vector3(-30,-10,-25), new THREE.Vector3(30,10,25));
  for (const arch of ["upper", "lower"]) {
    const pose = scanViewPose(box, "above", { arch });
    assert.deepEqual(pose.direction, [0,1,0]);
    assert.deepEqual(pose.up, [0,0,arch === "upper" ? 1 : -1]);
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

test("alternate painting axes keep front, above and side distinct", () => {
  const box = new THREE.Box3(new THREE.Vector3(-20,-15,-10), new THREE.Vector3(20,15,10));
  const front = {direction:[0,1,0], up:[0,0,-1]};
  for (const arch of ["upper", "lower"]) {
    assert.deepEqual(scanViewPose(box, "default", {arch, front}), front);
    for (const command of ["above", "side"]) {
      const pose = scanViewPose(box, command, {arch, front});
      assert.equal(new THREE.Vector3(...pose.direction).dot(new THREE.Vector3(...pose.up)), 0);
      assert.equal(new THREE.Vector3(...pose.direction).dot(new THREE.Vector3(...front.direction)), 0);
    }
  }
});
