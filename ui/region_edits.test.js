import test from "node:test";
import assert from "node:assert/strict";
import { RegionEdits } from "./region_edits.js";
test("brush, split, merge and undo preserve original labels and branch redo", () => {
  const original = new Uint8Array([11,11,12,0]), edits = new RegionEdits(original,"upper");
  edits.paint([0,1,2],13,11); assert.deepEqual([...edits.labels],[13,13,12,0]);
  edits.merge(13,12); assert.deepEqual([...edits.labels],[12,12,12,0]);
  edits.undo(); edits.undo(); assert.deepEqual(edits.labels,original);
  edits.redo(); edits.paint([3],14); edits.redo(); assert.deepEqual([...edits.labels],[13,13,12,14]);
  assert.deepEqual([...original],[11,11,12,0]);
});
test("corrections are hash bound and invalid paint is atomic", () => {
  const edits=new RegionEdits([11,12],"upper");
  assert.throws(()=>edits.paint([0,9],13)); assert.deepEqual([...edits.labels],[11,12]);
  assert.throws(()=>edits.paint([0],31));
  const record=edits.export("abc"); assert.equal(record.reviewed,false);
  assert.deepEqual([...RegionEdits.restore(record,"abc",2,"upper").labels],[11,12]);
  assert.throws(()=>RegionEdits.restore(record,"other",2,"upper"));
});
