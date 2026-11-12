import * as THREE from "./vendor/three.module.js";

// Display framing only: never rotate source vertices, labels, or fitted poses.
// A thin bounding-box axis is a useful starting view, not anatomical registration.
export function scanViewPose(box, view = "auto") {
  const size = box.getSize(new THREE.Vector3());
  if (view === "auto") {
    const thin = [size.x, size.y, size.z].indexOf(Math.min(size.x, size.y, size.z));
    view = ["side", "above", "face"][thin];
  }
  const poses = {
    face: { direction: [0, 0, -1], up: [0, 1, 0] },
    above: { direction: [0, 1, 0], up: [0, 0, -1] },
    side: { direction: [1, 0, 0], up: [0, 1, 0] },
  };
  return poses[view] || poses.face;
}

export function scanFitDistance(camera, box) {
  const radius = Math.max(box.getBoundingSphere(new THREE.Sphere()).radius, 0.01);
  const vertical = THREE.MathUtils.degToRad(camera.fov);
  const horizontal = 2 * Math.atan(Math.tan(vertical / 2) * Math.max(camera.aspect, 0.001));
  return radius / Math.sin(Math.min(vertical, horizontal) / 2) * 1.08;
}
