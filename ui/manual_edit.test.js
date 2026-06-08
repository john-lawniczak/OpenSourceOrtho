import test from "node:test";
import assert from "node:assert/strict";

import {
  NUDGE_STEP_MM,
  TARGET_LIMIT_MM,
  TARGET_STAGE,
  clampTarget,
  clearTarget,
  emptyTargetRow,
  isPlanarAxis,
  nudgeTarget,
  scaleConfirmed,
  targetFor,
  targetMagnitudeMm,
} from "./manual_edit.js";

test("scaleConfirmed only accepts confirmed mm units", () => {
  assert.equal(scaleConfirmed("mm"), true);
  assert.equal(scaleConfirmed("unverified"), false);
  assert.equal(scaleConfirmed("cm"), false);
  assert.equal(scaleConfirmed(""), false);
});

test("only x and y are authorable planar axes", () => {
  assert.equal(isPlanarAxis("x"), true);
  assert.equal(isPlanarAxis("y"), true);
  assert.equal(isPlanarAxis("z"), false);
  assert.equal(isPlanarAxis("rotation"), false);
});

test("clampTarget bounds values and rejects non-finite", () => {
  assert.equal(clampTarget(1.2), 1.2);
  assert.equal(clampTarget(TARGET_LIMIT_MM + 5), TARGET_LIMIT_MM);
  assert.equal(clampTarget(-TARGET_LIMIT_MM - 5), -TARGET_LIMIT_MM);
  assert.equal(clampTarget(Number.NaN), 0);
});

test("emptyTargetRow has zero rotation and zero vertical", () => {
  const row = emptyTargetRow("21");
  assert.equal(row.stage, TARGET_STAGE);
  assert.equal(row.tooth, "21");
  assert.deepEqual([row.x, row.y, row.z], [0, 0, 0]);
  assert.deepEqual([row.tip, row.torque, row.rotation], [0, 0, 0]);
});

test("nudgeTarget creates a target row when the tooth has none", () => {
  const rows = [];
  const next = nudgeTarget(rows, "21", "x", NUDGE_STEP_MM);
  assert.equal(rows.length, 0, "input rows are not mutated");
  assert.equal(next.length, 1);
  assert.equal(next[0].tooth, "21");
  assert.equal(next[0].stage, TARGET_STAGE);
  assert.ok(Math.abs(next[0].x - NUDGE_STEP_MM) < 1e-9);
  assert.equal(next[0].y, 0);
});

test("nudgeTarget accumulates on an existing target and never touches rotation/z", () => {
  let rows = nudgeTarget([], "11", "x", NUDGE_STEP_MM);
  rows = nudgeTarget(rows, "11", "x", NUDGE_STEP_MM);
  rows = nudgeTarget(rows, "11", "y", -NUDGE_STEP_MM);
  const row = rows.find((r) => r.tooth === "11");
  assert.ok(Math.abs(row.x - 2 * NUDGE_STEP_MM) < 1e-9);
  assert.ok(Math.abs(row.y - -NUDGE_STEP_MM) < 1e-9);
  assert.deepEqual([row.z, row.tip, row.torque, row.rotation], [0, 0, 0, 0]);
  assert.equal(rows.length, 1, "one target row per tooth");
});

test("nudgeTarget clamps to the authoring limit", () => {
  let rows = [];
  for (let i = 0; i < 100; i += 1) rows = nudgeTarget(rows, "33", "x", NUDGE_STEP_MM);
  assert.equal(targetFor(rows, "33").x, TARGET_LIMIT_MM);
});

test("nudgeTarget on a non-planar axis is a no-op copy", () => {
  const rows = nudgeTarget([], "21", "x", NUDGE_STEP_MM);
  const next = nudgeTarget(rows, "21", "z", NUDGE_STEP_MM);
  assert.notEqual(next, rows, "returns a new array");
  assert.deepEqual(targetFor(next, "21"), targetFor(rows, "21"));
});

test("nudgeTarget leaves other teeth and other stages alone", () => {
  const rows = [
    { stage: 0, tooth: "21", x: 0.5, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
    { stage: TARGET_STAGE, tooth: "11", x: 0.4, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
  ];
  const next = nudgeTarget(rows, "11", "x", NUDGE_STEP_MM);
  assert.equal(next.find((r) => r.stage === 0 && r.tooth === "21").x, 0.5);
  assert.ok(Math.abs(targetFor(next, "11").x - (0.4 + NUDGE_STEP_MM)) < 1e-9);
});

test("targetFor returns zeros for an unauthored tooth", () => {
  assert.deepEqual(targetFor([], "47"), { x: 0, y: 0 });
});

test("targetMagnitudeMm is the in-plane resultant", () => {
  assert.ok(Math.abs(targetMagnitudeMm({ x: 3, y: 4 }) - 5) < 1e-9);
  assert.equal(targetMagnitudeMm(), 0);
});

test("clearTarget removes only the tooth's target row", () => {
  const rows = [
    { stage: 0, tooth: "11", x: 0.5, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
    { stage: TARGET_STAGE, tooth: "11", x: 0.4, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
    { stage: TARGET_STAGE, tooth: "21", x: 0.2, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 },
  ];
  const next = clearTarget(rows, "11");
  assert.equal(next.length, 2);
  assert.equal(next.find((r) => r.stage === TARGET_STAGE && r.tooth === "11"), undefined);
  assert.ok(next.find((r) => r.stage === 0 && r.tooth === "11"), "non-target row for 11 stays");
  assert.ok(next.find((r) => r.tooth === "21"), "other tooth target stays");
});
