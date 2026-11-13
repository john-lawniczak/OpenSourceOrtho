// Brush the existing rim: empty space has no mesh surface to raycast against.
export function nearestOpening(holes, point, radius) {
  let best = -1, distance = radius * radius;
  holes.forEach((hole, index) => hole.points.forEach((a, i) => {
    const b = hole.points[(i + 1) % hole.points.length], ab = b.map((v, j) => v - a[j]);
    const length = ab.reduce((n, v) => n + v * v, 0);
    const t = length ? Math.max(0, Math.min(1, ab.reduce((n, v, j) => n + v * (point[j] - a[j]), 0) / length)) : 0;
    const d = a.reduce((n, v, j) => n + (point[j] - v - ab[j] * t) ** 2, 0);
    if (d < distance) { best = index; distance = d; }
  }));
  return best;
}
