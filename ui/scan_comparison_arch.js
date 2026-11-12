import * as THREE from "./vendor/three.module.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";
import { createMotionSurfaces, viewerRegistration } from "./scan_motion_geometry.js";

export function comparisonArch(scans, preview, material) {
  const meshes = [];
  let simulation;
  try {
    for (const scan of scans) meshes.push(new THREE.Mesh(comparisonGeometry(scan), material));
    if (preview) {
      meshes[1].geometry.applyMatrix4(viewerRegistration(preview.target_to_source));
      simulation = createMotionSurfaces(meshes[0].geometry, preview, material);
    }
  } catch (error) {
    meshes.forEach(mesh => mesh.geometry.dispose());
    throw error;
  }
  const group = new THREE.Group(), nodes = [...meshes, simulation?.group];
  nodes.filter(Boolean).forEach(node => group.add(node));
  return { group, meshes, nodes, simulation, motion: preview, arch: scans[0].arch,
    dispose() { meshes.forEach(mesh => mesh.geometry.dispose()); simulation?.dispose(); } };
}

// Display arrangement only. Keep each arch's placement fixed across visits;
// this does not estimate an occlusal/bite registration or change motion geometry.
export function arrangeComparisonArches(entries) {
  const combined = entries.length > 1;
  if (!combined) return Math.max(...entries[0].meshes.map(mesh => mesh.geometry.boundingSphere.radius), 5) * 1.08;
  const gap = combined ? Math.max(...entries.map(e => e.meshes[0].geometry.boundingSphere.radius)) * .04 : 0;
  for (const entry of entries) {
    entry.group.rotation.z = combined && entry.arch === "upper" ? Math.PI : 0;
    entry.group.position.set(0, 0, 0);
    entry.group.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(entry.meshes[0]);
    if (combined) entry.group.position.y = entry.arch === "upper" ? gap/2 - bounds.min.y : -gap/2 - bounds.max.y;
    entry.group.updateMatrixWorld(true);
  }
  const bounds = new THREE.Box3();
  for (const entry of entries) for (const mesh of entry.meshes) bounds.union(new THREE.Box3().setFromObject(mesh));
  const center = bounds.getCenter(new THREE.Vector3());
  if (combined) for (const entry of entries) { entry.group.position.sub(center); entry.group.updateMatrixWorld(true); }
  return Math.max(bounds.getSize(new THREE.Vector3()).length()/2, 5) * 1.08;
}
