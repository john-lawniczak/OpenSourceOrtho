import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { inputValidationText, loadObservedPair, observedPairMetadata } from "./scan_comparison_data.js";
import { historyFrame, historyCamera } from "./scan_history.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";

const root = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/", import.meta.url);
const files = ["manifest.json", "longitudinal-record.json", "derived/progress-01-comparison.json"];
const records = () => files.map(file => JSON.parse(readFileSync(new URL(file, root))));

test("observed visits retain actual dates, labels, hashes, and documented proper rotations", () => {
  const pair = observedPairMetadata(...records(), "upper");
  assert.deepEqual(pair.map(scan => scan.filename), ["initial-upper.stl", "progress-01-upper.stl"]);
  assert.deepEqual(pair.map(scan => scan.date), ["2026-06-05", "2026-09-17"]);
  assert.deepEqual(pair.map(scan => scan.label), ["Week 1 / baseline", "Reported week 7"]);
  assert.match(inputValidationText(pair[0].validation), /validated, confirmed by the contributor/);
  assert.deepEqual(pair.map(scan => scan.rotation), [[-1, 1, -1], [1, 1, 1]]);
  assert.equal(pair[1].units, "unverified");
  assert.throws(() => observedPairMetadata(...records(), "both"));
});

test("validation wording requires a matching source hash and confirmed provenance", () => {
  const items = records();
  items[1].comparison.input_validation.scans["initial-upper.stl"] = "0".repeat(64);
  const pair = observedPairMetadata(...items, "upper");
  assert.equal(pair[0].validation, null);
  assert.match(inputValidationText(pair[0].validation), /No contributor-confirmed/);
  assert.match(inputValidationText({status: "unknown"}), /No contributor-confirmed/);
});

test("mismatched identity, hashes, arch, visit membership, and mirror transforms fail closed", () => {
  for (const mutate of [
    items => { items[0].specimen_id = "another-case"; },
    items => { items[0].scans[0].sha256 = "a".repeat(64); },
    items => { items[0].scans[0].arch = "mandibular"; },
    items => { items[1].events[0].files = []; },
    items => { items[2].display.rotation_diagonals["initial-upper.stl"] = [1, 1, -1]; },
  ]) {
    const items = records();
    mutate(items);
    assert.throws(() => observedPairMetadata(...items, "upper"));
  }
});

test("loading verifies actual bytes and requests only the two chosen public observations", async t => {
  const bytes = new TextEncoder().encode("test scan bytes").buffer;
  const hash = createHash("sha256").update(new Uint8Array(bytes)).digest("hex");
  const items = records();
  for (const record of [items[0], items[2]]) record.scans.forEach(scan => { scan.sha256 = hash; });
  const calls = [];
  const controller = new AbortController();
  t.mock.method(globalThis, "fetch", async (url, { signal }) => {
    assert.equal(signal, controller.signal);
    calls.push(url);
    const i = files.findIndex(file => url.endsWith(file));
    return { ok: true, json: async () => items[i], arrayBuffer: async () => bytes };
  });
  const pair = await loadObservedPair("lower", { signal: controller.signal });
  assert.equal(pair[0].bytes, bytes);
  assert.equal(calls.length, 5);
  assert.equal(calls.filter(url => url.endsWith(".stl")).length, 2);
  assert.ok(calls.filter(url => url.endsWith(".stl")).every(url => url.endsWith("lower.stl")));
  assert.ok(calls.every(url => !url.includes("private") && !url.includes("progress-02")));
  items[0].scans.forEach(scan => { scan.sha256 = "0".repeat(64); });
  items[2].scans.forEach(scan => { scan.sha256 = "0".repeat(64); });
  await assert.rejects(loadObservedPair("lower", { signal: controller.signal }), /integrity check failed/);
});

test("week navigation without an estimate never substitutes endpoint scans for missing observations", () => {
  const pair = observedPairMetadata(...records(), "upper");
  assert.equal(historyFrame(1, pair).scan, pair[0]);
  assert.equal(historyFrame(7, pair).scan, pair[1]);
  for (let week = 2; week <= 6; week++) {
    assert.deepEqual(historyFrame(week, pair), { week, index: null, scan: null,
      kind: "unavailable", fraction: (week - 1) / 6 });
  }
  for (const week of [0, 19, 1.5, NaN, Infinity, "2"]) assert.throws(() => historyFrame(week, pair));
});

test("upper front/side camera is rolled so crowns point down; lower retains upright orientation", () => {
  for (const view of ["front", "left", "right"]) {
    assert.deepEqual(historyCamera("upper", view).up, [0, -1, 0]);
    assert.deepEqual(historyCamera("lower", view).up, [0, 1, 0]);
  }
  assert.deepEqual(historyCamera("upper"), historyCamera("upper", "front"));
  for (const arch of ["upper", "lower"]) {
    const { position, up } = historyCamera(arch, "occlusal");
    assert.equal(position.reduce((sum, v, i) => sum + v * up[i], 0), 0);
  }
});

test("week 18 is a separate observation and never extrapolates the week 1–7 fit", () => {
  const scans = [...observedPairMetadata(...records(), "upper"), { label: "Week 18" }];
  const motion = { simulation: {} };
  for (let week = 8; week < 18; week++) {
    assert.deepEqual(historyFrame(week, scans, motion, true), { week, index: null, scan: null, kind: "unavailable", fraction: 0 });
  }
  assert.equal(historyFrame(18, scans, motion, true).scan, scans[2]);
  assert.equal(historyFrame(18, scans, motion, true).index, 3);
  assert.equal(historyFrame(18, scans.slice(0, 2), motion).kind, "unavailable");
});

test("display geometry preserves triangle coordinates up to proper rotation and translation", () => {
  const bytes = new TextEncoder().encode(`solid test
facet normal 0 0 1
outer loop
vertex 1 2 3
vertex 5 2 3
vertex 1 8 7
endloop
endfacet
endsolid`).buffer;
  const original = new Uint8Array(bytes).slice();
  const geometry = comparisonGeometry({ bytes, rotation: [-1, 1, -1] });
  const p = geometry.attributes.position;
  assert.equal(p.count, 3);
  assert.deepEqual([p.getX(1) - p.getX(0), p.getY(1) - p.getY(0), p.getZ(1) - p.getZ(0)], [-4, 0, 0]);
  assert.deepEqual([p.getX(2) - p.getX(0), p.getY(2) - p.getY(0), p.getZ(2) - p.getZ(0)], [0, -4, -6]);
  assert.deepEqual(new Uint8Array(bytes), original);
  geometry.dispose();
  assert.throws(() => comparisonGeometry({ bytes: new ArrayBuffer(0), rotation: [1, 1, 1] }), /no surface/);
});
