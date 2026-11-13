import test from "node:test";
import assert from "node:assert/strict";

import { applySampleRootBoneFixture, prepareSampleSegmentation } from "./sample.js";
import { state } from "./state.js";

// Painted regions remain drafts when loaded into the sample workspace.
function proposalPayload() {
  return {
    ok: true,
    scan_sources: [{ name: "progress-01-upper.stl", asset: { units: "unverified" } }],
    annotations: [{ arch: "upper", origin: "private-archive" }],
    teeth: [
      { mesh_asset_id: "a1", tooth: "11", confidence: 0.7 },
      { mesh_asset_id: "a2", tooth: "21", confidence: 0.7 },
    ],
    plan_fragment: {
      mesh_assets: [{ id: "a1" }, { id: "a2" }],
      tooth_meshes: [
        { tooth: { system: "FDI", value: "11" }, mesh_asset_id: "a1", reviewed: false },
        { tooth: { system: "FDI", value: "21" }, mesh_asset_id: "a2", reviewed: false },
      ],
    },
  };
}

function enterFakeSample() {
  globalThis.document = { getElementById: () => ({ value: "" }) };
  state.sample.active = true; state.sample.visit = "progress-01";
  state.scanSources = [
    { name: "upper.stl", url: "./example-scans/upper.stl", arch: "maxillary" },
  ];
  state.scanArch = "";
  state.scanUnits = "mm";
  state.view = "overlay";
  state.segmentation = { busy: false, status: "", proposal: null, edits: {}, applied: null };
  state.availability = { ...state.availability, segmented_teeth: false };
  state.fixtureMeshAssets = [];
  state.caseRecords = [];
  state.registrations = [];
  state.derivedAnatomy = null;
}

function stubFetch(payload) {
  globalThis.fetch = async () => ({ ok: true, json: async () => payload });
}

test("prepareSampleSegmentation loads painted regions without inventing review or movement", async () => {
  enterFakeSample();
  stubFetch(proposalPayload());

  const ready = await prepareSampleSegmentation();

  assert.equal(ready, true);
  assert.equal(state.segmentation.applied.tooth_meshes.length, 2);
  assert.equal(state.availability.segmented_teeth, false);
  assert.equal(state.scanUnits, "unverified");
  assert.ok(state.segmentation.applied.tooth_meshes.every(link => !link.reviewed));
  assert.ok(state.rows.every(row => row.x === 0 && row.rotation === 0));
  assert.match(state.sampleStatus, /stage slider/);
  assert.match(state.segmentation.status, /loaded as drafts/);
});

test("applySampleRootBoneFixture loads CBCT registration and anatomy into isolated sample state", async () => {
  enterFakeSample();
  globalThis.fetch = async () => ({
    ok: true,
    json: async () => ({
      case_records: [{ id: "cb", kind: "cbct" }],
      mesh_assets: [{ id: "bone" }],
      registrations: [{ id: "reg" }],
      derived_anatomy: { roots: [{ tooth: { system: "FDI", value: "11" } }] },
      availability_patch: { cbct: true, roots: true },
    }),
  });

  const loaded = await applySampleRootBoneFixture();

  assert.equal(loaded, true);
  assert.equal(state.caseRecords.length, 1);
  assert.equal(state.fixtureMeshAssets.length, 1);
  assert.equal(state.registrations.length, 1);
  assert.equal(state.derivedAnatomy.roots.length, 1);
  assert.equal(state.availability.cbct, true);
  assert.equal(state.availability.roots, true);
  assert.match(state.recordUploadStatus, /root\/bone fixture loaded/);
});

test("prepareSampleSegmentation never applies after the sample exits mid-run", async () => {
  enterFakeSample();
  // The user exits the sample while the segmenter request is in flight.
  stubFetch(proposalPayload());
  const fetchJob = globalThis.fetch;
  globalThis.fetch = async url => { state.sample.active = false; return fetchJob(url); };

  const ready = await prepareSampleSegmentation();

  assert.equal(ready, false);
  assert.equal(state.segmentation.applied, null);
  assert.equal(state.availability.segmented_teeth, false);
});

test("prepareSampleSegmentation keeps scans visible when segmentation fails", async () => {
  enterFakeSample();
  stubFetch({ ok: false, errors: ["segmentation failed"] });

  const ready = await prepareSampleSegmentation();

  assert.equal(ready, false);
  assert.equal(state.segmentation.applied, null);
  assert.match(state.sampleStatus, /segmentation failed/);
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
test("failed visit reload preserves the last painted workspace and exploratory edits", async () => {
  enterFakeSample(); stubFetch(proposalPayload());
  await prepareSampleSegmentation();
  state.rows[0].x = 0.2;
  const applied = state.segmentation.applied, sources = state.scanSources;
  state.goalPreview = { status: "preview" };
  stubFetch({ ok: false, errors: ["unavailable"] });
  assert.equal(await prepareSampleSegmentation({ visit: "initial" }), false);
  assert.equal(state.sample.visit, "progress-01");
  assert.equal(state.segmentation.applied, applied);
  assert.equal(state.scanSources, sources);
  assert.equal(state.rows[0].x, 0.2);
  assert.equal(state.goalPreview.status, "preview");
});
test("duplicate loads cannot reset a workspace twice and fallback reports its actual visit", async () => {
  enterFakeSample(); let resolve, calls = 0;
  globalThis.fetch = () => { calls++; return new Promise(done => { resolve = done; }); };
  const pending = prepareSampleSegmentation({ allowFallback: true });
  assert.equal(await prepareSampleSegmentation(), false);
  resolve({ ok: true, json: async () => ({ ...proposalPayload(), visit: "initial", notice: "Using baseline" }) });
  assert.equal(await pending, true);
  assert.equal(calls, 1);
  assert.equal(state.sample.visit, "initial");
  assert.match(state.sampleStatus, /Using baseline/);
  assert.equal(state.segmentation.busy, false);
});

test("an old fixture response cannot populate a restarted sample", async (t) => {
  enterFakeSample();
  let resolve;
  t.mock.method(globalThis, 'fetch', () => new Promise(done => { resolve = done; }));
  const pending = applySampleRootBoneFixture();
  enterFakeSample(); // New segmentation/session object, still sample.active=true.
  resolve({ ok: true, json: async () => ({ case_records: [{ id: 'old-case' }] }) });
  assert.equal(await pending, false);
  assert.deepEqual(state.caseRecords, []);
});

test("an old fixture failure cannot overwrite the restored profile status", async (t) => {
  enterFakeSample();
  let reject;
  t.mock.method(globalThis, 'fetch', () => new Promise((_, no) => { reject = no; }));
  const pending = applySampleRootBoneFixture();
  state.sample.active = false;
  state.recordUploadStatus = 'Personal scan loaded';
  reject(new Error('old request failed'));
  assert.equal(await pending, false);
  assert.equal(state.recordUploadStatus, 'Personal scan loaded');
});
