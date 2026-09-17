// Turns canonical scan bytes into renderable geometry.
//
// The engine normalizes every registered scan to one of two shapes - binary STL
// for a mesh, plain-text XYZ for a point cloud - so this is the whole browser
// side of multi-format support. Which format the user originally uploaded is a
// question for scan_formats.js; this module only looks at the bytes it gets.

import * as THREE from "./vendor/three.module.js";
import { looksLikePointCloud } from "./scan_formats.js";
import { parseStlGeometry } from "./stl.js";

// Re-exported so the viewer has one scan-facing import.
export { isSupportedScanName } from "./scan_formats.js";

export function parseScanGeometry(buffer) {
  return looksLikePointCloud(buffer) ? parseXyzGeometry(buffer) : parseStlGeometry(buffer);
}

export function parseXyzGeometry(buffer) {
  const values = [];
  for (const line of new TextDecoder().decode(buffer).split(/\r?\n/)) {
    const parts = line.trim().split(/[\s,]+/);
    if (parts.length < 3) continue;
    const [x, y, z] = parts.map(Number);
    if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) values.push(x, y, z);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(values), 3));
  geometry.computeBoundingBox();
  geometry.userData.kind = "points";
  return geometry;
}

// A point cloud has no surface, so it renders as points rather than as a mesh
// whose triangles the scan never contained.
export function buildScanObject(geometry, material) {
  if (geometry.userData?.kind !== "points") return new THREE.Mesh(geometry, material);
  return new THREE.Points(geometry, pointsMaterialFor(material));
}

let pointsMaterial = null;

function pointsMaterialFor(material) {
  if (!pointsMaterial) {
    pointsMaterial = new THREE.PointsMaterial({ color: material?.color || 0xf6ead6, size: 0.35 });
  }
  return pointsMaterial;
}
