import { escapeHtml } from "./core.js";
import { planJson } from "./plan.js";
import { el, requestSetupComparison, state } from "./state.js";

let compareTimer = null;

const AXIS_LABELS = {
  translate_x_mm: "X",
  translate_y_mm: "Y",
  translate_z_mm: "Z",
  rotate_tip_deg: "tip",
  rotate_torque_deg: "torque",
  rotate_rotation_deg: "rotation",
};

export function captureSetupBaseline() {
  state.setupCompare.baseline = setupSnapshot(planJson(), "manual", "captured editor setup");
  state.setupCompare.baselineLabel = "Captured editor setup";
  state.setupCompare.result = null;
  state.setupCompare.latestKey = "";
  state.setupCompare.status = "Baseline captured from the current editor setup.";
  renderSetupCompare();
}

export function useLatestVersionBaseline() {
  const latest = [...(state.versions.list || [])].reverse().find((item) => item.snapshot);
  if (!latest?.snapshot) {
    state.setupCompare.status = "Save a version before using it as the comparison baseline.";
    renderSetupCompare();
    return;
  }
  state.setupCompare.baseline = setupSnapshot(latest.snapshot, "saved-version", latest.version_id);
  state.setupCompare.baselineLabel = `Saved version ${latest.version_id}`;
  state.setupCompare.result = null;
  state.setupCompare.latestKey = "";
  state.setupCompare.status = `${latest.version_id} is the comparison baseline.`;
  renderSetupCompare();
}

export function clearSetupBaseline() {
  state.setupCompare.baseline = null;
  state.setupCompare.baselineLabel = "";
  state.setupCompare.result = null;
  state.setupCompare.latestKey = "";
  state.setupCompare.status = "Capture a baseline or save a version to compare setups.";
  renderSetupCompare();
}

export function setupSnapshot(plan, provenance = "manual", label = "") {
  return {
    ...structuredClone(plan),
    setup_provenance: {
      source: provenance,
      label,
      captured_at: new Date().toISOString(),
      caveat: "Compared setup provenance only; this is not clinical approval or manufacturing readiness.",
    },
  };
}

export function currentComparisonCandidate(result) {
  if (!result || result.ok === false) return null;
  return result.restaged_plan || result.after || null;
}

export function setupWorkspaceMarkup(compare) {
  const baseline = compare.baseline?.setup_provenance;
  const result = compare.result;
  const candidate = currentComparisonCandidate(result);
  const candidateProvenance = candidate?.setup_provenance;
  const cards = [
    ["Current", compare.currentProvenance || { source: "manual", label: "current editor" }],
    ["Baseline", baseline],
    ["Candidate", candidateProvenance || (result?.source ? { source: "generated", label: result.source } : null)],
  ];
  return `
    <div class="setup-workspace-grid">
      ${cards.map(([title, provenance]) => `
        <div>
          <strong>${escapeHtml(title)}</strong>
          <span>${escapeHtml(provenance?.source || "unavailable")}</span>
          <small>${escapeHtml(provenance?.label || "No setup loaded")}</small>
        </div>
      `).join("")}
    </div>
  `;
}

export function scheduleSetupCompare(currentPlan = planJson()) {
  const compare = state.setupCompare;
  if (!compare.baseline) {
    compare.busy = false;
    return;
  }
  const payload = compare.liveRestage
    ? { before: compare.baseline, edited: currentPlan, live_restage: true }
    : { before: compare.baseline, after: currentPlan };
  const key = JSON.stringify(payload);
  if (key === compare.latestKey) return;
  compare.latestKey = key;
  compare.busy = true;
  compare.status = compare.liveRestage ? "Live restaging comparison..." : "Comparing setups...";
  renderSetupCompare();
  if (compareTimer) clearTimeout(compareTimer);
  compareTimer = setTimeout(() => runSetupCompare(payload, key), 250);
}

async function runSetupCompare(payload, key) {
  try {
    const result = await requestSetupComparison(payload);
    if (state.setupCompare.latestKey !== key) return;
    state.setupCompare.result = tagComparisonResult(result, payload);
    state.setupCompare.status = result.ok === false
      ? (result.errors || ["Setup comparison failed."]).join("; ")
      : "Comparison updated.";
  } catch (error) {
    if (state.setupCompare.latestKey !== key) return;
    state.setupCompare.result = null;
    state.setupCompare.status = error.message;
  } finally {
    if (state.setupCompare.latestKey === key) state.setupCompare.busy = false;
    renderSetupCompare();
  }
}

function tagComparisonResult(result, payload) {
  if (!result || result.ok === false) return result;
  if (payload.live_restage) {
    return {
      ...result,
      restaged_plan: setupSnapshot(result.restaged_plan || payload.edited, "generated", result.source || "live restage preview"),
    };
  }
  return {
    ...result,
    after: setupSnapshot(payload.after, "manual", "current editor candidate"),
  };
}

export function renderSetupCompare() {
  const compare = state.setupCompare;
  const live = el("setupLiveRestage");
  if (!live) return;
  live.checked = compare.liveRestage;
  el("setupCompareStatus").textContent = compare.busy ? "Working..." : compare.status;
  el("setupCompareBaseline").textContent = compare.baselineLabel || "No baseline selected";
  el("clearSetupBaseline").disabled = !compare.baseline;
  const promote = el("promoteSetupCandidate");
  if (promote) promote.disabled = !currentComparisonCandidate(compare.result);
  const workspace = el("setupWorkspace");
  if (workspace) workspace.innerHTML = setupWorkspaceMarkup(compare);
  el("setupCompareReport").innerHTML = setupComparisonMarkup(compare.result);
}

export function setupComparisonMarkup(result) {
  if (!result) {
    return "<p class=\"chat-empty\">No comparison yet.</p>";
  }
  if (result.ok === false) {
    return `<p class="finding-gap">${escapeHtml((result.errors || ["Setup comparison failed."]).join("; "))}</p>`;
  }
  const comparison = result.comparison || result;
  const changed = comparison.changed_teeth || [];
  const added = comparison.added_teeth || [];
  const removed = comparison.removed_teeth || [];
  const controls = [
    ["Attachments", comparison.attachment_count_delta],
    ["IPR contacts", comparison.ipr_count_delta],
    ["Spacing items", comparison.spacing_count_delta],
    ["Fixed teeth", comparison.fixed_tooth_count_delta],
  ].filter(([, value]) => Number(value || 0) !== 0);
  return `
    <div class="setup-compare-columns">
      <div>
        <h3>Baseline</h3>
        <dl>
          <div><dt>Plan</dt><dd>${escapeHtml(comparison.before_id)}</dd></div>
          <div><dt>Stages</dt><dd>${Number(comparison.before_stage_count || 0)}</dd></div>
          ${result.before_timeline_days != null ? `<div><dt>Timeline</dt><dd>${Number(result.before_timeline_days)} days</dd></div>` : ""}
        </dl>
      </div>
      <div>
        <h3>${result.source ? "Restaged" : "Current"}</h3>
        <dl>
          <div><dt>Plan</dt><dd>${escapeHtml(comparison.after_id)}</dd></div>
          <div><dt>Stages</dt><dd>${Number(comparison.after_stage_count || 0)} (${signed(comparison.stage_count_delta)})</dd></div>
          ${result.restaged_timeline_days != null ? `<div><dt>Timeline</dt><dd>${Number(result.restaged_timeline_days)} days</dd></div>` : ""}
        </dl>
      </div>
    </div>
    ${result.source ? `<p class="viewer-caveat">Restage source: ${escapeHtml(result.source)}. ${result.requires_acknowledgement ? "Educational acknowledgement required." : ""}</p>` : ""}
    <div class="setup-diff-summary">
      <span>${changed.length} moved tooth diff${changed.length === 1 ? "" : "s"}</span>
      <span>${added.length} added</span>
      <span>${removed.length} removed</span>
    </div>
    ${changed.length ? `<ul class="setup-diff-list">${changed.map(toothDiffMarkup).join("")}</ul>` : "<p class=\"chat-empty\">No tooth movement differences.</p>"}
    ${added.length || removed.length ? `<p class="viewer-caveat">Added: ${escapeHtml(added.join(", ") || "none")} · Removed: ${escapeHtml(removed.join(", ") || "none")}</p>` : ""}
    ${controls.length ? `<ul class="setup-diff-list compact">${controls.map(([label, value]) => `<li><strong>${escapeHtml(label)}</strong><span>${signed(value)}</span></li>`).join("")}</ul>` : ""}
    <p class="viewer-caveat">${escapeHtml(result.caveat || comparison.caveat || "")}</p>
  `;
}

function toothDiffMarkup(diff) {
  const axes = Object.entries(diff.delta || {})
    .map(([axis, value]) => `${AXIS_LABELS[axis] || axis} ${signed(value)}`)
    .join(", ");
  return `<li><strong>${escapeHtml(diff.tooth)}</strong><span>${escapeHtml(axes)}</span></li>`;
}

function signed(value) {
  const numeric = Number(value || 0);
  return `${numeric >= 0 ? "+" : ""}${Number.isInteger(numeric) ? numeric : numeric.toFixed(3).replace(/0+$/, "").replace(/\.$/, "")}`;
}
