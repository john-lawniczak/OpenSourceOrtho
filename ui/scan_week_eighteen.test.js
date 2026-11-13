import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { weekEighteenMetadata, loadWeekEighteenScan } from "./scan_week_eighteen.js";
const folder = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-02/", import.meta.url);
const read = name => JSON.parse(fs.readFileSync(new URL(name, folder)));
test("week 18 metadata binds the original pair, arch and reported visit without inventing dates", () => {
  const manifest = read("manifest.json"), source = read("source-metadata.json");
  const scan = weekEighteenMetadata(manifest, source, "lower");
  assert.equal(scan.filename, "visits/progress-02/progress-02-lower.stl");
  assert.equal(scan.date, "Acquisition date unknown");
  assert.equal(scan.validation, null);
  source.surfaces[1].sha256 = "0".repeat(64);
  assert.throws(() => weekEighteenMetadata(manifest, source, "lower"), /identity/);
  assert.throws(() => weekEighteenMetadata(manifest, source, "both"));
});
test("week 18 byte integrity failures are surfaced without requesting older scans", async t => {
  const calls = [], signal = new AbortController().signal;
  t.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push(url); assert.equal(options.signal, signal);
    return { ok: true, json: async () => read(url.split('/').at(-1)), arrayBuffer: async () => new Uint8Array([1, 2]).buffer };
  });
  await assert.rejects(loadWeekEighteenScan("upper", { signal }), /integrity/);
  assert.equal(calls.length, 3);
  assert.ok(calls.every(url => url.includes("visits/progress-02/")));
});

test("alternative lower painting captures retain their own identities", () => {
  for (const capture of ["fusion-h-4", "fusion-h-6"]) {
    const manifest = read(`captures/${capture}/manifest.json`), source = read(`captures/${capture}/source-metadata.json`);
    const scan = weekEighteenMetadata(manifest, source, "lower", capture);
    assert.equal(scan.capture, capture);
    assert.equal(scan.sha256, manifest.scans[0].sha256);
    assert.ok(scan.filename.includes(`captures/${capture}/`));
    assert.throws(() => weekEighteenMetadata(manifest, source, "upper", capture), /Invalid/);
    source.capture_id = "other";
    assert.throws(() => weekEighteenMetadata(manifest, source, "lower", capture), /provenance/);
  }
});
