import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

// Each gesture turns around the current screen vertical, not an axis left over
// from an earlier preset. Horizontal dragging therefore does not add roll.
export function screenOrbitUp(camera) {
  return new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion).normalize();
}
export function rebuildRegionOrbit(camera, controls, element, onChange, screenAligned = false) {
  if (screenAligned) camera.up.copy(screenOrbitUp(camera));
  const target = controls.target.clone(), enabled = controls.enabled;
  controls.dispose();
  const next = new OrbitControls(camera, element);
  next.target.copy(target); next.enabled = enabled;
  next.screenSpacePanning = true;
  next.addEventListener("change", onChange); next.update();
  return next;
}
