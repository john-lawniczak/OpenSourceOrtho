import test from "node:test";
import assert from "node:assert/strict";
import { newScanDates, validCaptureDate, matchScanDates } from "./scan_dates.js";
test("capture date stays unknown even when a file has a modification timestamp", () => {
  const dates = newScanDates([{ name: "upper.stl", size: 500, lastModified: 1234 }], "2026-11-13T12:00:00Z");
  assert.equal(dates[0].uploaded_at, "2026-11-13T12:00:00Z");
  assert.equal(dates[0].captured_on, null);
});
test("capture dates allow clearing and real calendar dates without rolling invalid days", () => {
  for (const date of ["", null, "2024-02-29", "2026-11-13"]) assert.ok(validCaptureDate(date));
  for (const date of ["2026-02-29", "2026-13-01", "today"]) assert.equal(validCaptureDate(date), false);
});
test("removing or reordering scans keeps dates bound to file identity", () => {
  const files = [{ name: "upper.stl", size: 1, lastModified: 1 }, { name: "lower.stl", size: 2, lastModified: 2 }];
  const dates = newScanDates(files, "2026-11-12T00:00:00Z");
  dates[1].captured_on = "2026-10-01";
  assert.deepEqual(matchScanDates([files[1]], dates), [dates[1]]);
  assert.deepEqual(matchScanDates([...files].reverse(), dates), [...dates].reverse());
  assert.equal(matchScanDates([{ ...files[1], size: 3 }], dates)[0].captured_on, null);
});
