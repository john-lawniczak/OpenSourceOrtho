import test from "node:test";
import assert from "node:assert/strict";
import { captureWorkspace, restoreWorkspace } from "./profile_snapshot.js";

test("progress keeps applied inputs and files but excludes credentials and transient requests", () => {
  const state = { sample: { active: false }, rows: [{ tooth: "11", x: .1 }],
    files: [new Blob(["scan bytes"])], guided: { step: "details", excludedTeeth: ["12"] },
    segmentation: { busy: true, applied: { tooth_meshes: [] }, missingTeeth: "18" },
    generation: { busy: true, notes: "discussion", result: "transient" },
    chat: { apiKey: "secret", agentAccessEnabled: true }, lastEval: { transient: true } };
  const fields = new Map();
  const doc = { getElementById: id => {
    if (!fields.has(id)) fields.set(id, { value: "", checked: false });
    return fields.get(id);
  } };
  doc.getElementById("planTitle").value = "Family profile";
  const snapshot = captureWorkspace(state, doc);
  assert.ok(!JSON.stringify(snapshot).includes("secret"));
  assert.equal(snapshot.values.segmentation.busy, undefined);
  assert.equal(snapshot.values.generation.result, undefined);
  assert.equal(snapshot.values.files[0].size, 10);
  state.rows[0].x = 2;
  assert.equal(snapshot.values.rows[0].x, .1);
  const restored = { guided: {}, segmentation: { busy: false }, generation: { busy: false } };
  restoreWorkspace(snapshot, restored, doc);
  assert.equal(restored.rows[0].x, .1);
  assert.equal(restored.segmentation.busy, false);
  assert.equal(doc.getElementById("planTitle").value, "Family profile");
});
test("sample and pending previews cannot replace personal progress", () => {
  assert.equal(captureWorkspace({ sample: { active: true } }, {}), null);
  assert.equal(captureWorkspace({ sample: { active: false }, goalPreview: {} }, {}), null);
});
