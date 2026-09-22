import test from "node:test";
import assert from "node:assert/strict";

import { segmentRowMarkup } from "./segmentation_render.js";

test("segmentation row renders review state and escapes server values", () => {
  const markup = segmentRowMarkup(
    { mesh_asset_id: 'mesh"><script>', tooth: "11", arch: "maxillary", confidence: 0.42 },
    { tooth: "21", included: false },
  );
  assert.match(markup, /42% · Review/);
  assert.match(markup, /value="21"/);
  assert.doesNotMatch(markup, /<script>/);
  assert.doesNotMatch(markup, / checked/);
});
