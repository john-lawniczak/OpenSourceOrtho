import test from "node:test";
import assert from "node:assert/strict";

import {
  buildProximityScans,
  hasBothArches,
  proximitySummary,
  registeredOffsetForViewer,
  registrationActionable,
} from "./proximity.js";

test("buildProximityScans prefers server URLs and carries the arch", () => {
  const scans = buildProximityScans([
    { name: "upper.stl", url: "/api/mesh/u", arch: "maxillary", asset: { id: "asset-u" } },
    { name: "lower.stl", arch: "mandibular" },
  ]);
  assert.deepEqual(scans, [
    { reference: "asset-u", arch: "maxillary" },
    { reference: "lower.stl", arch: "mandibular" },
  ]);
});

test("hasBothArches requires an upper and a lower", () => {
  assert.equal(hasBothArches([{ arch: "maxillary" }, { arch: "mandibular" }]), true);
  assert.equal(hasBothArches([{ arch: "maxillary" }]), false);
  assert.equal(hasBothArches([{ arch: "maxillary" }, { arch: "maxillary" }]), false);
  assert.equal(hasBothArches([]), false);
});

test("proximitySummary reports counts and the not-force framing", () => {
  const summary = proximitySummary({
    registration: { mode: "as-scanned" },
    proximity: { aligned_to_scan: true, counts: { contact: 3, near: 2, clearance: 5 } },
  });
  assert.match(summary, /3 touching/);
  assert.match(summary, /2 near/);
  assert.match(summary, /not bite force/i);
});

test("proximitySummary flags a hidden estimated overlay", () => {
  const summary = proximitySummary({
    registration: { mode: "estimated" },
    proximity: { aligned_to_scan: false, counts: { contact: 1, near: 1, clearance: 1 } },
  });
  assert.match(summary, /estimated alignment/);
  assert.match(summary, /hidden/);
});

test("registeredOffsetForViewer maps an estimated offset to viewer axes", () => {
  // scan (dx,dy,dz) -> viewer (dx, dz, -dy)
  const offset = registeredOffsetForViewer({ approximate: true, lower_offset: [2, 4, 6] });
  assert.deepEqual(offset, { x: 2, y: 6, z: -4 });
  assert.equal(registrationActionable({ approximate: true, lower_offset: [2, 4, 6] }), true);
});

test("registeredOffsetForViewer is null when applying it would do nothing", () => {
  // As-scanned (identity) — already occluding, nothing to move.
  assert.equal(registeredOffsetForViewer({ approximate: false, lower_offset: [0, 0, 0] }), null);
  // Estimated but zero offset.
  assert.equal(registeredOffsetForViewer({ approximate: true, lower_offset: [0, 0, 0] }), null);
  // Missing / malformed.
  assert.equal(registeredOffsetForViewer(null), null);
  assert.equal(registeredOffsetForViewer({ approximate: true, lower_offset: [1, 2] }), null);
  assert.equal(registrationActionable({ approximate: false, lower_offset: [0, 0, 0] }), false);
});
