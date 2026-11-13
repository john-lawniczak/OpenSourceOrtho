import test from "node:test";
import assert from "node:assert/strict";
import { toothExampleOffsets } from "./tooth_examples.js";
import { FDI_TEETH } from "./tooth_selection.js";

test("examples retain all tooth identities and reset without retaining offsets", () => {
  for (const name of ["neutral", "crowding", "spacing", "open-bite"]) {
    const offsets = toothExampleOffsets(name);
    assert.equal(Object.keys(offsets).length, 32);
    assert.ok(FDI_TEETH.every(tooth => Object.values(offsets[tooth]).every(Number.isFinite)));
  }
  const neutral = toothExampleOffsets("neutral");
  assert.ok(Object.values(neutral).every(offset => Object.values(offset).every(value => value === 0)));
  const crowding = toothExampleOffsets("crowding");
  assert.ok(crowding["31"].x < 0 && crowding["41"].x > 0);
  assert.ok(crowding["31"].y > 0 && crowding["32"].y < 0);
  const spacing = toothExampleOffsets("spacing");
  assert.ok(spacing["11"].x < 0 && spacing["21"].x > 0);
  const open = toothExampleOffsets("open-bite");
  assert.ok(open["11"].z > 0 && open["41"].z < 0);
  assert.equal(open["16"].z, 0);
  assert.deepEqual(toothExampleOffsets("neutral"), neutral);
  assert.throws(() => toothExampleOffsets("unknown"));
});
