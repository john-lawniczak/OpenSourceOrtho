import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "./vendor/three.module.js";
import { placeHistoryObservation } from "./scan_history_placement.js";

test("history placement is rigid, deterministic, and leaves earlier visits and source vertices intact", () => {
  for (const arch of ["upper", "lower"]) {
    const baseline = new THREE.Mesh(new THREE.BoxGeometry(40, 15, 35));
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(42, 20, 37));
    const positions = mesh.geometry.attributes.position.array.slice();
    const prior = baseline.matrix.clone();
    const scan = { arch, historyDisplay: true };
    placeHistoryObservation(mesh, baseline, scan);
    const matrix = mesh.matrix.clone();
    assert.ok(Math.abs(matrix.determinant() - 1) < 1e-10);
    assert.deepEqual(mesh.scale.toArray(), [1, 1, 1]);
    assert.deepEqual(mesh.geometry.attributes.position.array, positions);
    assert.deepEqual(baseline.matrix, prior);
    const fresh = new THREE.Mesh(mesh.geometry);
    placeHistoryObservation(fresh, baseline, scan);
    assert.deepEqual(fresh.matrix, matrix);
    baseline.geometry.dispose(); mesh.geometry.dispose();
  }
});
