import test from "node:test";
import assert from "node:assert/strict";
import { syntheticToothGeometry, toothProfile } from "./tooth_geometry.js";
import { FDI_TEETH } from "./tooth_selection.js";

test("all permanent schematic teeth have finite surfaces and outward normals", () => {
  for (const tooth of FDI_TEETH) {
    const geometry = syntheticToothGeometry(tooth);
    for (const name of ["position", "normal"]) {
      assert.ok([...geometry.getAttribute(name).array].every(Number.isFinite), `${tooth}: ${name}`);
    }
    assert.ok(geometry.boundingBox.max.y > 1);
    assert.ok(geometry.boundingBox.min.y < -1);
    const normals = geometry.getAttribute("normal");
    // First wall ring starts on the positive x face.
    assert.ok(normals.getX(0) > 0, `${tooth}: crown should face out`);
  }
});

test("schematic tooth classes have distinct silhouettes and branching roots", () => {
  assert.equal(toothProfile("16").roots, 3);
  assert.equal(toothProfile("46").roots, 2);
  assert.equal(toothProfile("11").roots, 1);
  assert.ok(toothProfile("16").width > toothProfile("11").width);
  assert.ok(toothProfile("13").root > toothProfile("11").root);
  assert.notEqual(syntheticToothGeometry("11"), syntheticToothGeometry("12"));
  assert.equal(syntheticToothGeometry("11"), syntheticToothGeometry("21"));
});
