import test from "node:test";
import assert from "node:assert/strict";
import { labelEdges, boundarySegments } from "./region_boundaries.js";
import { RegionEdits } from "./region_edits.js";

test("label edges follow face ownership, without drawing internal triangle edges", () => {
  // Two triangles with duplicated STL vertices share the diagonal.
  const positions = new Float32Array([0,0,0, 1,0,0, 1,1,0, 0,0,0, 1,1,0, 0,1,0]);
  const edges = labelEdges(positions);
  assert.equal(edges.length / 4, 5);
  assert.equal(boundarySegments(edges, positions, [25,25]).length / 6, 4);
  assert.equal(boundarySegments(edges, positions, [25,26]).length / 6, 5);
  assert.equal(boundarySegments(edges, positions, [0,0]).length, 0);
  assert.equal(boundarySegments(edges, positions, [25,0]).length / 6, 3);
});

test("spillover painting only transfers source faces; undo restores both crowns", () => {
  const edits = new RegionEdits([25,25,26,27,0], "upper");
  edits.beginStroke(); edits.paint([1,2,3,4],26,25); edits.endStroke();
  assert.deepEqual([...edits.labels], [25,26,26,27,0]);
  edits.undo(); assert.deepEqual([...edits.labels], [25,25,26,27,0]);
  edits.redo(); assert.deepEqual([...edits.labels], [25,26,26,27,0]);
});
