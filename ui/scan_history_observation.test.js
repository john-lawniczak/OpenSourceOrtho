import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { loadHistoryObservation } from "./scan_history_observation.js";

test("local cleanup verifies both the selected H4 source and its own bytes; absence uses explicit original H4", async t => {
  const root = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-02/captures/fusion-h-4/", import.meta.url);
  const manifest = JSON.parse(readFileSync(new URL("manifest.json", root)));
  const provenance = JSON.parse(readFileSync(new URL("source-metadata.json", root)));
  const bytes = new TextEncoder().encode("original H4 fixture").buffer;
  const hash = value => createHash("sha256").update(new Uint8Array(value)).digest("hex");
  manifest.scans[0].sha256 = provenance.surfaces[0].sha256 = hash(bytes);
  const trimmed = new TextEncoder().encode("trimmed H4 fixture").buffer;
  let record = { available: true, source_sha256: hash(bytes), sha256: hash(trimmed),
    stl_base64: Buffer.from(trimmed).toString("base64"), filename: "trimmed.stl" };
  t.mock.method(globalThis, "fetch", async url => ({ ok: true, status: 200,
    json: async () => url.endsWith("lower-cleaned") ? record : url.endsWith("/manifest.json") ? manifest : provenance,
    arrayBuffer: async () => bytes }));
  const scan = await loadHistoryObservation("lower");
  assert.equal(scan.surfaceDescription, "cleaned H4 lower");
  assert.equal(scan.sha256, hash(trimmed));
  assert.equal(scan.sourceSha256, hash(bytes));
  record.source_sha256 = "0".repeat(64);
  await assert.rejects(loadHistoryObservation("lower"), /another source/);
  record.source_sha256 = hash(bytes); record.sha256 = "0".repeat(64);
  await assert.rejects(loadHistoryObservation("lower"), /integrity/);
  record = { available: false };
  assert.equal((await loadHistoryObservation("lower")).surfaceDescription, "original H4 lower");
});
