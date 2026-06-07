// Guided wizard: the simplified, primary flow for non-technical first-time
// users. It is a step-by-step walk: upload scans -> review which teeth move and
// how long -> small details -> review the plan (with a prominent AI box) ->
// slide through the 3D preview -> get printable files to email/attach.
//
// This module owns ONLY the wizard's step routing and per-step presentation. It
// reuses the technician singletons (the 3D viewer block, the AI chat block, the
// upload stack) by relocating them into guided step hosts - event handling is
// delegated on document.body and renders target elements by id, so moving a
// subtree is safe and avoids a second WebGL context. Engine/generation/chat all
// flow through the same helpers the technician page uses.

import { el, state } from "./state.js";
import { planJson } from "./plan.js";
import { requestPrintPackage } from "./state.js";

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

function relocate(blockId, hostId) {
  const block = el(blockId);
  const host = el(hostId);
  if (block && host && block.parentElement !== host) host.appendChild(block);
}

// Relocate shared singletons into the host for the active mode/step. In guided
// mode the viewer/AI/upload live inside their wizard steps; in technician mode
// they return to the review workspace.
export function placeSharedBlocks() {
  if (state.userMode === "simple") {
    relocate("simpleUpload", "guidedUploadHost");
    relocate("viewerBlock", "guidedPreviewHost");
    relocate("aiChatBlock", "guidedAiHost");
  } else {
    relocate("simpleUpload", "techUploadHost");
    relocate("viewerBlock", "techViewerHost");
    relocate("aiChatBlock", "techAiHost");
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
  const t = state.lastEval?.timeline;
  if (!t) {
    if (headline) headline.innerHTML = "";
    if (summary) summary.innerHTML = "<li>Build your plan in step 2 to see a summary and timeline here.</li>";
    return;
  }
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

function renderGuidedPrint() {
  const status = el("guidedPrintStatus");
  if (status) status.textContent = state.guided.print.status || "";
  const button = el("guidedPrint");
  if (button) button.disabled = state.guided.print.busy;
  const links = el("guidedPrintLinks");
  if (links) links.hidden = !state.guided.print.result;
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
        `Ready: ${result.stage_count} stage file(s). Download the zip to 3D print, or the email draft to send the files to yourself.`;
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
