import assert from "node:assert/strict";
import { test } from "node:test";

import {
  createLatest,
  degToRad,
  displacement,
  escapeHtml,
  framePoseTotals,
  rotationApplications,
  stageBuckets,
  toothKind,
} from "./core.js";
import { parseStlGeometry } from "./stl.js";
import { canonicalScanSources, demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";

test("toothKind classifies FDI teeth by last digit", () => {
  assert.equal(toothKind("11"), "incisor");
  assert.equal(toothKind("22"), "incisor");
  assert.equal(toothKind("13"), "canine");
  assert.equal(toothKind("24"), "premolar");
  assert.equal(toothKind("15"), "premolar");
  assert.equal(toothKind("16"), "molar");
  assert.equal(toothKind("48"), "molar");
});

test("escapeHtml neutralizes HTML metacharacters", () => {
  assert.equal(
    escapeHtml('<img src=x onerror="alert(1)">'),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
  );
  assert.equal(escapeHtml("a & b's"), "a &amp; b&#39;s");
});

test("escapeHtml coerces non-strings", () => {
  assert.equal(escapeHtml(11), "11");
  assert.equal(escapeHtml(0), "0");
});

test("stageBuckets reindexes gapped stages to contiguous 0..n-1", () => {
  const rows = [
    { stage: 0, tooth: "11" },
    { stage: 2, tooth: "21" },
    { stage: 5, tooth: "31" },
  ];
  const buckets = stageBuckets(rows);
  assert.deepEqual(buckets.map((b) => b.index), [0, 1, 2]);
  assert.equal(buckets[1].rows[0].tooth, "21"); // original stage 2 -> index 1
});

test("stageBuckets groups multiple rows per stage and sorts", () => {
  const rows = [
    { stage: 1, tooth: "21" },
    { stage: 0, tooth: "11" },
    { stage: 1, tooth: "22" },
  ];
  const buckets = stageBuckets(rows);
  assert.equal(buckets.length, 2);
  assert.equal(buckets[0].rows[0].tooth, "11");
  assert.deepEqual(buckets[1].rows.map((r) => r.tooth), ["21", "22"]);
});

test("stageBuckets handles no rows", () => {
  assert.deepEqual(stageBuckets([]), []);
});

test("framePoseTotals maps tooth -> translation from a frame", () => {
  const frame = {
    poses: [
      { tooth: "11", translate_x_mm: 0.5, translate_y_mm: 0.1, translate_z_mm: 0 },
    ],
  };
  const totals = framePoseTotals(frame);
  assert.deepEqual(totals.get("11"), { x: 0.5, y: 0.1, z: 0 });
});

test("framePoseTotals tolerates missing/empty frames", () => {
  assert.equal(framePoseTotals(undefined).size, 0);
  assert.equal(framePoseTotals(null).size, 0);
  assert.equal(framePoseTotals({}).size, 0);
});

test("displacement scales translation by the exaggeration factor", () => {
  assert.deepEqual(
    displacement({ translate_x_mm: 0.2, translate_y_mm: 0, translate_z_mm: -0.1 }, 10),
    { x: 2, y: 0, z: -1 },
  );
});

test("rotationApplications returns nothing when rotation is not renderable", () => {
  const frame = { axes: [[1, 0, 0], [0, 1, 0], [0, 0, 1]] };
  assert.deepEqual(rotationApplications({ rotation_renderable: false, rotate_tip_deg: 5 }, frame), []);
  assert.deepEqual(rotationApplications({ rotation_renderable: true, rotate_tip_deg: 5 }, null), []);
});

test("rotationApplications maps nonzero components onto the frame axes", () => {
  const frame = { axes: [[1, 0, 0], [0, 1, 0], [0, 0, 1]] };
  const apps = rotationApplications(
    { rotation_renderable: true, rotate_tip_deg: 90, rotate_torque_deg: 0, rotate_rotation_deg: 0 },
    frame,
  );
  assert.equal(apps.length, 1); // only the nonzero tip component
  assert.deepEqual(apps[0].axis, [1, 0, 0]);
  assert.ok(Math.abs(apps[0].angleRad - degToRad(90)) < 1e-12);
});

test("createLatest only treats the newest token as current", () => {
  const latest = createLatest();
  const first = latest.next();
  const second = latest.next();
  assert.equal(latest.isCurrent(first), false); // stale response must be dropped
  assert.equal(latest.isCurrent(second), true);
});

test("parseStlGeometry reads ASCII STL vertices", () => {
  const stl = `solid tooth
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid tooth
`;
  const geometry = parseStlGeometry(new TextEncoder().encode(stl).buffer);
  assert.equal(geometry.getAttribute("position").count, 3);
});

test("syntheticCrowdingRows creates 12 stages that counter initial offsets", () => {
  const rows = syntheticCrowdingRows(12);
  const teeth = Object.keys(demoInitialOffsets);
  assert.equal(rows.length, teeth.length * 12);
  const firstTooth = teeth[0];
  const total = rows
    .filter((row) => row.tooth === firstTooth)
    .reduce((sum, row) => sum + row.x, 0);
  assert.ok(Math.abs(total + demoInitialOffsets[firstTooth].x) < 0.01);
});

test("canonical scan sources expose upper and lower STL fixtures", () => {
  assert.deepEqual(canonicalScanSources.map((source) => source.arch), ["maxillary", "mandibular"]);
  assert.ok(canonicalScanSources.every((source) => source.url.endsWith(".stl")));
});
