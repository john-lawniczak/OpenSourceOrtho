import * as THREE from "./vendor/three.module.js";
import { labelEdges, boundarySegments } from "./region_boundaries.js";

export function createBoundaryView(scene, geometry) {
  const positions = geometry.attributes.position.array, edges = labelEdges(positions);
  const lines = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({
    color: 0xffffff, transparent: true, opacity: 0.8, depthWrite: false,
  }));
  lines.renderOrder = 2; lines.frustumCulled = false; scene.add(lines);
  let previous = null;
  return {
    update(labels) {
      if (previous?.length === labels.length && labels.every((value, i) => previous[i] === value)) return;
      previous = new Uint8Array(labels);
      lines.geometry.dispose(); lines.geometry = new THREE.BufferGeometry();
      lines.geometry.setAttribute("position", new THREE.BufferAttribute(boundarySegments(edges, positions, labels), 3));
    },
    visible(value) { lines.visible = value; },
    dispose() { scene.remove(lines); lines.geometry.dispose(); lines.material.dispose(); },
  };
}
