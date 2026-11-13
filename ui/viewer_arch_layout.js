import * as THREE from "./vendor/three.module.js";

// Display-only separated arches for week 7 exports. No bite registration is implied.
export function arrangeScanArches(meshes) {
  for (const mesh of meshes) {
    if (!mesh.userData.displayArchStack) continue;
    const upper = mesh.userData.arch === "upper";
    mesh.rotation.z = upper ? Math.PI : 0;
    mesh.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(mesh);
    mesh.position.y = upper ? 1 - bounds.min.y : -1 - bounds.max.y;
    mesh.updateMatrix();
    mesh.userData.layoutPosition = mesh.position.clone();
    mesh.userData.scanView = { arch: mesh.userData.arch, front: { direction: [0,0,1], up: [0,1,0] } };
  }
}

export function archDisplayMatrix(meshes, arch) {
  return meshes.find(mesh => mesh.userData.arch === arch)?.matrix || new THREE.Matrix4();
}
