import * as THREE from "./vendor/three.module.js";
import { historyFrames } from "./scan_history_frames.js";

// Separate rigid inspection frames use draft crown rows, not cast/base outlines.
// A small display gap keeps the arches distinct; it is not measured occlusion.
export function placeHistoryObservation(mesh, group, scan) {
  if (!scan.historyDisplay) return;
  const frame = historyFrames.find(item => item.source_sha256 === scan.sha256 && item.arch === scan.arch);
  if (!frame) throw new Error("Week 18 inspection frame does not match this scan.");
  const up = new THREE.Vector3().fromArray(frame.up).normalize();
  const front = new THREE.Vector3().fromArray(frame.front);
  front.addScaledVector(up, -front.dot(up)).normalize();
  const right = up.clone().cross(front).normalize(), origin = new THREE.Vector3().fromArray(frame.origin);
  const sourceToCrown = new THREE.Matrix4().set(
    right.x, right.y, right.z, -right.dot(origin),
    up.x, up.y, up.z, -up.dot(origin),
    front.x, front.y, front.z, -front.dot(origin),
    0, 0, 0, 1);
  const [rx, ry, rz] = scan.rotation;
  const sourceToGeometry = new THREE.Matrix4().set(rx,0,0,0, 0,0,rz,0, 0,-ry,0,0, 0,0,0,1);
  const center = mesh.geometry.userData.sourceCenter;
  const world = sourceToCrown.multiply(sourceToGeometry.invert())
    .multiply(new THREE.Matrix4().makeTranslation(center.x, center.y, center.z));
  const depthCenter = Math.max(...historyFrames.map(item => item.crown_depth_scan_units)) / 2;
  let vertical = 0;
  if (group.userData.historyCombined) {
    const upper = scan.arch === "upper";
    if (upper) world.premultiply(new THREE.Matrix4().makeRotationZ(Math.PI));
    vertical = upper ? .6 : -.6;
  }
  world.premultiply(new THREE.Matrix4().makeTranslation(0, vertical, depthCenter));
  if (!group.userData.historyCombined) {
    // An individual arch is centered for inspection, without changing its
    // crown orientation. Pair placement continues to use the common origins.
    const center = mesh.geometry.boundingBox.clone().applyMatrix4(world).getCenter(new THREE.Vector3());
    world.premultiply(new THREE.Matrix4().makeTranslation(-center.x, -center.y, -center.z));
  }
  // Cancel the older visits' group placement for this node only. Otherwise the
  // baseline cast bounds would offset/tilt the new crown frame a second time.
  group.updateMatrixWorld(true);
  const local = group.matrixWorld.clone().invert().multiply(world);
  local.decompose(mesh.position, mesh.quaternion, mesh.scale);
  mesh.updateMatrixWorld(true);
}
