import { parseStlGeometry } from "./stl.js";

// Proper display rotations and translation only. Never fit scale, deform a
// crown, match vertices across visits, or claim anatomical registration.
export function comparisonGeometry(scan) {
  const geometry = parseStlGeometry(scan.bytes);
  const positions = geometry.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i) * scan.rotation[0];
    const y = positions.getY(i) * scan.rotation[1];
    const z = positions.getZ(i) * scan.rotation[2];
    if (![x, y, z].every(Number.isFinite)) {
      geometry.dispose();
      throw new Error("The scan contains non-finite coordinates.");
    }
    positions.setXYZ(i, x, z, -y);
  }
  geometry.computeBoundingBox();
  if (geometry.boundingBox.isEmpty()) {
    geometry.dispose();
    throw new Error("The scan contains no surface geometry.");
  }
  geometry.userData.sourceCenter = geometry.boundingBox.getCenter(geometry.boundingBox.min.clone());
  geometry.center();
  geometry.computeVertexNormals();
  geometry.computeBoundingSphere();
  return geometry;
}
