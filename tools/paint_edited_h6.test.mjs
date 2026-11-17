import assert from "node:assert/strict";
import test from "node:test";
import { retainedLabels } from "./paint_edited_h6.mjs";

function mesh(records) {
  return Buffer.concat([Buffer.alloc(84), ...records.map(n => Buffer.alloc(50, n))]);
}
test("removed faces stay removed, existing painting survives, patches stay unseeded", () => {
  const labels = retainedLabels(mesh([1, 2, 3, 4]), [31, 32, 33, 34], mesh([2, 4, 9]), 2, [0, 41, 0]);
  assert.deepEqual([...labels], [32, 41, 0]);
});
test("conflicting duplicate face labels remain uncertain", () => {
  assert.deepEqual([...retainedLabels(mesh([1, 1, 1]), [31, 32, 31], mesh([1]), 1, [0])], [0]);
});
test("changed retained geometry is rejected", () => {
  assert.throws(() => retainedLabels(mesh([1]), [31], mesh([2]), 1, [0]), /does not match/);
});
