// A proposal is separate from authored rows. Exports continue to use the applied plan.
import { el, state, evaluatePlan } from "./state.js";
import { rowsFromPlan } from "./core.js";
import { planJson } from "./plan.js";
import { acceptGoalEvaluation, renderAll, renderStagePreview } from "./render.js";

const snapshot = () => JSON.stringify(planJson());
let requestVersion = 0;

export function discardGoalPreview() {
  requestVersion++;
  state.goalPreview = null;
  state.goalBusy = false;
}

export async function requestToothGoal(message, adjustment) {
  if (state.goalBusy) throw new Error("A tooth preview is already being prepared.");
  if (state.goalPreview) throw new Error("Apply or discard the current preview first.");
  const baseline = snapshot();
  const selected = state.manualEdit.selectedTooth;
  if (!selected) throw new Error("Select a reviewed tooth first.");
  const version = ++requestVersion;
  state.goalBusy = true;
  renderAll();
  try {
    const response = await fetch("/api/preview-goal", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan: JSON.parse(baseline), selected_tooth: selected,
        message, adjustment, provider: state.chat.provider, model: state.chat.model,
        api_key: adjustment ? undefined : el("chatApiKey").value.trim() || undefined,
        endpoint: state.chat.agentEndpoint.trim() || undefined,
        share_acknowledged: state.chat.agentAccessEnabled }),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error((result.errors || ["Preview request failed."]).join(" "));
    if (version !== requestVersion || snapshot() !== baseline) throw new Error("The working plan changed; request a new preview.");
    if (result.clarification) return result.clarification;
    const evaluation = await evaluatePlan(result.plan);
    if (evaluation.ok === false || !evaluation.frames) throw new Error("The proposal could not be evaluated.");
    if (version !== requestVersion || snapshot() !== baseline) throw new Error("The working plan changed; request a new preview.");
    state.goalPreview = { ...result, baseline, evaluation };
    state.view = "planned";
    if (state.userMode === "simple") state.guided.step = "plan";
    el("stageSlider").max = String(Math.max(0, evaluation.frames.length - 1));
    el("stageSlider").value = el("stageSlider").max;
    return `Tooth ${result.change.tooth}: ${result.finding.message} Drag the stage timeline to inspect it, then Apply or Discard.`;
  } finally {
    if (version === requestVersion) state.goalBusy = false;
    renderAll();
    renderStagePreview();
  }
}

export function renderGoalPreview() {
  const preview = state.goalPreview;
  if (preview && snapshot() !== preview.baseline) discardGoalPreview();
  el("goalPreviewPanel").hidden = !state.goalPreview && !state.goalBusy;
  el("goalPreviewText").textContent = state.goalBusy ? "Preparing staged preview…"
    : state.goalPreview ? `Tooth ${preview.change.tooth}: ${preview.finding.message} Projected timeline: ${preview.timeline.projected_duration_weeks} weeks. Only applied changes are exported.` : "";
  el("applyGoalPreview").disabled = !state.goalPreview;
  el("discardGoalPreview").disabled = !state.goalPreview;
}

document.body.addEventListener("click", event => {
  const id = event.target.closest?.("button")?.id;
  if (id === "applyGoalPreview") {
    const proposal = state.goalPreview;
    if (proposal && snapshot() === proposal.baseline) {
      state.manualEdit.undoStack = [...(state.manualEdit.undoStack || []), state.rows.map(row => ({ ...row }))].slice(-20);
      state.rows = rowsFromPlan(proposal.plan);
      acceptGoalEvaluation(proposal.evaluation);
    }
    discardGoalPreview();
    renderAll();
  }
  if (id === "discardGoalPreview") { discardGoalPreview(); renderAll(); renderStagePreview(); }
});
