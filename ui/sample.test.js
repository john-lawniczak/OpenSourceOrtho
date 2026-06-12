import test from "node:test";
import assert from "node:assert/strict";

import { prepareSampleSegmentation } from "./sample.js";
import { state } from "./state.js";

// A minimal /api/segment proposal: two anterior teeth with included edits, the
// shape proposeSegmentation/applySegmentation consume.
function proposalPayload() {
  return {
    ok: true,
    overall_confidence: 0.7,
    teeth: [
      { mesh_asset_id: "a1", tooth: "11", confidence: 0.7 },
      { mesh_asset_id: "a2", tooth: "21", confidence: 0.7 },
    ],
    plan_fragment: {
      mesh_assets: [{ id: "a1" }, { id: "a2" }],
      tooth_meshes: [
        { tooth: { system: "FDI", value: "11" }, mesh_asset_id: "a1" },
        { tooth: { system: "FDI", value: "21" }, mesh_asset_id: "a2" },
      ],
    },
  };
}

function enterFakeSample() {
  state.sample.active = true;
  state.scanSources = [
    { name: "upper.stl", url: "./example-scans/upper.stl", arch: "maxillary" },
  ];
  state.scanArch = "";
  state.view = "overlay";
  state.segmentation = { busy: false, status: "", proposal: null, edits: {}, applied: null };
  state.availability = { ...state.availability, segmented_teeth: false };
}

function stubFetch(payload) {
  globalThis.fetch = async () => ({ ok: true, json: async () => payload });
}

test("prepareSampleSegmentation applies the draft so per-tooth movement renders", async () => {
  enterFakeSample();
  stubFetch(proposalPayload());

  const ready = await prepareSampleSegmentation();

  assert.equal(ready, true);
  assert.equal(state.segmentation.applied.tooth_meshes.length, 2);
  assert.equal(state.availability.segmented_teeth, true);
  assert.match(state.sampleStatus, /stage slider/);
  assert.match(state.segmentation.status, /applied for you/);
});

test("prepareSampleSegmentation never applies after the sample exits mid-run", async () => {
  enterFakeSample();
  // The user exits the sample while the segmenter request is in flight.
  globalThis.fetch = async () => {
    state.sample.active = false;
    return { ok: true, json: async () => proposalPayload() };
  };

  const ready = await prepareSampleSegmentation();

  assert.equal(ready, false);
  assert.equal(state.segmentation.applied, null);
  assert.equal(state.availability.segmented_teeth, false);
});

test("prepareSampleSegmentation falls back to arrows when segmentation fails", async () => {
  enterFakeSample();
  stubFetch({ ok: false, errors: ["segmentation failed"] });

  const ready = await prepareSampleSegmentation();

  assert.equal(ready, false);
  assert.equal(state.segmentation.applied, null);
  assert.match(state.sampleStatus, /markers and arrows/);
});

test("prepareSampleSegmentation is a no-op outside the sample", async () => {
  enterFakeSample();
  state.sample.active = false;
  let fetched = false;
  globalThis.fetch = async () => {
    fetched = true;
    return { ok: true, json: async () => proposalPayload() };
  };

  assert.equal(await prepareSampleSegmentation(), false);
  assert.equal(fetched, false);
});
