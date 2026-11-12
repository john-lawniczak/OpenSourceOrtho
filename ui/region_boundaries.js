// Exact shared edges in the original face order; never infer anatomical boundaries.
export function labelEdges(positions) {
  const vertices = new Map(), edges = new Map(), result = [];
  function vertex(index) {
    const key = `${positions[index]},${positions[index + 1]},${positions[index + 2]}`;
    if (!vertices.has(key)) vertices.set(key, vertices.size);
    return vertices.get(key);
  }
  for (let face = 0; face < positions.length / 9; face++) {
    const offsets = [face * 9, face * 9 + 3, face * 9 + 6], ids = offsets.map(vertex);
    for (let corner = 0; corner < 3; corner++) {
      const next = (corner + 1) % 3, a = ids[corner], b = ids[next];
      if (a === b) continue;
      const key = a < b ? `${a}:${b}` : `${b}:${a}`;
      if (edges.has(key)) result[edges.get(key) + 3] = face;
      else { edges.set(key, result.length); result.push(offsets[corner], offsets[next], face, -1); }
    }
  }
  return new Int32Array(result);
}

export function boundarySegments(edges, positions, labels) {
  const result = [];
  for (let i = 0; i < edges.length; i += 4) {
    const [a, b, first, second] = edges.subarray(i, i + 4);
    const left = labels[first] || 0, right = second < 0 ? 0 : labels[second] || 0;
    if (left === right) continue;
    result.push(...positions.subarray(a, a + 3), ...positions.subarray(b, b + 3));
  }
  return new Float32Array(result);
}
