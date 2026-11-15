import * as THREE from "./vendor/three.module.js";

// Approximate inspection poses for the selected model captures, in the comparison
// display frame. Rounded Euler angles are not anatomical/cross-visit registrations.
const MODEL_POSES = { upper: [-145, 15, 150], lower: [70, -5, -10] };

function surfaceAnchor(mesh) {
  mesh.updateMatrix();
  const points = mesh.geometry.attributes.position, axes = [[], [], []];
  const point = new THREE.Vector3(), stride = Math.max(1, Math.floor(points.count / 12000));
  for (let i = 0; i < points.count; i += stride) {
    point.fromBufferAttribute(points, i).applyMatrix4(mesh.matrix);
    axes[0].push(point.x); axes[1].push(point.y); axes[2].push(point.z);
  }
  axes.forEach(axis => axis.sort((a, b) => a - b));
  const q = (axis, fraction) => axes[axis][Math.floor((axes[axis].length - 1) * fraction)];
  // Robust lateral center, crown-facing edge, and anterior edge reduce the effect
  // of stray model-base triangles. No scaling or geometry modification.
  return new THREE.Vector3((q(0, .02) + q(0, .98)) / 2, q(1, .98), q(2, .98));
}

export function placeHistoryObservation(mesh, baseline, scan) {
  if (!scan.historyDisplay) return;
  mesh.rotation.set(...MODEL_POSES[scan.arch].map(THREE.MathUtils.degToRad));
  mesh.position.copy(surfaceAnchor(baseline).sub(surfaceAnchor(mesh)));
  mesh.updateMatrixWorld(true);
}
