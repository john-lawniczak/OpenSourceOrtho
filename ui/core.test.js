import assert from "node:assert/strict";
import { test } from "node:test";

import {
  FULL_ARCH_TEETH,
  archFromTooth,
  confidenceTier,
  countNoteMarkup,
  createLatest,
  closestDatasetTarget,
  degToRad,
  displacement,
  escapeHtml,
  framePoseTotals,
  inferArchFromName,
  normalizeArchLabel,
  rotationApplications,
  rowsFromPlan,
  stageBuckets,
  toothKind,
} from "./core.js";
import { parseStlGeometry } from "./stl.js";
import { canonicalScanSources, demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";

test("confidenceTier buckets a percentage into low/mid/high", () => {
  assert.equal(confidenceTier(20), "low");
  assert.equal(confidenceTier(44), "low");
  assert.equal(confidenceTier(45), "mid");
  assert.equal(confidenceTier(64), "mid");
  assert.equal(confidenceTier(65), "high");
  assert.equal(confidenceTier(100), "high");
});

test("countNoteMarkup warns only when an arch is not a full arch", () => {
  const full = Array.from({ length: FULL_ARCH_TEETH }, () => ({ arch: "maxillary" }));
  assert.equal(countNoteMarkup(full), "");
  assert.equal(countNoteMarkup([]), "");

  const short = Array.from({ length: FULL_ARCH_TEETH - 1 }, () => ({ arch: "maxillary" }));
  const note = countNoteMarkup(short);
  assert.match(note, /Proposed 13 maxillary/);
});

test("countNoteMarkup is ambiguous (merge OR missing) when no gap is marked", () => {
  const short = Array.from({ length: FULL_ARCH_TEETH - 2 }, () => ({ arch: "maxillary" }));
  const note = countNoteMarkup(short, 0);
  // Does not assert a tooth is missing - it may be merged crowns.
  assert.match(note, /merged/);
  assert.match(note, /a tooth may be absent/);
  assert.match(note, /Re-anchor/);
});

test("countNoteMarkup is confirmatory when the reviewer marked the gap", () => {
  const short = Array.from({ length: FULL_ARCH_TEETH - 1 }, () => ({ arch: "maxillary" }));
  const note = countNoteMarkup(short, 1);
  assert.match(note, /your 1 marked gap\b/);
  // No re-prompt to enter a missing tooth once the gap is marked.
  assert.doesNotMatch(note, /Re-anchor/);
  assert.doesNotMatch(note, /enter its FDI/);
  // Plural form for multiple gaps.
  assert.match(countNoteMarkup(Array.from({ length: FULL_ARCH_TEETH - 2 }, () => ({ arch: "maxillary" })), 2), /marked gaps/);
});

test("countNoteMarkup escapes arch names", () => {
  const note = countNoteMarkup([{ arch: "<b>x</b>" }]);
  assert.match(note, /&lt;b&gt;x&lt;\/b&gt;/);
  assert.doesNotMatch(note, /<b>x<\/b>/);
});

test("toothKind classifies FDI teeth by last digit", () => {
  assert.equal(toothKind("11"), "incisor");
  assert.equal(toothKind("22"), "incisor");
  assert.equal(toothKind("13"), "canine");
  assert.equal(toothKind("24"), "premolar");
  assert.equal(toothKind("15"), "premolar");
  assert.equal(toothKind("16"), "molar");
  assert.equal(toothKind("48"), "molar");
});

test("arch helpers reject invalid and ambiguous arch signals", () => {
  assert.equal(normalizeArchLabel("upper"), "maxillary");
  assert.equal(inferArchFromName("upper.stl"), "maxillary");
  assert.equal(inferArchFromName("scan_l.stl"), "mandibular");
  assert.equal(inferArchFromName("upper-lower.stl"), null);
  assert.equal(archFromTooth("11"), "maxillary");
  assert.equal(archFromTooth("38"), "mandibular");
  assert.equal(archFromTooth("99"), null);
  assert.equal(archFromTooth("1"), null);
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

test("rowsFromPlan maps engine stages into editable UI rows", () => {
  const rows = rowsFromPlan({
    stages: [
      {
        index: 2,
        deltas: [
          {
            tooth: { value: "11" },
            translate_x_mm: 0.1,
            translate_y_mm: 0.2,
            translate_z_mm: 0.3,
            rotate_tip_deg: 1,
            rotate_torque_deg: 2,
            rotate_rotation_deg: 3,
          },
        ],
      },
    ],
  });
  assert.deepEqual(rows, [
    { stage: 2, tooth: "11", x: 0.1, y: 0.2, z: 0.3, tip: 1, torque: 2, rotation: 3 },
  ]);
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

test("closestDatasetTarget returns direct and ancestor data targets", () => {
  const direct = { dataset: { journeyStep: "review" } };
  assert.equal(closestDatasetTarget(direct, "journeyStep"), direct);

  const ancestor = { dataset: { journeyStep: "stages" } };
  const child = {
    dataset: {},
    closest(selector) {
      assert.equal(selector, "[data-journey-step]");
      return ancestor;
    },
  };
  assert.equal(closestDatasetTarget(child, "journeyStep"), ancestor);
});

test("closestDatasetTarget tolerates non-element targets", () => {
  assert.equal(closestDatasetTarget(null, "journeyStep"), null);
  assert.equal(closestDatasetTarget({ dataset: {} }, "journeyStep"), null);
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

test("syntheticCrowdingRows can keep stage 0 as a before-state baseline", () => {
  const rows = syntheticCrowdingRows(4, { includeBaseline: true });
  const teeth = Object.keys(demoInitialOffsets);
  assert.equal(rows.length, teeth.length * 4);
  assert.ok(rows.filter((row) => row.stage === 0).every((row) => row.x === 0 && row.y === 0));

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

test("arch helpers normalize labels, file names, and FDI quadrants", () => {
  assert.equal(normalizeArchLabel("upper"), "maxillary");
  assert.equal(normalizeArchLabel("mandibular"), "mandibular");
  assert.equal(normalizeArchLabel("unknown"), null);
  assert.equal(inferArchFromName("sample-test-case-upper.stl"), "maxillary");
  assert.equal(inferArchFromName("scan_l.stl"), "mandibular");
  assert.equal(inferArchFromName("scan.stl"), null);
  assert.equal(archFromTooth("11"), "maxillary");
  assert.equal(archFromTooth("38"), "mandibular");
  assert.equal(archFromTooth("99"), null);
});
