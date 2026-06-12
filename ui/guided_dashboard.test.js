import test from "node:test";
import assert from "node:assert/strict";

import { guidedReviewDashboard } from "./guided.js";

test("guidedReviewDashboard cannot assess before a plan exists", () => {
  const dashboard = guidedReviewDashboard(null, []);

  assert.equal(dashboard.verdict, "cannot-assess");
  assert.match(dashboard.summary, /Build your plan/);
  assert.deepEqual(dashboard.cards, []);
});

test("guidedReviewDashboard surfaces edit diffs and warnings", () => {
  const dashboard = guidedReviewDashboard(
    {
      scale_confirmed: true,
      timeline: { stage_count: 2 },
      review_tier: { label: "STL surface only", root_bone_aware: false },
      root_bone_review: { verdict: "NOT_APPLICABLE" },
      findings: [
        { severity: "warning", code: "movement-cap-exceeded", title: "Movement cap exceeded" },
      ],
      print_export: {
        ready: false,
        blockers: ["print export is disabled"],
        manufacturing_readiness: { verdict: "NOT_APPLICABLE", reason: "disabled" },
      },
    },
    [{ stage: 1, tooth: "11", x: 0.4, y: 0.3, z: 0, tip: 0, torque: 0, rotation: 0 }],
  );

  assert.equal(dashboard.verdict, "cannot-assess");
  assert.equal(dashboard.cards[0].value, "1 tooth change(s)");
  assert.match(dashboard.cards[0].detail[0], /Tooth 11: 0\.5 mm/);
  assert.equal(dashboard.cards[1].status, "needs-review");
  assert.ok(dashboard.highlights.includes("Movement cap markers"));
  assert.ok(dashboard.highlights.includes("Root/bone unavailable badge"));
});

test("guidedReviewDashboard does not count info/notice findings as warnings", () => {
  // `root-bone-context` (info) is emitted for healthy root/bone-aware plans. It
  // must not flip the dashboard to "needs review" or fabricate a warning count.
  const dashboard = guidedReviewDashboard(
    {
      scale_confirmed: true,
      timeline: { stage_count: 1 },
      review_tier: { label: "Root/bone-aware review", root_bone_aware: true },
      root_bone_review: { verdict: "CONSISTENT" },
      findings: [
        { severity: "info", code: "root-bone-context", title: "Root/bone context available for tooth 11" },
      ],
      print_export: {
        ready: true,
        blockers: [],
        manufacturing_readiness: { verdict: "CONSISTENT", reason: "passed QA" },
      },
    },
    [],
  );

  assert.equal(dashboard.verdict, "ready");
  assert.equal(dashboard.cards[1].status, "ready");
  assert.equal(dashboard.cards[1].value, "No findings");
  assert.match(dashboard.summary, /No deterministic warnings/);
});

test("guidedReviewDashboard ignores skipped-check notices for overlay chips", () => {
  // The `*-scale-unconfirmed` notice codes contain the substrings "movement-cap"
  // and "collision" but mean the check was SKIPPED, not violated. They must not
  // produce phantom overlay highlight chips.
  const dashboard = guidedReviewDashboard(
    {
      scale_confirmed: true,
      timeline: { stage_count: 1 },
      review_tier: { label: "Root/bone-aware review", root_bone_aware: true },
      root_bone_review: { verdict: "CONSISTENT" },
      findings: [
        { severity: "notice", code: "movement-cap-scale-unconfirmed", title: "Cap check skipped" },
        { severity: "notice", code: "segmented-crown-collision-scale-unconfirmed", title: "Collision check skipped" },
      ],
      print_export: {
        ready: true,
        blockers: [],
        manufacturing_readiness: { verdict: "CONSISTENT", reason: "passed QA" },
      },
    },
    [],
  );

  assert.equal(dashboard.verdict, "ready");
  assert.ok(!dashboard.highlights.includes("Movement cap markers"));
  assert.ok(!dashboard.highlights.includes("Collision/IPR highlights"));
});

test("guidedReviewDashboard reports ready when checks and print readiness pass", () => {
  const dashboard = guidedReviewDashboard(
    {
      scale_confirmed: true,
      timeline: { stage_count: 1 },
      review_tier: { label: "Root/bone-aware review", root_bone_aware: true },
      root_bone_review: { verdict: "CONSISTENT" },
      findings: [],
      print_export: {
        ready: true,
        blockers: [],
        manufacturing_readiness: { verdict: "CONSISTENT", reason: "passed QA" },
      },
    },
    [],
  );

  assert.equal(dashboard.verdict, "ready");
  assert.equal(dashboard.cards[1].value, "No findings");
  assert.equal(dashboard.cards[2].value, "Trusted anatomy");
  assert.equal(dashboard.cards[3].status, "ready");
});
