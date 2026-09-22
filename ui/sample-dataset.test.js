import test from "node:test";
import assert from "node:assert/strict";
import { canonicalScanSources } from "./demo.js";
import { sampleDataset } from "./sample-dataset.js";

test("sample requests use published routes and relative engine asset references", () => {
  assert.equal(sampleDataset.pseudonym, "USER_ONE");
  assert.deepEqual(canonicalScanSources.map(scan => scan.name), ["initial-upper.stl", "initial-lower.stl"]);
  for (const scan of canonicalScanSources) {
    assert.equal(scan.url, `${sampleDataset.urlRoot}/${scan.name}`);
    assert.equal(scan.segmentReference, scan.url);
    assert.equal(scan.asset.reference, scan.url.slice(1));
    assert.ok(!scan.asset.reference.startsWith("/"));
  }
});
