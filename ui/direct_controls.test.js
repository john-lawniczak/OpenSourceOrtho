import test from "node:test";
import assert from "node:assert/strict";

import {
  CONTROL_LIMITS,
  applyDirectControl,
  clampControl,
  controlGate,
  proposeArchResponse,
  setDirectControl,
} from "./direct_controls.js";

test("controlGate fails closed without units and reviewed segmentation", () => {
  const gate = controlGate({ unitsConfirmed: false, segmentedTeeth: false });

  assert.equal(gate.allowed, false);
  assert.match(gate.blockers.join(" "), /millimeters/);
  assert.match(gate.blockers.join(" "), /segmentation/);
  assert.match(gate.warnings.join(" "), /root\/bone response/);
});

test("direct controls clamp each movement family", () => {
  assert.equal(clampControl("x", CONTROL_LIMITS.x + 10), CONTROL_LIMITS.x);
  assert.equal(clampControl("rotation", -CONTROL_LIMITS.rotation - 10), -CONTROL_LIMITS.rotation);
  assert.equal(clampControl("tip", Number.NaN), 0);
});

test("applyDirectControl authors translation, intrusion, and rotation axes", () => {
  let rows = [];
  rows = applyDirectControl(rows, "11", "x", 0.2);
  rows = applyDirectControl(rows, "11", "z", -0.1);
  rows = applyDirectControl(rows, "11", "rotation", 1.5);
  rows = applyDirectControl(rows, "11", "tip", 0.5);
  rows = applyDirectControl(rows, "11", "torque", -0.5);

  assert.equal(rows.length, 1);
  assert.deepEqual(
    [rows[0].x, rows[0].z, rows[0].rotation, rows[0].tip, rows[0].torque],
    [0.2, -0.1, 1.5, 0.5, -0.5],
  );
});

test("setDirectControl replaces an axis value without mutating input", () => {
  const rows = applyDirectControl([], "21", "x", 0.2);
  const next = setDirectControl(rows, "21", "x", 1.1);

  assert.equal(rows[0].x, 0.2);
  assert.equal(next[0].x, 1.1);
});

test("arch response proposes same-arch adjustments when gates pass", () => {
  const rows = [
    { stage: 0, tooth: "11", x: 0, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
    { stage: 0, tooth: "21", x: 0, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
    { stage: 0, tooth: "31", x: 0, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
  ];
  const result = proposeArchResponse(rows, "11", 0.3, {
    unitsConfirmed: true,
    segmentedTeeth: true,
    rootsAvailable: true,
    reviewedAnatomy: true,
  });

  assert.deepEqual(result.proposed.map((item) => item.tooth), ["11", "21"]);
  assert.equal(result.rows.find((row) => row.tooth === "11" && row.stage === 1).x, -0.3);
  assert.equal(result.rows.find((row) => row.tooth === "21" && row.stage === 1).x, 0.3);
  assert.match(result.warnings.join(" "), /contacts\/spacing/);
});

test("arch response returns warnings and no proposal when gates fail", () => {
  const result = proposeArchResponse([], "11", 0.2, {
    unitsConfirmed: false,
    segmentedTeeth: false,
  });

  assert.equal(result.proposed.length, 0);
  assert.match(result.warnings.join(" "), /millimeters/);
});

