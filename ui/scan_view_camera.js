import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

import { scanViewPose, scanFitDistance } from "./scan_view_pose.js";

export function frameScanView(camera, controls, element, box, command, onChange, viewContext = {}) {
  if (!box || box.isEmpty()) return controls;
  const center = box.getCenter(new THREE.Vector3());
  const direction = camera.position.clone().sub(controls.target).normalize();
  if (command === "flip") direction.negate();
  else if (command === "roll-left" || command === "roll-right") {
    camera.up.applyAxisAngle(direction, command === "roll-left" ? Math.PI / 2 : -Math.PI / 2);
  } else if (command !== "fit") {
    const pose = scanViewPose(box, command, viewContext);
    direction.fromArray(pose.direction); camera.up.fromArray(pose.up);
  }
  const distance = scanFitDistance(camera, box);
  camera.position.copy(center).addScaledVector(direction, distance);
  camera.near = Math.max(distance / 1000, 0.0001); camera.far = distance * 100;
  camera.updateProjectionMatrix();
  // OrbitControls caches its up-axis at construction. Recreate after a roll so
  // the next drag does not snap back or orbit around the old axis.
  const damping = controls.enableDamping, enabled = controls.enabled;
  const auto = controls.autoRotate, speed = controls.autoRotateSpeed;
  controls.dispose();
  const next = new OrbitControls(camera, element);
  next.enableDamping = damping; next.enabled = enabled;
  next.autoRotate = auto; next.autoRotateSpeed = speed;
  next.target.copy(center); next.addEventListener("change", onChange); next.update();
  onChange();
  return next;
}
