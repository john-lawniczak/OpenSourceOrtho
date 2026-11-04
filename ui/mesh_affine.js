// Conjugate the engine's scan-local affine transform by rotateX(-90).
// Return row-major Matrix4 elements, without recomputing anatomical rotations.
export function orientedMeshMatrix(affine, pose, exaggeration = 1) {
  const a = affine || [[1, 0, 0, pose.translate_x_mm || 0], [0, 1, 0, pose.translate_y_mm || 0], [0, 0, 1, pose.translate_z_mm || 0]];
  const order = [0, 2, 1], signs = [1, 1, -1];
  const extra = [pose.translate_x_mm || 0, pose.translate_y_mm || 0, pose.translate_z_mm || 0];
  const rows = order.flatMap((axis, i) => [
    ...order.map((column, j) => signs[i] * signs[j] * a[axis][column]),
    signs[i] * (a[axis][3] + extra[axis] * (exaggeration - 1)),
  ]);
  return [...rows, 0, 0, 0, 1];
}
