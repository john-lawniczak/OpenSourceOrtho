// Render endpoint-match evidence separately from the timeline and renderer.
import { fitConsistencyText } from "./fit_consistency.js";
import { el } from "./state.js";

export function renderMotionControls(motion, selected, frame, error = "") {
  const select = el("comparisonTooth");
  const ids = motion?.teeth.map(tooth => tooth.tooth) || [];
  if (select.dataset.teeth !== ids.join(",")) {
    select.replaceChildren(new Option("All teeth", ""), ...ids.map(id => new Option(`${id} (draft)`, id)));
    select.dataset.teeth = ids.join(",");
  }
  select.value = selected;
  select.disabled = !motion;
  el("comparisonFocusTooth").disabled = !motion || !selected;
  el("comparisonEndpointFit").hidden = frame.week !== 7 || !motion;
  el("comparisonEndpointFit").setAttribute("aria-pressed", String(frame.kind === "estimated"));
  el("comparisonEndpointFit").textContent = frame.kind === "estimated" ? "Show recorded week 7" : "Inspect estimated endpoint";
  el("comparisonEstimateNote").hidden = !motion;
  el("comparisonEstimateNote").textContent = frame.kind === "estimated"
    ? "SIMULATED ESTIMATE · Assumed timing between the two scans. Tooth boundaries and matches are automatic drafts."
    : "Weeks 2–6 simulate motion fitted to the endpoint scans. Tooth boundaries and matches are automatic drafts.";
  el("comparisonMotionRetry").hidden = !error;
  const detail = el("comparisonMatchDetail");
  if (!motion) { detail.textContent = error; return; }
  const tooth = motion.teeth.find(item => item.tooth === selected);
  if (!tooth) {
    const estimated = motion.teeth.filter(item => item.status.startsWith("estimated")).length;
    const weak = motion.teeth.filter(item => item.status === "estimated-weak").length;
    detail.textContent = `${estimated}/${motion.teeth.length} draft regions fitted · ${weak} uncertain matches · `
      + `${motion.teeth.length - estimated} held without a usable fit. Select a tooth to inspect its estimate.`;
    return;
  }
  const angle = 2 * Math.acos(Math.min(1, Math.abs(tooth.quaternion_xyzw[3]))) * 180 / Math.PI;
  const shift = Math.hypot(...tooth.translation) * frame.fraction;
  const status = { "estimated-draft": "Draft match", "estimated-weak": "Uncertain match", "held-unmatched": "Held — no usable fit" }[tooth.status];
  detail.textContent = `Draft tooth ${tooth.tooth} · ${status}. Estimated change from week 1: `
    + `${shift.toFixed(2)} scan units, ${(angle * frame.fraction).toFixed(1)}° rotation. `
    + (tooth.fit ? `Endpoint surface residual (90th percentile): ${tooth.fit.p90_residual.toFixed(2)} scan units. ` : "")
    + `${fitConsistencyText(tooth)} `
    + "Scale is unverified; values are not millimeter measurements. Highlighted regions appear on simulated weeks and the baseline.";
}
