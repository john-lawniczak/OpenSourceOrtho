import test from "node:test";
import assert from "node:assert/strict";

import { buildProximityScans, hasBothArches, proximitySummary } from "./proximity.js";

test("buildProximityScans prefers server URLs and carries the arch", () => {
  const scans = buildProximityScans([
    { name: "upper.stl", url: "/api/mesh/u", arch: "maxillary" },
    { name: "lower.stl", arch: "mandibular" },
  ]);
  assert.deepEqual(scans, [
    { reference: "/api/mesh/u", arch: "maxillary" },
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
