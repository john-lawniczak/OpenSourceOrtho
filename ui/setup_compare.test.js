import test from "node:test";
import assert from "node:assert/strict";

import { setupComparisonMarkup } from "./setup_compare.js";

test("setup comparison markup shows side-by-side restage details", () => {
  const html = setupComparisonMarkup({
    ok: true,
    source: "authored",
    before_timeline_days: 10,
    restaged_timeline_days: 30,
    comparison: {
      before_id: "baseline",
      after_id: "edited",
      before_stage_count: 1,
      after_stage_count: 3,
      stage_count_delta: 2,
      changed_teeth: [
        { tooth: "11", delta: { translate_x_mm: 0.4, rotate_tip_deg: -1 } },
      ],
      added_teeth: ["21"],
      removed_teeth: [],
      attachment_count_delta: 1,
      ipr_count_delta: 0,
      spacing_count_delta: 0,
      fixed_tooth_count_delta: 0,
      caveat: "Educational comparison only.",
    },
    caveat: "Preview only.",
  });

  assert.match(html, /Baseline/);
  assert.match(html, /Restaged/);
  assert.match(html, /30 days/);
  assert.match(html, /11/);
  assert.match(html, /X \+0.4, tip -1/);
  assert.match(html, /Attachments/);
});

test("setup comparison markup escapes server values", () => {
  const html = setupComparisonMarkup({
    ok: false,
    errors: ["bad <plan>"],
  });

  assert.match(html, /bad &lt;plan&gt;/);
});
