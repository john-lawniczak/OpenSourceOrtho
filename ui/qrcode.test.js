import assert from "node:assert/strict";
import { test } from "node:test";

import { makeQrModules, qrSvg } from "./qrcode.js";

test("QR module matrix has fixed version-5 dimensions and finder patterns", () => {
  const modules = makeQrModules("https://ortho.example/app/?case=golden-case-001");

  assert.equal(modules.length, 37);
  assert.equal(modules[0].length, 37);
  assert.equal(modules[0][0], true);
  assert.equal(modules[6][6], true);
  assert.equal(modules[0][30], true);
  assert.equal(modules[30][0], true);
});

test("QR SVG renders a self-contained image and rejects long payloads", () => {
  const svg = qrSvg("orthoplan://case/golden-case-001");
  assert.match(svg, /^<svg /);
  assert.match(svg, /Case handoff QR code/);
  assert.match(svg, /<path fill="#111"/);

  assert.throws(() => qrSvg("x".repeat(200)), /too long/);
});
