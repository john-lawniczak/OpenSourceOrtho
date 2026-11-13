import { el, state } from "./state.js";
import { addNoteFocusTeeth, seedSampleFocus } from "./plan_focus.js";

const drafts = new Map();
let mounted = false;
let focusTimer, pendingFocus;
const key = () => state.sample.active ? "sample:USER_ONE" : `personal:${el("planId").value || "draft-001"}`;
const storageKey = context => `orthoplan-plan-brief-v1:${context}`;

function flushFocusTags() {
  clearTimeout(focusTimer);
  if (!pendingFocus) return;
  const { context, text } = pendingFocus; pendingFocus = null;
  addNoteFocusTeeth(text, context);
}

function draft(context) {
  if (!drafts.has(context)) {
    let text = null, status = "Not yet saved. Notes save here as you type.";
    try {
      text = localStorage.getItem(storageKey(context));
      if (text !== null) status = "Saved in this browser for this plan.";
    } catch { status = "Browser storage is unavailable. Download notes to keep a copy."; }
    drafts.set(context, { text: text || "", status, hasSaved: text !== null, loading: false, attempted: false, revision: 0, error: false });
  }
  return drafts.get(context);
}

async function loadSampleGoals(context, entry) {
  entry.loading = true; entry.attempted = true; entry.error = false;
  if (!entry.hasSaved) entry.status = "Loading sample goals…";
  const revision = entry.revision;
  try {
    const response = await fetch("/api/sample-plan-brief");
    if (!response.ok) throw new Error("Sample goals unavailable");
    const data = await response.json();
    if (!data.ok || typeof data.text !== "string") throw new Error("Sample goals unavailable");
    seedSampleFocus(data.focus_teeth);
    if (entry.revision !== revision || entry.hasSaved) return;
    entry.text = data.text;
    entry.status = data.available ? "User-reported sample goals. Your edits save in this browser." : "No supplied goals in this installation. Add your own discussion notes.";
  } catch {
    if (entry.revision === revision && !entry.hasSaved) {
      entry.status = "Could not load sample goals. Retry, or write your own notes.";
      entry.error = true;
    }
  } finally {
    entry.loading = false;
    if (key() === context) renderPlanBrief();
  }
}

function summaries(text) {
  const lines = text.split(/\r?\n/).map(line => line.replace(/^\s*[-*•]\s*/, "").trim()).filter(Boolean);
  for (const list of document.querySelectorAll("[data-plan-brief-summary]")) {
    list.replaceChildren(...(lines.length ? lines : ["No goals added yet. Describe your plan in step 3."]).map(line => {
      const item = document.createElement("li"); item.textContent = line; return item;
    }));
  }
}

function resize() {
  const input = el("planBriefText");
  if (!input.clientWidth) return;
  input.style.height = "auto";
  input.style.height = `${Math.max(210, input.scrollHeight)}px`;
}

function mount() {
  const input = el("planBriefText");
  input.addEventListener("input", event => {
    // Discussion text does not invalidate geometry or trigger plan evaluation.
    event.stopPropagation();
    const context = key(), entry = draft(context);
    entry.text = input.value; entry.revision++; entry.error = false;
    try {
      localStorage.setItem(storageKey(context), entry.text);
      entry.hasSaved = true; entry.status = "Saved in this browser for this plan.";
    } catch { entry.status = "Could not save in this browser. Download notes to keep a copy."; }
    renderPlanBrief();
    // Wait for a typing pause so @123 is not saved midway through as tooth 12.
    clearTimeout(focusTimer); pendingFocus = { context, text: entry.text };
    focusTimer = setTimeout(flushFocusTags, 400);
  });
  input.addEventListener("blur", flushFocusTags);
  window.addEventListener("pagehide", flushFocusTags);
  el("retryPlanBrief").addEventListener("click", () => {
    const context = key();
    void loadSampleGoals(context, draft(context)); renderPlanBrief();
  });
  for (const button of document.querySelectorAll("[data-plan-brief-edit]")) {
    button.addEventListener("click", () => document.querySelector('#guidedRail [data-gstep-nav="details"] button').click());
  }
  el("downloadPlanBrief").addEventListener("click", () => {
    const text = `Discussion goals — ${state.sample.active ? "USER_ONE" : el("planTitle").value}\n\n${draft(key()).text}\n\nUser-stated goals, not prescribed movements or a reviewed treatment plan.\n`;
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "plan-discussion-notes.txt";
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  new ResizeObserver(resize).observe(input);
  mounted = true;
}

export function renderPlanBrief() {
  if (!el("planBriefText")) return;
  if (!mounted) mount();
  const context = key(), entry = draft(context);
  if (state.sample.active && !entry.attempted) void loadSampleGoals(context, entry);
  if (el("planBriefText").value !== entry.text) el("planBriefText").value = entry.text;
  el("planBriefStatus").textContent = entry.status;
  el("samplePlanBriefCaveat").hidden = !state.sample.active;
  el("downloadPlanBrief").disabled = !entry.text.trim();
  el("retryPlanBrief").hidden = !entry.error || !state.sample.active;
  el("retryPlanBrief").disabled = entry.loading;
  summaries(entry.text); resize();
}
