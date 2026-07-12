import test from "node:test";
import assert from "node:assert/strict";

import { anatomyCounts, guidedAnatomyMarkup } from "./anatomy_render.js";

const anatomy = {
  roots: [{ trusted: true }, { trusted: false }],
  tooth_axes: [{ trusted: true }],
  alveolar_bone: [{ trusted: true }],
};

test("guided anatomy is summarized without review controls", () => {
  const markup = guidedAnatomyMarkup(anatomy);
  assert.match(markup, /3 of 4/);
  assert.match(markup, /2 root geometries/);
  assert.match(markup, /Technician mode/);
  assert.doesNotMatch(markup, />Accept</);
  assert.doesNotMatch(markup, />Correct</);
  assert.doesNotMatch(markup, />Reject</);
});

test("anatomy counts tolerate missing groups", () => {
  assert.deepEqual(anatomyCounts({ roots: [{}] }), {
    roots: 1,
    tooth_axes: 0,
    alveolar_bone: 0,
  });
});
