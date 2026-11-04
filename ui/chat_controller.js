import { requestToothGoal } from "./tooth_goal_ui.js";
import { askPlanAssistant, el, state, streamPlanAssistant } from "./state.js";
import { planJson } from "./plan.js";
import { renderChat } from "./chat_view.js";

export async function sendChatMessage(uiContext) {
  const message = state.chat.input.trim();
  if (!message || state.chat.busy) return;
  if (state.chat.provider !== "local" && !state.chat.agentAccessEnabled) {
    el("chatSettingsDialog").showModal();
    el("agentAccessEnabled").focus();
    return;
  }
  const history = state.chat.messages
    .filter((item) => !item.failed && !item.pending && (item.role === "user" || item.role === "assistant"))
    .slice(-16).map(({ role, content }) => ({ role, content }));
  state.chat.busy = true;
  state.chat.status = "Reading your plan…";
  const content = el("chatEditMode").checked ? `Tooth ${state.manualEdit.selectedTooth} · ${message}` : message;
  state.chat.messages.push({ role: "user", content });
  state.chat.messages.push({ role: "assistant", content: "Reading your plan…", pending: true });
  el("chatInput").value = "";
  state.chat.input = "";
  renderChat();
  try {
    // The API key is read straight from the DOM at send time so it is never
    // held in app state or persisted - only transmitted on an explicit "Ask AI".
    if (el("chatEditMode").checked) {
      const pending = state.chat.messages.at(-1);
      pending.content = await requestToothGoal(message);
      state.chat.status = "Preview ready";
      return;
    }
    const apiKey = el("chatApiKey").value.trim();
    const payload = {
      plan: planJson(),
      message,
      history,
      provider: state.chat.provider,
      model: state.chat.model,
      // The assistant always works from the full plan context (no scope selector).
      context_scope: state.chat.contextScope,
      ui_context: { ...uiContext, selected_tooth: state.manualEdit.selectedTooth,
        stage_index: Number(el("stageSlider").value || 0), view: state.view, sample: state.sample.active },
      api_key: apiKey || undefined,
      endpoint: state.chat.agentEndpoint.trim() || undefined,
      share_acknowledged: state.chat.agentAccessEnabled,
      session_id: state.chat.sessionId || undefined,
    };
    const pending = state.chat.messages[state.chat.messages.length - 1];
    const connector = (state.chat.connectors || []).find((item) => item.kind === state.chat.provider);
    const result = connector?.supports_streaming
      ? await streamChatPayload(payload, pending)
      : await askPlanAssistant(payload);
    if (result.ok === false) {
      pending.failed = true;
      pending.content = (result.errors || ["AI chat is not available."]).join(" ");
      state.chat.status = "Connector unavailable";
    } else {
      const assistant = [...result.session.messages].reverse().find((item) => item.role === "assistant");
      pending.content = assistant?.content || "No answer returned.";
      state.chat.sessionId = result.session.session_id;
      state.chat.status = "Ready";
    }
  } catch (error) {
    const pending = state.chat.messages[state.chat.messages.length - 1];
    if (pending?.role === "assistant") { pending.content = error.message; pending.failed = true; }
    else state.chat.messages.push({ role: "assistant", content: error.message });
    state.chat.status = "Chat request failed";
  } finally {
    state.chat.messages.at(-1).pending = false;
    state.chat.busy = false;
    el("chatInput").focus();
    renderChat();
  }
}

async function streamChatPayload(payload, pending) {
  pending.content = "";
  let finalResult = null;
  await streamPlanAssistant(payload, {
    onDelta: (text) => {
      pending.content += text;
      renderChat();
    },
    onDone: (result) => {
      finalResult = result;
    },
  });
  return finalResult || { ok: false, errors: ["AI chat stream ended without a final response."] };
}

