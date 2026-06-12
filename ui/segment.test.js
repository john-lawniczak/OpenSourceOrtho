import test from "node:test";
import assert from "node:assert/strict";

import { applySegmentation, cbctPriorNote, isValidFdi, parseMissingTeeth, setSegmentInclude, setSegmentToothEdit } from "./segment.js";
import { state } from "./state.js";

test("parseMissingTeeth keeps valid FDI, drops junk, de-duplicates", () => {
  assert.deepEqual(parseMissingTeeth("15, 38"), ["15", "38"]);
  assert.deepEqual(parseMissingTeeth("15 15  15"), ["15"]);
  assert.deepEqual(parseMissingTeeth(" 15 , bad, 9, 21 "), ["15", "21"]);
  assert.deepEqual(parseMissingTeeth(""), []);
  assert.deepEqual(parseMissingTeeth(null), []);
});

function seedProposal() {
  state.segmentation.proposal = {
    plan_fragment: {
      mesh_assets: [{ id: "a1" }, { id: "a2" }, { id: "a3" }],
      tooth_meshes: [
        { tooth: { system: "FDI", value: "11" }, mesh_asset_id: "a1" },
        { tooth: { system: "FDI", value: "12" }, mesh_asset_id: "a2" },
        { tooth: { system: "FDI", value: "13" }, mesh_asset_id: "a3" },
      ],
    },
    teeth: [
      { mesh_asset_id: "a1", tooth: "11" },
      { mesh_asset_id: "a2", tooth: "12" },
      { mesh_asset_id: "a3", tooth: "13" },
    ],
  };
  state.segmentation.edits = {
    a1: { tooth: "11", included: true },
    a2: { tooth: "12", included: true },
    a3: { tooth: "13", included: true },
  };
  state.segmentation.applied = null;
}

test("isValidFdi accepts two-digit 1-8 and rejects everything else", () => {
  for (const ok of ["11", "48", "27"]) assert.ok(isValidFdi(ok), ok);
  for (const bad of ["99", "9", "ab", "", "111", "10"]) assert.ok(!isValidFdi(bad), bad);
});

test("applySegmentation includes all valid teeth by default", () => {
  seedProposal();
  applySegmentation();
  assert.equal(state.segmentation.applied.tooth_meshes.length, 3);
  assert.equal(state.segmentation.applied.mesh_assets.length, 3);
});

test("applySegmentation respects include checkboxes", () => {
  seedProposal();
  setSegmentInclude("a2", false);
  applySegmentation();
  const ids = state.segmentation.applied.mesh_assets.map((a) => a.id).sort();
  assert.deepEqual(ids, ["a1", "a3"]);
  assert.equal(state.segmentation.applied.tooth_meshes.length, 2);
});

test("applySegmentation applies a corrected tooth number", () => {
  seedProposal();
  setSegmentToothEdit("a1", "21");
  applySegmentation();
  const link = state.segmentation.applied.tooth_meshes.find((m) => m.mesh_asset_id === "a1");
  assert.equal(link.tooth.value, "21");
});

test("applySegmentation skips an invalid FDI correction instead of breaking the plan", () => {
  seedProposal();
  setSegmentToothEdit("a3", "99");
  applySegmentation();
  const ids = state.segmentation.applied.tooth_meshes.map((m) => m.mesh_asset_id);
  assert.ok(!ids.includes("a3"));
  assert.equal(state.segmentation.applied.tooth_meshes.length, 2);
  assert.match(state.segmentation.status, /invalid FDI/i);
});

test("applySegmentation skips duplicate FDI corrections", () => {
  seedProposal();
  setSegmentToothEdit("a2", "11");
  applySegmentation();
  const values = state.segmentation.applied.tooth_meshes.map((m) => m.tooth.value);
  assert.deepEqual(values, ["11", "13"]);
  assert.match(state.segmentation.status, /duplicate tooth number/i);
});

test("applySegmentation yields no fragment when nothing valid is selected", () => {
  seedProposal();
  for (const id of ["a1", "a2", "a3"]) setSegmentInclude(id, false);
  applySegmentation();
  assert.equal(state.segmentation.applied, null);
});

test("cbctPriorNote summarizes prior usage per arch", () => {
  assert.equal(cbctPriorNote(null), "");
  assert.equal(cbctPriorNote({ used: false, status: "no plan supplied" }), "");
  const note = cbctPriorNote({
    used: true,
    arches: { maxillary: { boundary_count: 13, mean_agreement: 0.82 } },
  });
  assert.match(note, /maxillary: 13 CBCT boundary prior\(s\), agreement 0.82/);
  const noAgreement = cbctPriorNote({
    used: true,
    arches: { mandibular: { boundary_count: 5, mean_agreement: null } },
  });
  assert.match(noAgreement, /mandibular: 5 CBCT boundary prior\(s\)/);
  assert.doesNotMatch(noAgreement, /agreement/);
});
