import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sourceRotation, sourceViewContext, visibleScanView } from "./scan_source_orientation.js";

const root = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/", import.meta.url);
const manifest = JSON.parse(readFileSync(new URL("manifest.json", root)));
const comparison = JSON.parse(readFileSync(new URL("derived/progress-01-comparison.json", root)));

test("known raw scan camera conventions are content-bound and arch-specific", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async url => ({ ok: true, json: async () => url.endsWith("manifest.json") ? manifest : comparison });
  try {
    for (const arch of ["upper", "lower"]) for (const visit of ["initial", "progress-01"]) {
      const scan = manifest.scans.find(s => s.filename === `${visit}-${arch}.stl`);
      const expected = comparison.display.rotation_diagonals[scan.filename];
      assert.deepEqual(await sourceRotation(scan.sha256, arch), expected);
      assert.deepEqual(await sourceRotation(scan.sha256, arch === "upper" ? "lower" : "upper"), [1,1,1]);
      const bytes = readFileSync(new URL(scan.filename, root));
      const context = await sourceViewContext(bytes, arch);
      assert.deepEqual(context.front.up, [0,(arch === "upper" ? -1 : 1) * expected[2],0]);
    }
    assert.deepEqual(await sourceRotation("unknown", "upper"), [1,1,1]);
    assert.deepEqual(await sourceViewContext(new Uint8Array(), "unknown"), {});
    const context = { arch: "upper" };
    assert.equal(visibleScanView([{ userData: { scanView: context } }]), context);
    assert.deepEqual(visibleScanView([{ userData: { scanView: context } }, { userData: {} }]).front, { direction: [0,0,1], up: [0,1,0] });
  } finally { globalThis.fetch = original; }
});
