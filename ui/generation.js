import { rowsFromPlan } from "./core.js";
import { planJson } from "./plan.js";
import { renderAll, renderGeneration } from "./render.js";
import { el, requestPlanGeneration, state } from "./state.js";

export async function generatePlan() {
  if (state.generation.busy) return;
  state.generation.busy = true;
  state.generation.status = "Reviewing scan, generating, and orchestrating checks...";
  renderGeneration();
  try {
    // The API key is read from the DOM only at request time (never persisted),
    // matching the chat layer. The external-agent acknowledgement opts into the
    // optional model review step; without it the pipeline runs fully offline.
    const apiKey = el("chatApiKey").value.trim();
    const result = await requestPlanGeneration({
      plan: planJson(),
      landmarks: state.generation.landmarks || undefined,
      acknowledge_educational: state.generation.acknowledged,
      notes: state.generation.notes.trim() || undefined,
      provider: state.chat.provider,
      model: state.chat.model,
      api_key: apiKey || undefined,
      endpoint: state.chat.agentEndpoint.trim() || undefined,
      share_acknowledged: state.chat.agentAccessEnabled,
    });
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
        state.view = "overlay";
      }
    }
  } catch (error) {
    state.generation.result = null;
    state.generation.status = error.message;
  } finally {
    state.generation.busy = false;
    renderAll();
  }
}
