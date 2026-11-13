import test from "node:test";
import assert from "node:assert/strict";
import { registerUploadedScans } from "./upload_registration.js";

function workspace() {
  return { files: [{ name: "upper.stl" }], scanArch: "", sample: { active: false }, scanSources: [] };
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
test("a slower old upload cannot replace a newer scan", async () => {
  const state = workspace(), slow = deferred();
  const pending = registerUploadedScans(state, state.files, () => slow.promise);
  state.files = [{ name: "lower.stl" }];
  await registerUploadedScans(state, state.files, async () => ({ ok: true, url: "/new" }));
  slow.resolve({ ok: true, url: "/old" });
  assert.equal(await pending, false);
  assert.equal(state.scanSources[0].url, "/new");
});
test("an upload failure cannot change sample sources or status", async () => {
  const state = workspace(), slow = deferred();
  const pending = registerUploadedScans(state, state.files, () => slow.promise);
  state.sample.active = true; state.uploadStorageStatus = "Sample loaded";
  state.scanSources = [{ url: "/sample" }];
  slow.reject(new Error("upload failed"));
  assert.equal(await pending, false);
  assert.equal(state.scanSources[0].url, "/sample");
  assert.equal(state.uploadStorageStatus, "Sample loaded");
});
test("an arch change during a batch cannot give its scans inconsistent metadata", async () => {
  const state = workspace(), arches = [];
  state.files = [{ name: "a.stl" }, { name: "b.stl" }]; state.scanArch = "maxillary";
  await registerUploadedScans(state, state.files, async (_, options) => {
    arches.push(options.arch); state.scanArch = "mandibular"; return { ok: true, url: "/scan" };
  });
  assert.deepEqual(arches, ["maxillary", "maxillary"]);
});
test("server registration does not hide a failed browser save", async () => {
  const state = workspace();
  await registerUploadedScans(state, state.files, async () => ({ ok: true, url: "/scan" }), "Browser storage failed: quota exceeded");
  assert.match(state.uploadStorageStatus, /Registered 1/);
  assert.match(state.uploadStorageStatus, /quota exceeded/);
});
