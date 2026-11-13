// Conservative planar, convex patches. Source coordinates and winding are retained.
const sub = (a, b) => a.map((v, i) => v - b[i]);
const dot = (a, b) => a.reduce((n, v, i) => n + v * b[i], 0);
const cross = (a, b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
export function proposePatch(points, maxDiameter) {
  if (points.length < 3 || points.length > 256) return { reason: "Boundary needs 3–256 vertices" };
  const center = [0, 1, 2].map(axis => points.reduce((n, p) => n + p[axis], 0) / points.length);
  const size = [0, 1, 2].map(axis => Math.max(...points.map(p => p[axis])) - Math.min(...points.map(p => p[axis])));
  const diameter = Math.hypot(...size);
  if (!(diameter > 0) || diameter > maxDiameter) return { diameter, reason: "Opening exceeds the small-hole limit" };
  let normal = [0, 0, 0];
  points.forEach((p, i) => { const n = cross(sub(p, center), sub(points[(i+1)%points.length], center)); normal = normal.map((v, j) => v + n[j]); });
  const length = Math.hypot(...normal);
  if (length < diameter * diameter * 1e-8) return { diameter, reason: "Boundary has no stable plane" };
  normal = normal.map(v => v / length);
  if (points.some(p => Math.abs(dot(sub(p, center), normal)) > diameter * .05)) return { diameter, reason: "Opening is too curved for a simple patch" };
  // A supporting-half-plane check rejects concave and self-crossing polygons.
  const tolerance = diameter * diameter * 1e-9;
  for (let i = 0; i < points.length; i++) {
    const p = points[i], edge = sub(points[(i+1)%points.length], p);
    if (Math.hypot(...edge) < diameter * 1e-8) return { diameter, reason: "Boundary contains tiny or repeated edges" };
    if (points.some(q => dot(cross(edge, sub(q, p)), normal) < -tolerance)) return { diameter, reason: "Opening is not a simple convex boundary" };
    if (dot(cross(edge, sub(center, p)), normal) <= tolerance) return { diameter, reason: "Boundary is too thin to patch" };
  }
  // Reverse the source boundary direction so new faces oppose each shared edge.
  const triangles = points.flatMap((p, i) => [...points[(i+1)%points.length], ...p, ...center]);
  return { diameter, triangles, center, reason: null };
}
