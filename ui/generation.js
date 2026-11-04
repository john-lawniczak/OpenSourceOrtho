import { rowsFromPlan } from "./core.js";
import { planJson } from "./plan.js";
import { renderAll, renderGeneration } from "./render.js";
import { el, requestPlanGeneration, state } from "./state.js";

export async function generatePlan() {
  if (state.generation.busy) return;
  if (state.goalPreview || state.goalBusy) {
    state.generation.status = "Apply or discard the tooth preview first.";
    renderAll();
    return;
  }
  if (state.userMode === "simple" && (state.scanUnits !== "mm" || !state.segmentation.applied)) {
    state.generation.status = "Confirm mm units and review individual teeth in Upload first.";
    state.guided.step = "upload";
    renderAll();
    return;
  }
  const generation = state.generation;
  const segmentation = state.segmentation;
  const baseline = JSON.stringify(planJson());
  const parameters = () => JSON.stringify([generation.landmarks, generation.notes, state.simpleGoal]);
  const initialParameters = parameters();
  const isCurrent = () => state.generation === generation && state.segmentation === segmentation
    && JSON.stringify(planJson()) === baseline && parameters() === initialParameters;
  generation.busy = true;
  state.generation.status = "Reviewing scan, generating, and orchestrating checks...";
  renderGeneration();
  try {
    // The API key is read from the DOM only at request time (never persisted),
    // matching the chat layer. The external-agent acknowledgement opts into the
    // optional model review step; without it the pipeline runs fully offline.
    const apiKey = el("chatApiKey").value.trim();
    const result = await requestPlanGeneration({
      plan: JSON.parse(baseline),
      landmarks: state.generation.landmarks || undefined,
      acknowledge_educational: state.generation.acknowledged,
      notes: [state.userMode === "simple" ? `Exploration focus: ${state.simpleGoal.replaceAll("-", " ")}.` : "",
        state.generation.notes.trim()].filter(Boolean).join(" ") || undefined,
      provider: state.chat.provider,
      model: state.chat.model,
      api_key: apiKey || undefined,
      endpoint: state.chat.agentEndpoint.trim() || undefined,
      share_acknowledged: state.chat.agentAccessEnabled,
    });
    if (!isCurrent()) {
      generation.status = "The working plan changed; generate a new preview.";
      return;
    }
    if (result.ok === false) {
      state.generation.result = null;
      state.generation.status = (result.errors || ["Generation failed."]).join("; ");
    } else {
      state.generation.result = result;
      state.generation.status = `source: ${result.source} · ${result.correctness.verdict}`;
      // Load generated staging into the editable rows so the existing review,
      // timeline, and 3D pipeline visualize it - the UI never re-stages itself.
      if (result.plan?.stages?.length) {
        state.rows = rowsFromPlan(result.plan);
        state.activeStep = "review";
        if (state.userMode === "simple") state.guided.step = "plan";
        state.view = "overlay";
      }
    }
  } catch (error) {
    generation.result = null;
    generation.status = error.message;
  } finally {
    generation.busy = false;
    renderAll();
  }
}
