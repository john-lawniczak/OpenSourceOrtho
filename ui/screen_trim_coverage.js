import * as THREE from "./vendor/three.module.js";

// A swept circle covers the gaps between pointer events as well as each stamp.
export function inTrimStroke(x, y, stroke) {
  const dx = stroke.cx - stroke.ax, dy = stroke.cy - stroke.ay;
  const length = dx * dx + dy * dy;
  const t = length ? Math.max(0, Math.min(1, ((x - stroke.ax) * dx + (y - stroke.ay) * dy) / length)) : 0;
  return (x - stroke.ax - t * dx) ** 2 + (y - stroke.ay - t * dy) ** 2 <= stroke.r ** 2;
}

// Face-ID rasterization can represent only one triangle per pixel. Supplement it
// with projected centroids so subpixel triangles on that visible surface are not
// left as speckles. A one-pixel surface-depth band includes nearby roughness;
// deeper occluded surfaces still fail the front-surface depth check.
export function createTrimCoverage(geometry, camera) {
  const positions = geometry.attributes.position, count = positions.count / 3;
  const centers = new Float32Array(count * 3), projected = new Float32Array(count * 3);
  for (let f = 0; f < count; f++) for (let axis = 0; axis < 3; axis++) {
    const i = f * 9 + axis;
    centers[f * 3 + axis] = (positions.array[i] + positions.array[i + 3] + positions.array[i + 6]) / 3;
  }
  let lastKey = "", centerFaces;
  const point = new THREE.Vector3(), a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  function project(size) {
    camera.updateMatrixWorld();
    const key = [...camera.matrixWorldInverse.elements, ...camera.projectionMatrix.elements, size.x, size.y].join(",");
    if (key === lastKey) return;
    lastKey = key;
    centerFaces = new Int32Array(size.x * size.y).fill(-1);
    const depths = new Float32Array(size.x * size.y).fill(Infinity);
    for (let f = 0; f < count; f++) {
      point.fromArray(centers, f * 3).applyMatrix4(camera.matrixWorldInverse);
      projected[f * 3 + 2] = -point.z;
      point.applyMatrix4(camera.projectionMatrix);
      projected[f * 3] = (point.x + 1) * size.x / 2;
      projected[f * 3 + 1] = (point.y + 1) * size.y / 2;
      const x = Math.floor(projected[f * 3]), y = Math.floor(projected[f * 3 + 1]);
      const depth = projected[f * 3 + 2], pixel = y * size.x + x;
      if (x >= 0 && x < size.x && y >= 0 && y < size.y && depth >= camera.near && depth <= camera.far && depth < depths[pixel]) {
        depths[pixel] = depth; centerFaces[pixel] = f;
      }
    }
  }
  function expand(faces, pixels, rect, stroke, size) {
    project(size);
    const planes = new Map(), projection = camera.projectionMatrix.elements;
    function frontDepth(face, x, y) {
      if (!planes.has(face)) {
        a.fromBufferAttribute(positions, face * 3).applyMatrix4(camera.matrixWorldInverse);
        b.fromBufferAttribute(positions, face * 3 + 1).applyMatrix4(camera.matrixWorldInverse);
        c.fromBufferAttribute(positions, face * 3 + 2).applyMatrix4(camera.matrixWorldInverse);
        const near = Math.min(-a.z, -b.z, -c.z), far = Math.max(-a.z, -b.z, -c.z);
        const normal = b.sub(a).cross(c.sub(a)).normalize();
        planes.set(face, [normal.x, normal.y, normal.z, normal.dot(a), near, far]);
      }
      const [nx, ny, nz, d, near, far] = planes.get(face);
      const denominator = nx * ((2 * x / size.x - 1) / projection[0]) + ny * ((2 * y / size.y - 1) / projection[5]) - nz;
      return Math.abs(denominator) > 1e-10 ? Math.max(near, Math.min(far, d / denominator)) : NaN;
    }
    for (let f = 0; f < count; f++) {
      const x = projected[f * 3], y = projected[f * 3 + 1], depth = projected[f * 3 + 2];
      if (faces.has(f) || depth < camera.near || depth > camera.far || !inTrimStroke(x, y, stroke)) continue;
      const col = Math.floor(x) - rect.x, row = Math.floor(y) - rect.y;
      if (col < 0 || col >= rect.w || row < 0 || row >= rect.h) continue;
      const i = (row * rect.w + col) * 4;
      const id = pixels[i] * 65536 + pixels[i + 1] * 256 + pixels[i + 2];
      // Subpixel foreground may miss every raster sample. Its centroid still
      // occludes deeper centroids in that pixel, including at silhouette edges.
      const centerFace = centerFaces[Math.floor(y) * size.x + Math.floor(x)];
      const depths = [id ? frontDepth(id - 1, x, y) : NaN, frontDepth(centerFace, x, y)]
        .filter(value => Number.isFinite(value) && value > 0);
      const front = Math.min(...depths);
      // One drawing-buffer pixel in view space captures near-surface roughness,
      // without turning the brush into an unlimited cut through the model.
      const tolerance = Math.max(1e-5, 2 * depth / (size.y * projection[5]));
      if (Number.isFinite(front) && depth <= front + tolerance) faces.add(f);
    }
  }
  return { expand };
}
