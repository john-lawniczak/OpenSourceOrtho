import test from "node:test";
import assert from "node:assert/strict";

import { SCALE_BAR_MM, formatScaleStatus, scaleBarLabel } from "./scale.js";

test("scaleBarLabel reads the bar length in mm", () => {
  assert.equal(scaleBarLabel(), `${SCALE_BAR_MM} mm`);
});

test("formatScaleStatus is empty when the reference is off", () => {
  assert.equal(formatScaleStatus({ enabled: false, hasScan: true, unitsConfirmed: true }), "");
});

test("formatScaleStatus guides the user when prerequisites are missing", () => {
  assert.match(
    formatScaleStatus({ enabled: true, hasScan: false, unitsConfirmed: true }),
    /Load a scan/,
  );
  assert.match(
    formatScaleStatus({ enabled: true, hasScan: true, unitsConfirmed: false }),
    /Confirm the scan units/,
  );
});

test("formatScaleStatus reports the reference and the measured extent", () => {
  const status = formatScaleStatus({
    enabled: true,
    hasScan: true,
    unitsConfirmed: true,
    extentMm: { x: 63.6, y: 30.9, z: 54.0 },
  });
  assert.match(status, new RegExp(`${SCALE_BAR_MM} mm reference`));
  assert.match(status, /64 × 31 × 54 mm/); // rounded W×H×D
});

test("formatScaleStatus omits the extent when it is unavailable", () => {
  const status = formatScaleStatus({ enabled: true, hasScan: true, unitsConfirmed: true, extentMm: null });
  assert.match(status, /reference shown/);
  assert.doesNotMatch(status, /×/);
});
