import * as THREE from "./vendor/three.module.js";

// Canonical display geometry is crown-up (+Y), viewed from the anterior (+Z).
// The arch determines screen vertical; source rotation alone cannot identify it.
// Raw uploaded geometry can supply its documented source-to-canonical signs.
export function scanFrontPose(arch, rotation = [1, 1, 1]) {
  const vertical = arch === "upper" || arch === "maxillary" ? -1 : 1;
  return { direction: [0, 0, rotation[1]], up: [0, vertical * rotation[2], 0] };
}

// Display framing only: never rotate source vertices, labels, or fitted poses.
export function scanViewPose(box, view = "auto", { arch, front } = {}) {
  front ||= arch === "upper" || arch === "lower" ? scanFrontPose(arch) : null;
  const size = box.getSize(new THREE.Vector3());
  if (view === "auto") {
    // Full dental arches use the same front convention as Default/Face-on.
    // A nearly planar test/import surface still needs its broad side visible.
    if (front && Math.min(size.x, size.y, size.z) > Math.max(size.x, size.y, size.z) * 0.02) return front;
    const thin = [size.x, size.y, size.z].indexOf(Math.min(size.x, size.y, size.z));
    view = ["side", "above", "face"][thin];
  }
  if (front && ["default", "face"].includes(view)) return front;
  const up = front?.up || [0, 1, 0], archSign = arch === "upper" ? -1 : 1;
  // A documented painting camera may use a different front/up basis. Keep its
  // Above and Side buttons relative to that frame instead of fixed world axes.
  if (front && (front.direction[0] || front.direction[1] || up[0] || up[2])) {
    if (view === "above") return { direction: up.map(v => archSign * v), up: front.direction.map(v => -archSign * v) };
    if (view === "side") return { direction: new THREE.Vector3().fromArray(up)
      .cross(new THREE.Vector3().fromArray(front.direction)).multiplyScalar(archSign).normalize().toArray(), up };
  }
  const poses = {
    face: { direction: [0, 0, -1], up },
    above: { direction: [0, archSign * up[1], 0], up: [0, 0, -archSign * (front?.direction[2] || 1)] },
    side: { direction: [1, 0, 0], up },
  };
  return poses[view] || poses.face;
}

export function scanFitDistance(camera, box) {
  const radius = Math.max(box.getBoundingSphere(new THREE.Sphere()).radius, 0.01);
  const vertical = THREE.MathUtils.degToRad(camera.fov);
  const horizontal = 2 * Math.atan(Math.tan(vertical / 2) * Math.max(camera.aspect, 0.001));
  return radius / Math.sin(Math.min(vertical, horizontal) / 2) * 1.08;
}
