import test from "node:test";
import assert from "node:assert/strict";

import { printExportMarkup } from "./print_export.js";

test("print export markup keeps readiness, QA, tolerances, and caveats visible", () => {
  const markup = printExportMarkup({
    ready: false,
    blockers: ["Reviewed geometry is missing"],
    manufacturing_readiness: { verdict: "ISSUES", reason: "QA needs review" },
    shell_qa_findings: [{ verdict: "ISSUES", message: "nonmanifold edges: 2" }],
    printer_tolerances: { xy_compensation_mm: 0.05, z_compensation_mm: -0.03 },
    model_material: "model resin",
    thermoforming_material: "sheet",
    caveat: "Physical use is not authorized.",
  });
  assert.match(markup, /Inputs incomplete/);
  assert.match(markup, /Manufacturing readiness: ISSUES/);
  assert.match(markup, /nonmanifold edges: 2/);
  assert.match(markup, /XY 0\.05 mm, Z -0\.03 mm/);
  assert.match(markup, /Physical use is not authorized/);
});

test("print export markup escapes dynamic values", () => {
  assert.doesNotMatch(printExportMarkup({ blockers: ["<script>alert(1)</script>"] }), /<script>/);
});
