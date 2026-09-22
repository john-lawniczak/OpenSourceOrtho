import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { intakeReadinessMarkup, navigateReadinessAction, READINESS_ACTIONS } from "./intake_readiness.js";

const report = {
  records: [{ label: '<img src=x onerror="bad()">', detail: "<script>bad()</script>", state: "missing", scope: "surface", action: "upload_scans" }],
  caveat: "Metadata only", plan_consistency: { status: "checks_completed", detail: "Checks ran" },
  artifacts: { status: "prerequisites_met", detail: "Prerequisites only", blockers: [] },
};

test("readiness escapes record text and separates the four evidence layers", () => {
  const html = intakeReadinessMarkup(report);
  assert.doesNotMatch(html, /<img|<script>/);
  for (const text of ["Record evidence", "Plan consistency", "Artifact prerequisites", "Physical validation · Not assessed", "Geometry QA has not run"]) {
    assert.ok(html.includes(text), text);
  }
  assert.match(html, /data-readiness-action="upload_scans"/);
});

test("pending and failed evaluations cannot display previous readiness", () => {
  assert.match(intakeReadinessMarkup(report, { pending: true }), /Updating/);
  assert.doesNotMatch(intakeReadinessMarkup(report, { pending: true }), /Prerequisites met/);
  assert.match(intakeReadinessMarkup(null), /unavailable/);
});

test("unknown action identifiers never become arbitrary links", () => {
  const html = intakeReadinessMarkup({ ...report, records: [{ ...report.records[0], action: "javascript:bad()" }] });
  assert.doesNotMatch(html, /javascript:/);
});

test("all readiness routes resolve to real controls and reveal the technician panel before focus", () => {
  const source = readFileSync(new URL("./index.html", import.meta.url), "utf8");
  for (const [action, route] of Object.entries(READINESS_ACTIONS)) {
    assert.ok(source.includes(`id="${route.target}"`), action);
    assert.ok(source.includes(`id="panel-${route.step}"`), action);
    const state = { userMode: "simple", activeStep: "sample" };
    const calls = [];
    const target = { setAttribute() {}, focus() { calls.push("focus"); }, scrollIntoView() { calls.push("scroll"); } };
    const doc = { getElementById(id) { assert.equal(id, route.target); return target; } };
    assert.equal(navigateReadinessAction(action, state, () => calls.push("render"), doc), true);
    assert.equal(state.userMode, "advanced");
    assert.equal(state.activeStep, route.step);
    assert.deepEqual(calls, ["render", "focus", "scroll"]);
  }
});
