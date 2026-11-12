// Match the audit's exact-coordinate welding and manifold shared-edge definition.
export function manifoldFacePairs(positions) {
  if (positions.length % 9) throw new Error("Expected source triangles.");
  const vertices = new Map(), edges = new Map();
  function vertex(offset) {
    const xyz = [positions[offset], positions[offset + 1], positions[offset + 2]];
    if (!xyz.every(Number.isFinite)) throw new Error("Non-finite source coordinates.");
    const key = xyz.join(",");
    if (!vertices.has(key)) vertices.set(key, vertices.size);
    return vertices.get(key);
  }
  for (let face = 0; face < positions.length / 9; face++) {
    const ids = [0, 3, 6].map(offset => vertex(face * 9 + offset));
    for (let corner = 0; corner < 3; corner++) {
      const a = ids[corner], b = ids[(corner + 1) % 3];
      const key = a < b ? `${a}:${b}` : `${b}:${a}`;
      const entry = edges.get(key);
      if (entry) { entry.count++; entry.second = face; }
      else edges.set(key, { first: face, second: -1, count: 1 });
    }
  }
  const pairs = [];
  for (const { first, second, count } of edges.values()) {
    if (count === 2 && first !== second) pairs.push(first, second);
  }
  return new Int32Array(pairs);
}

export function disconnectedPatches(labels, pairs) {
  const parent = Int32Array.from(labels, (_, i) => i), sizes = new Int32Array(labels.length).fill(1);
  function root(i) {
    while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; }
    return i;
  }
  for (let i = 0; i < pairs.length; i += 2) {
    const a = pairs[i], b = pairs[i + 1];
    if (!labels[a] || labels[a] !== labels[b]) continue;
    let x = root(a), y = root(b);
    if (x === y) continue;
    if (sizes[x] < sizes[y]) [x, y] = [y, x];
    parent[y] = x; sizes[x] += sizes[y];
  }
  const components = new Map(), main = new Map();
  for (let face = 0; face < labels.length; face++) {
    const label = labels[face]; if (!label) continue;
    const id = root(face);
    if (!components.has(id)) components.set(id, { label, faces: [] });
    components.get(id).faces.push(face);
  }
  for (const group of components.values()) {
    // Face-order tie breaking agrees with scipy's first largest component.
    if (!main.has(group.label) || group.faces.length > main.get(group.label).faces.length) main.set(group.label, group);
  }
  return [...components.values()].filter(group => group !== main.get(group.label))
    .sort((a, b) => a.label - b.label || b.faces.length - a.faces.length || a.faces[0] - b.faces[0]);
}
