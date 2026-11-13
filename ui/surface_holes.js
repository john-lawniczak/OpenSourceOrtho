import { patchIntersectsSurface } from "./surface_patch_intersection.js";
import { proposePatch } from "./surface_patch.js";

// Exact welding only: near-coincident surfaces are never silently joined.
export function findSurfaceHoles(positions, maxDiameter = 3) {
  if (!positions.length || positions.length % 9 || positions.length > 9_000_000) throw new Error("Inspect scans with 1–1,000,000 triangles.");
  if (!Number.isFinite(maxDiameter) || maxDiameter <= 0) throw new Error("Enter a positive small-hole size in scan units.");
  const vertices = new Map(), points = [], parents = [], edges = new Map(), bad = new Set();
  const root = id => { while (parents[id] !== id) { parents[id] = parents[parents[id]]; id = parents[id]; } return id; };
  function vertex(i) {
    const p = Array.from(positions.subarray(i, i+3));
    if (!p.every(Number.isFinite)) throw new Error("Scan contains non-finite coordinates.");
    const key = p.join(",");
    if (!vertices.has(key)) { vertices.set(key, points.length); parents.push(points.length); points.push(p); }
    return vertices.get(key);
  }
  const stride = positions.length / 3 + 1;
  for (let f = 0; f < positions.length; f += 9) {
    const ids = [vertex(f), vertex(f+3), vertex(f+6)];
    for (let i = 0; i < 3; i++) {
      const a = ids[i], b = ids[(i+1)%3];
      parents[root(b)] = root(a);
      if (new Set(ids).size < 3) { ids.forEach(id => bad.add(id)); continue; }
      const key = Math.min(a,b) * stride + Math.max(a,b), entry = edges.get(key);
      if (!entry) edges.set(key, { a, b, third: ids[(i+2)%3], count: 1 });
      else { entry.count++; if (entry.count > 2 || entry.a === a) { bad.add(a); bad.add(b); } }
    }
  }
  const adjacent = new Map(), boundary = [];
  for (const e of edges.values()) if (e.count === 1) {
    boundary.push(e);
    for (const id of [e.a, e.b]) { if (!adjacent.has(id)) adjacent.set(id, []); adjacent.get(id).push(e); }
  }
  if (boundary.length > 50_000) throw new Error("Too many open edges for small-hole repair; inspect the source mesh first.");
  const seen = new Set(), loops = []; let rejected = 0;
  for (const start of boundary) {
    if (seen.has(start)) continue;
    const stack = [start], component = [];
    while (stack.length) {
      const e = stack.pop(); if (seen.has(e)) continue;
      seen.add(e); component.push(e);
      for (const id of [e.a,e.b]) for (const next of adjacent.get(id)) if (!seen.has(next)) stack.push(next);
    }
    if (component.some(e => [e.a,e.b].some(id => bad.has(id) || adjacent.get(id).length !== 2))) { rejected++; continue; }
    const outgoing = new Map(component.map(e => [e.a,e]));
    if (outgoing.size !== component.length) { rejected++; continue; }
    const ids = []; let e = start;
    do { ids.push(e.a); e = outgoing.get(e.b); } while (e && e !== start && ids.length <= component.length);
    if (e !== start || ids.length !== component.length) { rejected++; continue; }
    const loop = ids.map(id => points[id]);
    const perimeter = loop.reduce((n,p,i) => n + Math.hypot(...p.map((v,j) => v-loop[(i+1)%loop.length][j])), 0);
    loops.push({ points: loop, support: component.map(e=>points[e.third]), perimeter, component: root(ids[0]) });
  }
  if (loops.length > 128) throw new Error("Too many separate openings for a bounded small-hole inspection; use a smaller surface.");
  const largest = new Map();
  for (const loop of loops) if (!largest.has(loop.component) || largest.get(loop.component).perimeter < loop.perimeter) largest.set(loop.component, loop);
  const low = [Infinity,Infinity,Infinity], high = [-Infinity,-Infinity,-Infinity];
  points.forEach(p => p.forEach((v,i) => { low[i] = Math.min(low[i],v); high[i] = Math.max(high[i],v); }));
  const limit = Math.min(maxDiameter, Math.hypot(...high.map((v,i) => v-low[i])) * .15);
  const holes = loops.map((loop, index) => {
    const patch = largest.get(loop.component) === loop ? { reason: "Outer or ambiguous boundary — kept open" } : proposePatch(loop.points, limit);
    if (patch.triangles && patchIntersectsSurface(patch.triangles, positions, patch.diameter)) { patch.reason = "Patch would overlap an existing surface"; delete patch.triangles; }
    return { id: index+1, points: loop.points, support:loop.support, outer:largest.get(loop.component)===loop, ...patch };
  });
  return { holes, rejected, boundaryEdges: boundary.length, limit };
}
