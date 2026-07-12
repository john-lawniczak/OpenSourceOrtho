import test from "node:test";
import assert from "node:assert/strict";

import { trustStatusItems, trustStatusMarkup } from "./trust_status.js";

function baseState() {
  return {
    files: [], scanSources: [], scanUnits: "unverified", useDemoMeshes: false,
    rows: [], sample: { active: false }, generation: { result: null },
    segmentation: { proposal: null, applied: null },
    availability: {}, derivedAnatomy: null, lastEval: null,
  };
}

test("trust status fails closed before evaluation", () => {
  const items = trustStatusItems(baseState());
  assert.deepEqual(items.map((entry) => entry.value), [
    "Not evaluated", "Unverified", "No scan", "Not proposed",
    "Unavailable", "No active plan", "Not evaluated",
  ]);
});

test("trust status reports known inputs without implying approval", () => {
  const state = baseState();
  state.scanSources = [{ name: "upper.stl" }];
  state.scanUnits = "mm";
  state.rows = [{ stage: 0, tooth: "11" }];
  state.segmentation.applied = { tooth_meshes: [{}, {}] };
  state.lastEval = {
    review_tier: { label: "Root/bone-aware review", root_bone_aware: true },
    print_export: {
      ready: true,
      manufacturing_readiness: { verdict: "CONSISTENT" },
    },
  };
  const values = trustStatusItems(state).map((entry) => entry.value);
  assert.ok(values.includes("Confirmed mm"));
  assert.ok(values.includes("Applied draft · 2"));
  assert.ok(values.includes("Inputs consistent"));
  assert.ok(!values.some((value) => /safe|approved/i.test(value)));
});

test("trust status exposes local segmentation work in progress", () => {
  const state = baseState();
  state.segmentation.busy = true;
  assert.equal(trustStatusItems(state)[3].value, "Processing locally…");
});

test("trust status markup escapes values and links to detail regions", () => {
  const markup = trustStatusMarkup([
    { label: "Geometry", value: "<scan>", target: "scanMetadata", tone: "known" },
  ]);
  assert.match(markup, /href="#scanMetadata"/);
  assert.doesNotMatch(markup, /<scan>/);
});

test("every trust status item links to a detail region", () => {
  const items = trustStatusItems(baseState());
  assert.equal(items.length, 7);
  assert.ok(items.every((entry) => entry.target && !entry.target.startsWith("#")));
  assert.equal((trustStatusMarkup(items).match(/href="#/g) || []).length, 7);
});
