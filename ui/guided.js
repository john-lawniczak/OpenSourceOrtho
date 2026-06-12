// Guided wizard: the simplified, primary flow for non-technical first-time
// users. It is a step-by-step walk: upload scans -> review which teeth move and
// how long -> small details -> review the plan -> slide through the 3D preview
// -> get printable files to email/attach.
//
// This module owns ONLY the wizard's step routing and per-step presentation. It
// reuses the technician singletons (the 3D viewer block and the upload stack) by
// relocating them into guided step hosts - event handling is delegated on
// document.body and renders target elements by id, so moving a subtree is safe
// and avoids a second WebGL context. Engine/generation/chat all flow through the
// same helpers the technician page uses.

import { el, state } from "./state.js";
import { planJson } from "./plan.js";
import { requestPrintPackage } from "./state.js";
import {
  TARGET_STAGE,
  scaleConfirmed,
  targetFor,
  targetMagnitudeMm,
  targetStatusText,
  targetWarningTier,
} from "./manual_edit.js";

// Step order. Each id maps to a <section class="gstep" data-gstep="..."> panel
// and a progress-rail dot in index.html.
export const GUIDED_STEPS = [
  { id: "upload", label: "Upload" },
  { id: "plan", label: "Teeth & time" },
  { id: "details", label: "Details" },
  { id: "review", label: "Review" },
  { id: "preview", label: "3D preview" },
  { id: "print", label: "Print / send" },
];

const TOOTH_NAMES = {
  1: "central incisor", 2: "lateral incisor", 3: "canine", 4: "first premolar",
  5: "second premolar", 6: "first molar", 7: "second molar", 8: "third molar",
};

const ARCH_NAMES = { 1: "upper right", 2: "upper left", 3: "lower left", 4: "lower right" };

function toothLabel(value) {
  const quadrant = ARCH_NAMES[Number(String(value)[0])] || "tooth";
  const name = TOOTH_NAMES[Number(String(value)[1])] || "tooth";
  return `${value} · ${quadrant} ${name}`;
}

function stepIndex(id) {
  const idx = GUIDED_STEPS.findIndex((step) => step.id === id);
  return idx < 0 ? 0 : idx;
}

export function currentGuidedStep() {
  return state.guided.step || "upload";
}

export function goGuided(stepId) {
  if (!GUIDED_STEPS.some((step) => step.id === stepId)) return;
  state.guided.step = stepId;
  // The 3D preview is only meaningful in a view where staged movement renders;
  // "current" shows just the static baseline scan, so default to overlay.
  if (stepId === "preview" && state.view === "current") state.view = "overlay";
}

export function guidedNext() {
  goGuided(GUIDED_STEPS[Math.min(stepIndex(currentGuidedStep()) + 1, GUIDED_STEPS.length - 1)].id);
}

export function guidedBack() {
  goGuided(GUIDED_STEPS[Math.max(stepIndex(currentGuidedStep()) - 1, 0)].id);
}

// The set of teeth the user has chosen to hold still. plan.js folds these into
// the plan's fixed_teeth so the engine excludes them.
export function toggleExcludedTooth(value) {
  const set = new Set(state.guided.excludedTeeth);
  if (set.has(value)) set.delete(value);
  else set.add(value);
  state.guided.excludedTeeth = [...set];
}

export function setWearInterval(days) {
  const field = el("wearInterval");
  if (field) field.value = String(days);
}

// Teeth that the current plan actually moves (appear in any authored stage row).
function planTeeth() {
  return [...new Set(state.rows.map((row) => String(row.tooth)))].sort();
}

function rowMagnitude(row) {
  return targetMagnitudeMm({ x: row?.x || 0, y: row?.y || 0 });
}

function editedTargets(rows = state.rows) {
  return (rows || [])
    .filter((row) => row.stage === TARGET_STAGE && rowMagnitude(row) > 0)
    .map((row) => ({
      tooth: String(row.tooth),
      x: row.x || 0,
      y: row.y || 0,
      magnitude: rowMagnitude(row),
    }))
    .sort((a, b) => b.magnitude - a.magnitude || a.tooth.localeCompare(b.tooth));
}

export function guidedReviewDashboard(result, rows = []) {
  if (!result?.timeline) {
    return {
      verdict: "cannot-assess",
      label: "Cannot assess yet",
      summary: "Build your plan first.",
      cards: [],
      highlights: [],
    };
  }
  const findings = result.findings || [];
  // Only `warning`-severity findings are blocking review concerns. `info`/`notice`
  // findings are educational or data-gap context (e.g. the `root-bone-context` info
  // finding emitted for healthy root/bone-aware plans) and must NOT flip the
  // dashboard to "needs review". Unknown/missing severity is surfaced fail-safe.
  const warnings = findings.filter((finding) => !isAdvisorySeverity(finding.severity));
  const edits = editedTargets(rows);
  const tier = result.review_tier || {};
  const print = result.print_export || {};
  const readiness = print.manufacturing_readiness || {};
  const rootAware = Boolean(tier.root_bone_aware);
  const scaleOk = result.scale_confirmed !== false;
  const printReady = Boolean(print.ready && readiness.verdict === "CONSISTENT");
  const issueCount = warnings.length + (readiness.verdict === "ISSUES" ? 1 : 0);
  const cannotAssess = !scaleOk || !rootAware || readiness.verdict === "NOT_APPLICABLE";
  const verdict = cannotAssess ? "cannot-assess" : (issueCount ? "needs-review" : "ready");

  return {
    verdict,
    label: {
      ready: "Ready for reviewed export",
      "needs-review": "Needs review",
      "cannot-assess": "Cannot assess fully",
    }[verdict],
    summary: dashboardSummary({ warnings, edits, rootAware, printReady, scaleOk, readiness }),
    cards: [
      editCard(edits),
      warningCard(warnings),
      rootBoneCard(tier, result.root_bone_review),
      printCard(print),
    ],
    highlights: overlayHighlights(warnings, readiness, tier),
  };
}

// `info` and `notice` findings are advisory context, not blocking warnings.
// Anything else (including a malformed finding with no severity) is treated as a
// warning so a genuine concern is never silently hidden.
function isAdvisorySeverity(severity) {
  return severity === "info" || severity === "notice";
}

function dashboardSummary({ warnings, edits, rootAware, printReady, scaleOk, readiness }) {
  if (!scaleOk) return "Confirm scan units before trusting millimeter checks.";
  if (warnings.length) return `${warnings.length} warning(s) need review before export.`;
  if (!rootAware) return "Surface plan is reviewable; root/bone anatomy is not trusted.";
  if (!printReady) return `Print status: ${readiness.verdict || "not ready"}.`;
  if (edits.length) return "Edits rebuilt with no deterministic warnings.";
  return "No deterministic warnings in the current review.";
}

function editCard(edits) {
  return {
    id: "edits",
    title: "Edit diff",
    status: edits.length ? "needs-review" : "ready",
    value: edits.length ? `${edits.length} tooth change(s)` : "No guided edits",
    detail: edits.slice(0, 4).map((edit) => `Tooth ${edit.tooth}: ${edit.magnitude.toFixed(1)} mm`),
  };
}

function warningCard(warnings) {
  return {
    id: "warnings",
    title: "Warnings",
    status: warnings.length ? "needs-review" : "ready",
    value: warnings.length ? `${warnings.length} finding(s)` : "No findings",
    detail: warnings.slice(0, 3).map((finding) => finding.title || finding.code || "Review finding"),
  };
}

function rootBoneCard(tier, review) {
  const aware = Boolean(tier.root_bone_aware);
  return {
    id: "root-bone",
    title: "Root / bone",
    status: aware ? "ready" : "cannot-assess",
    value: aware ? "Trusted anatomy" : "Cannot assess",
    detail: [tier.label || "STL surface only", review?.verdict ? `Review: ${review.verdict}` : ""].filter(Boolean),
  };
}

function printCard(print) {
  const readiness = print?.manufacturing_readiness || {};
  const verdict = readiness.verdict || "NOT_APPLICABLE";
  return {
    id: "print",
    title: "Print readiness",
    status: verdict === "CONSISTENT" && print?.ready ? "ready" : (verdict === "ISSUES" ? "needs-review" : "cannot-assess"),
    value: verdict,
    detail: [readiness.reason, ...(print?.blockers || []).slice(0, 2)].filter(Boolean),
  };
}

// `warnings` is already filtered to warning-severity findings, so the `*-scale-
// unconfirmed` notice codes (which also contain "movement-cap"/"collision") do
// not produce phantom overlay chips for checks that were skipped, not violated.
function overlayHighlights(warnings, readiness, tier) {
  const highlights = [];
  if ((warnings || []).some((finding) => String(finding.code || "").includes("movement-cap"))) {
    highlights.push("Movement cap markers");
  }
  if ((warnings || []).some((finding) => String(finding.code || "").includes("collision"))) {
    highlights.push("Collision/IPR highlights");
  }
  if (!tier?.root_bone_aware) highlights.push("Root/bone unavailable badge");
  if (readiness?.verdict && readiness.verdict !== "CONSISTENT") highlights.push("Print readiness badge");
  return highlights;
}

function relocate(blockId, hostId) {
  const block = el(blockId);
  const host = el(hostId);
  if (block && host && block.parentElement !== host) host.appendChild(block);
}

// The single 3D viewer follows the active guided step: the user picks teeth in
// "plan", watches the movement-scale slider in "details", and scrubs stages in
// "preview". Only one step is visible at a time, so relocating the one WebGL
// instance into the active step's host is safe.
const VIEWER_STEP_HOSTS = {
  plan: "guidedPlanViewerHost",
  details: "guidedDetailsViewerHost",
  preview: "guidedPreviewHost",
};

// Relocate shared singletons into the host for the active mode/step. In guided
// mode the viewer/upload live inside their wizard steps; in technician mode they
// return to the review workspace.
export function placeSharedBlocks() {
  if (state.userMode === "simple") {
    relocate("simpleUpload", "guidedUploadHost");
    relocate("viewerBlock", VIEWER_STEP_HOSTS[currentGuidedStep()] || "guidedPreviewHost");
  } else {
    relocate("simpleUpload", "techUploadHost");
    relocate("viewerBlock", "techViewerHost");
  }
}

export function renderGuided() {
  placeSharedBlocks();
  const active = currentGuidedStep();

  document.querySelectorAll("#guided .gstep").forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.gstep === active);
  });
  document.querySelectorAll("#guidedRail [data-gstep-nav]").forEach((dot) => {
    const done = stepIndex(dot.dataset.gstepNav) < stepIndex(active);
    dot.classList.toggle("is-active", dot.dataset.gstepNav === active);
    dot.classList.toggle("is-done", done);
  });
  document.querySelectorAll("[data-guided-view]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.guidedView === state.view);
  });

  const idx = stepIndex(active);
  const back = el("guidedBack");
  const next = el("guidedNext");
  if (back) back.disabled = idx === 0;
  if (next) next.hidden = idx === GUIDED_STEPS.length - 1;

  // Sample banner + heading: the sample reuses this wizard, so flag it clearly.
  const banner = el("sampleBanner");
  if (banner) banner.hidden = !state.sample.active;
  const heading = el("guidedHeading");
  if (heading) {
    heading.textContent = state.sample.active
      ? "Sample test case — guided walkthrough"
      : "Plan your aligners, step by step";
  }

  renderGuidedTeeth();
  renderGuidedEdit();
  renderGuidedBuildStatus();
  renderGuidedReview();
  renderGuidedPrint();
}

// Visible feedback for "Build my plan" so the action is never silent.
function renderGuidedBuildStatus() {
  const status = el("guidedBuildStatus");
  if (!status) return;
  const gen = state.generation;
  const text = gen.busy ? "Building your plan..." : (gen.status || "");
  status.hidden = !text;
  status.textContent = text;
}

function renderGuidedEdit() {
  const title = el("guidedEditTitle");
  if (!title) return;
  const selected = state.manualEdit.selectedTooth;
  const confirmed = scaleConfirmed(state.scanUnits);
  const target = selected ? targetFor(state.rows, selected) : { x: 0, y: 0 };
  const tier = targetWarningTier(target);
  const canEdit = Boolean(selected && confirmed);

  title.textContent = selected ? `Tooth ${selected}` : "No tooth selected";
  const status = el("guidedEditStatus");
  if (status) {
    status.dataset.tier = selected && confirmed ? tier : "muted";
    status.textContent = !selected
      ? "Select a tooth in the 3D view."
      : (!confirmed
          ? "Set scan units to mm before nudging."
          : targetStatusText(target));
  }

  const readout = el("guidedEditReadout");
  if (readout) {
    readout.textContent = selected
      ? `x ${target.x.toFixed(2)} mm · y ${target.y.toFixed(2)} mm`
      : "";
  }

  document.querySelectorAll(".guided-nudge-pad button").forEach((button) => {
    button.disabled = !canEdit;
  });
  const undo = el("guidedEditUndo");
  if (undo) undo.disabled = !(state.manualEdit.undoStack || []).length;
  const rebuild = el("guidedRebuild");
  if (rebuild) rebuild.disabled = !state.rows.length;
  const reset = el("guidedTargetReset");
  if (reset) reset.disabled = !canEdit;
  const clear = el("guidedClearSelection");
  if (clear) clear.disabled = !selected;
}

function renderGuidedTeeth() {
  const host = el("guidedTeeth");
  if (!host) return;
  const teeth = planTeeth();
  const excluded = new Set(state.guided.excludedTeeth);
  host.innerHTML = teeth.length
    ? teeth.map((tooth) => `
        <label class="guided-tooth ${excluded.has(tooth) ? "is-excluded" : ""}">
          <input type="checkbox" data-guided-tooth="${tooth}" ${excluded.has(tooth) ? "" : "checked"} />
          <span>${toothLabel(tooth)}</span>
        </label>
      `).join("")
    : "<p class=\"guided-hint\">Upload scans or load the sample, then build your plan to see which teeth move.</p>";

  const wear = Number(el("wearInterval")?.value || 0);
  document.querySelectorAll("#guidedDuration [data-wear]").forEach((button) => {
    button.classList.toggle("is-active", Number(button.dataset.wear) === wear);
  });
  // Balanced (10) is the default and the only always-visible choice; if a
  // non-default pace is active, open the "Other pacing options" disclosure so the
  // selected button stays visible instead of hidden behind the summary.
  const more = el("guidedDurationMore");
  if (more && wear && wear !== 10) more.open = true;
  const summary = el("guidedDurationSummary");
  if (summary) {
    const t = state.lastEval?.timeline;
    summary.textContent = t
      ? `About ${t.projected_duration_weeks} weeks (${t.stage_count} stage(s) at ${t.wear_interval_days}-day wear). Projected, not promised.`
      : "Build your plan to see a projected duration.";
  }
}

// Step 4: a plain-language summary + projected timeline as clear bullet points.
// (Engine findings and data gaps are intentionally not surfaced here - they are
// audience-specific detail that lives in the Technician review, not the guided
// summary for a first-time user.)
function renderGuidedReview() {
  const headline = el("guidedHeadline");
  const summary = el("guidedSummary");
  const dashboard = el("guidedReviewDashboard");
  const t = state.lastEval?.timeline;
  if (!t) {
    if (headline) headline.innerHTML = "";
    if (summary) summary.innerHTML = "<li>Build your plan in step 2 to see a summary and timeline here.</li>";
    renderDashboard(dashboard, guidedReviewDashboard(null));
    return;
  }
  renderDashboard(dashboard, guidedReviewDashboard(state.lastEval, state.rows));
  // The headline carries the two things that matter most: how many trays, and how
  // long overall. Everything else is supporting detail below it.
  const trays = t.stage_count;
  if (headline) {
    headline.innerHTML = `
      <strong class="guided-headline-main">${trays} ${trays === 1 ? "tray" : "trays"} · about ${t.projected_duration_weeks} weeks total</strong>
      <span class="guided-headline-sub">${t.wear_interval_days} days of wear per tray</span>
    `;
  }
  const teeth = planTeeth().length;
  if (summary) {
    summary.innerHTML = [
      `<li><strong>${trays}</strong> aligner stage(s) — one tray per stage, worn in sequence.</li>`,
      `<li><strong>${t.wear_interval_days} days</strong> of wear per tray.</li>`,
      `<li><strong>${t.projected_duration_days} days</strong> (~${t.projected_duration_weeks} weeks) projected total.</li>`,
      `<li><strong>${teeth} ${teeth === 1 ? "tooth" : "teeth"}</strong> moved by this plan.</li>`,
      `<li class="guided-summary-note">${escapeText(t.caveat)}</li>`,
    ].join("");
  }
}

function renderDashboard(host, dashboard) {
  if (!host) return;
  const cards = dashboard.cards?.length
    ? dashboard.cards.map(dashboardCardMarkup).join("")
    : "<p class=\"guided-hint\">Build your plan to populate review checks.</p>";
  const highlights = dashboard.highlights?.length
    ? `<div class="guided-overlay-chips" aria-label="3D warning overlays">${
        dashboard.highlights.map((item) => `<span>${escapeText(item)}</span>`).join("")
      }</div>`
    : "";
  host.innerHTML = `
    <div class="guided-dashboard-hero" data-status="${dashboard.verdict}">
      <strong>${escapeText(dashboard.label)}</strong>
      <span>${escapeText(dashboard.summary)}</span>
    </div>
    <div class="guided-dashboard-grid">${cards}</div>
    ${highlights}
  `;
}

function dashboardCardMarkup(card) {
  const detail = card.detail?.length
    ? `<ul>${card.detail.map((item) => `<li>${escapeText(item)}</li>`).join("")}</ul>`
    : "";
  return `
    <article class="guided-dashboard-card" data-status="${card.status}">
      <span>${escapeText(card.title)}</span>
      <strong>${escapeText(card.value)}</strong>
      ${detail}
    </article>
  `;
}

function renderGuidedPrint() {
  const status = el("guidedPrintStatus");
  if (status) status.textContent = state.guided.print.status || "";
  const button = el("guidedPrint");
  if (button) button.disabled = state.guided.print.busy;
  const links = el("guidedPrintLinks");
  if (links) links.hidden = !state.guided.print.result;
  renderPrintQa(el("guidedPrintQa"), state.guided.print.result);
}

// Surface the manufacturing-readiness verdict and per-stage shell QA that the
// backend already computes, so a user can see WHY a stage is consistent, flagged,
// or skipped instead of only getting a "files built" message.
export function renderPrintQa(host, result) {
  if (!host) return;
  if (!result || result.ok === false) {
    host.hidden = true;
    host.innerHTML = "";
    return;
  }
  host.hidden = false;
  host.innerHTML = [
    readinessBanner(result.manufacturing_readiness),
    backendLine(result.aligner_shell_backend),
    toleranceLine(result.printer_tolerances),
    shellStageTable(result.aligner_shell_reports),
  ].filter(Boolean).join("");
}

function backendLine(backend) {
  if (!backend || !backend.used) return "";
  const used = `Shell backend: ${escapeText(String(backend.used))}`;
  // A fallback_reason means the requested (robust) backend was unavailable and
  // the export honestly downgraded rather than silently substituting geometry.
  if (backend.fallback_reason) {
    return `<p class="print-qa-tolerances qa-issue">${used} — ${escapeText(backend.fallback_reason)}</p>`;
  }
  return `<p class="print-qa-tolerances">${used}.</p>`;
}

function readinessBanner(readiness) {
  if (!readiness || !readiness.verdict) return "";
  const verdict = String(readiness.verdict);
  const reason = readiness.reason ? `<span>${escapeText(readiness.reason)}</span>` : "";
  return `<p class="print-qa-readiness ${verdictClass(verdict)}">`
    + `<strong>Manufacturing readiness: ${escapeText(verdict)}</strong>${reason}</p>`;
}

function toleranceLine(tolerances) {
  if (!tolerances) return "";
  const xy = formatMm(tolerances.xy_compensation_mm);
  const z = formatMm(tolerances.z_compensation_mm);
  const feature = formatMm(tolerances.minimum_printable_feature_mm);
  return `<p class="print-qa-tolerances">Printer compensation applied to geometry — `
    + `XY ${xy} mm, Z ${z} mm · minimum printable feature ${feature} mm.</p>`;
}

function shellStageTable(reports) {
  if (!Array.isArray(reports) || reports.length === 0) return "";
  const rows = reports.map((report) => {
    const quality = report.quality || {};
    const thickness = quality.thickness_mm || {};
    const failed = Array.isArray(quality.failed_checks) ? quality.failed_checks : [];
    let detail;
    if (!quality.verdict) {
      detail = escapeText(report.reason || "");
    } else if (failed.length) {
      detail = failed.map((reason) => escapeText(reason)).join("; ");
    } else {
      detail = `watertight ${quality.watertight ? "yes" : "no"} · `
        + `thickness ${formatMm(thickness.min)}–${formatMm(thickness.max)} mm · `
        + `self-intersections ${Number(quality.self_intersection_count ?? 0)} · `
        + `nonmanifold edges ${Number(quality.nonmanifold_edge_count ?? 0)}`;
    }
    return `<tr><td>${Number(report.stage_index)}</td>`
      + `<td class="${verdictClass(report.verdict)}">${escapeText(String(report.verdict || ""))}</td>`
      + `<td>${detail}</td></tr>`;
  }).join("");
  return `<table class="print-qa-table"><thead><tr>`
    + `<th>Stage</th><th>Shell QA</th><th>Detail</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function verdictClass(verdict) {
  if (verdict === "CONSISTENT") return "qa-ok";
  if (verdict === "ISSUES") return "qa-issue";
  return "qa-na";
}

function formatMm(value) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(2) : "—";
}

export async function runPrintPackage() {
  if (state.guided.print.busy) return;
  state.guided.print.busy = true;
  state.guided.print.status = "Building your printable files...";
  renderGuidedPrint();
  try {
    const result = await requestPrintPackage(planJson());
    if (result.ok === false) {
      state.guided.print.result = null;
      state.guided.print.status = (result.errors || ["Could not build files."]).join("; ");
    } else {
      state.guided.print.result = result;
      state.guided.print.status =
        `Files built: ${result.stage_count} stage file(s). Download the zip for your own review, or the email draft to send the files to yourself. Physical use remains your own responsibility and risk.`;
      downloadBase64(result.zip_base64, result.filename, "application/zip");
    }
  } catch (error) {
    state.guided.print.result = null;
    state.guided.print.status = error.message;
  } finally {
    state.guided.print.busy = false;
    renderGuidedPrint();
  }
}

// Re-download the already-built artifacts (zip / .eml) without rebuilding.
export function downloadPrintArtifact(kind) {
  const result = state.guided.print.result;
  if (!result) return;
  if (kind === "zip") downloadBase64(result.zip_base64, result.filename, "application/zip");
  if (kind === "email") downloadBase64(result.email_eml_base64, result.email_filename, "message/rfc822");
}

function downloadBase64(b64, filename, type) {
  const bytes = Uint8Array.from(atob(b64), (char) => char.charCodeAt(0));
  const blob = new Blob([bytes], { type });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.append(link);
  link.click();
  const href = link.href;
  link.remove();
  URL.revokeObjectURL(href);
}

function escapeText(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}
