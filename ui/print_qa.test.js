import test from "node:test";
import assert from "node:assert/strict";

import { renderPrintQa } from "./guided.js";

// renderPrintQa only reads/writes host.hidden and host.innerHTML, so a plain
// object stands in for the DOM node and keeps the test DOM-free like the others.
function fakeHost() {
  return { hidden: false, innerHTML: "" };
}

test("renderPrintQa hides itself when there is no result", () => {
  const host = fakeHost();
  renderPrintQa(host, null);
  assert.equal(host.hidden, true);
  assert.equal(host.innerHTML, "");
});

test("renderPrintQa hides itself when the build failed", () => {
  const host = fakeHost();
  renderPrintQa(host, { ok: false });
  assert.equal(host.hidden, true);
});

test("renderPrintQa surfaces readiness, compensation, and per-stage shell QA", () => {
  const host = fakeHost();
  renderPrintQa(host, {
    ok: true,
    manufacturing_readiness: { verdict: "CONSISTENT", reason: "passed QA" },
    printer_tolerances: {
      xy_compensation_mm: 0.05,
      z_compensation_mm: -0.03,
      minimum_printable_feature_mm: 0.3,
    },
    aligner_shell_reports: [
      {
        stage_index: 0,
        verdict: "CONSISTENT",
        quality: {
          verdict: "CONSISTENT",
          watertight: true,
          self_intersection_count: 1,
          thickness_mm: { min: 0.58, max: 0.62 },
        },
      },
    ],
  });

  assert.equal(host.hidden, false);
  assert.match(host.innerHTML, /Manufacturing readiness: CONSISTENT/);
  // Compensation values that are baked into the geometry are shown to the user.
  assert.match(host.innerHTML, /XY 0\.05 mm, Z -0\.03 mm/);
  assert.match(host.innerHTML, /min feature|minimum printable feature 0\.30 mm/);
  // The per-stage row exposes the watertight + thickness detail.
  assert.match(host.innerHTML, /watertight yes/);
  assert.match(host.innerHTML, /0\.58.*0\.62/);
});

test("renderPrintQa lists the named failed checks for an ISSUES stage", () => {
  const host = fakeHost();
  renderPrintQa(host, {
    ok: true,
    manufacturing_readiness: { verdict: "ISSUES", reason: "one stage failed QA" },
    aligner_shell_reports: [
      {
        stage_index: 0,
        verdict: "ISSUES",
        quality: {
          verdict: "ISSUES",
          failed_checks: ["self-intersecting triangles: 4", "nonmanifold edges: 2"],
        },
      },
    ],
  });

  assert.match(host.innerHTML, /Manufacturing readiness: ISSUES/);
  assert.match(host.innerHTML, /self-intersecting triangles: 4/);
  assert.match(host.innerHTML, /nonmanifold edges: 2/);
});

test("renderPrintQa shows the shell backend and any fail-closed downgrade", () => {
  const host = fakeHost();
  renderPrintQa(host, {
    ok: true,
    manufacturing_readiness: { verdict: "CONSISTENT" },
    aligner_shell_backend: {
      requested: "robust",
      used: "pure-python",
      available: false,
      fallback_reason: "robust backend requested but the 'mesh-processing' extra (Open3D) is not installed",
    },
    aligner_shell_reports: [],
  });

  assert.match(host.innerHTML, /Shell backend: pure-python/);
  assert.match(host.innerHTML, /Open3D/);
});

test("renderPrintQa shows the skip reason for a NOT_APPLICABLE stage", () => {
  const host = fakeHost();
  renderPrintQa(host, {
    ok: true,
    manufacturing_readiness: { verdict: "NOT_APPLICABLE", reason: "no reviewed geometry" },
    aligner_shell_reports: [
      { stage_index: 0, verdict: "NOT_APPLICABLE", reason: "real reviewed geometry unavailable" },
    ],
  });

  assert.match(host.innerHTML, /Manufacturing readiness: NOT_APPLICABLE/);
  assert.match(host.innerHTML, /real reviewed geometry unavailable/);
});
