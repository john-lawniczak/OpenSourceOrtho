import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { weekTwentyOneMetadata, loadWeekTwentyOneScan } from "./scan_week_twenty_one.js";
import { historyFrame } from "./scan_history.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";
import { placeHistoryObservation } from "./scan_history_placement.js";
import * as THREE from "./vendor/three.module.js";

const folder = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-03/", import.meta.url);
const json = name => JSON.parse(readFileSync(new URL(name, folder)));
const records = () => [json("manifest.json"), json("source-metadata.json")];

test("week 21 identity rejects mixed visits, arches and hashes", () => {
  const [manifest, source] = records();
  const scan = weekTwentyOneMetadata(manifest, source, "upper");
  assert.equal(scan.date, "2026-11-23");
  assert.equal(scan.units, "unverified");
  assert.equal(scan.reportedWeek, 21);
  assert.equal(scan.validation, null);
  for (const change of [s => s.reported_week = 7, s => s.specimen_id = "other",
    s => s.surfaces[0].sha256 = "0".repeat(64), s => s.surfaces[0].arch = "mandibular",
    s => s.coordinate_frame.export_label = "shell_teethup"]) {
    const altered = structuredClone(source); change(altered);
    assert.throws(() => weekTwentyOneMetadata(manifest, altered, "upper"), /inconsistent/);
  }
  assert.throws(() => weekTwentyOneMetadata(manifest, source, "bite"));
});

test("later weeks neither reuse a different observation nor extrapolate the early fit", () => {
  const scan = weekTwentyOneMetadata(...records(), "lower");
  const pair = [{}, {}, scan], motion = { simulation: {} };
  for (const week of [8, 17, 18, 19, 20]) assert.equal(historyFrame(week, pair, motion).kind, "unavailable");
  assert.equal(historyFrame(21, pair, motion, true).scan, scan);
  assert.equal(historyFrame(21, pair, motion).fraction, 0);
  assert.equal(historyFrame(21, [{},{},{reportedWeek:18}], motion).kind, "unavailable");
  assert.throws(() => historyFrame(22, pair));
});

test("week 21 load verifies exact bytes and does not fall back to another visit", async t => {
  let corrupt = false;
  const requests = [];
  t.mock.method(globalThis, "fetch", async url => {
    requests.push(url);
    const name = url.split("/").at(-1);
    if (name.endsWith("json")) return new Response(JSON.stringify(json(name)));
    const bytes = readFileSync(new URL(name, folder));
    if (corrupt) bytes[100] ^= 1;
    return new Response(bytes);
  });
  const scan = await loadWeekTwentyOneScan("lower");
  assert.equal(scan.bytes.byteLength, 13802584);
  corrupt = true;
  await assert.rejects(loadWeekTwentyOneScan("upper"), /integrity/);
  assert.ok(requests.every(url => url.includes("visits/progress-03/")));
});

test("combined week 21 preserves shared source coordinates despite older arch placement", () => {
  const [manifest, source] = records();
  for (const arch of ["upper", "lower"]) {
    const scan = weekTwentyOneMetadata(manifest, source, arch);
    const file = readFileSync(new URL(`progress-03-${arch}.stl`, folder));
    scan.bytes = file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength);
    const group = new THREE.Group(); group.userData.historyCombined = true;
    group.position.set(7, arch === "upper" ? 40 : -40, 13);
    group.rotation.z = arch === "upper" ? Math.PI : 0;
    const mesh = new THREE.Mesh(comparisonGeometry(scan)); group.add(mesh);
    placeHistoryObservation(mesh, group, scan);
    const original = new DataView(scan.bytes);
    for (const face of [0, 100, 10000]) {
      const offset = 84 + face * 50 + 12;
      const expected = new THREE.Vector3(original.getFloat32(offset, true),
        original.getFloat32(offset + 8, true), -original.getFloat32(offset + 4, true))
        .sub(new THREE.Vector3().fromArray(scan.sharedFrameCenter));
      const actual = new THREE.Vector3().fromBufferAttribute(mesh.geometry.attributes.position, face * 3)
        .applyMatrix4(mesh.matrixWorld);
      assert.ok(actual.distanceTo(expected) < 1e-4);
    }
    assert.ok(Math.abs(mesh.matrixWorld.determinant() - 1) < 1e-10);
    mesh.geometry.dispose(); mesh.material.dispose();
  }
});
