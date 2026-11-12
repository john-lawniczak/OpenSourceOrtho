import { selectedChatCase } from "./chat_context.js";
import { collapseChatComposer } from "./chat_composer.js";
import { requestToothGoal } from "./tooth_goal_ui.js";
import { askPlanAssistant, el, state, streamPlanAssistant } from "./state.js";
import { planJson } from "./plan.js";
import { renderChat } from "./chat_view.js";
import { beginChatRequest, finishChatRequest } from "./chat_persistence.js";

export async function sendChatMessage(uiContext) {
  const message = state.chat.input.trim();
  if (!message || state.chat.busy || !connectionReady()) return;
  const history = state.chat.messages
    .filter((item) => !item.failed && !item.pending && (item.role === "user" || item.role === "assistant"))
    .slice(-16).map(({ role, content }) => ({ role, content }));
  const editing = selectedChatCase() === "workspace" && el("chatEditMode").checked;
  const user = { role: "user", prompt: message,
    content: editing ? `Tooth ${state.manualEdit.selectedTooth} · ${message}` : message };
  const pending = { role: "assistant", content: "Reading your plan…", pending: true };
  const request = beginChatRequest();
  state.chat.busy = true;
  state.chat.status = "Reading your plan…";
  state.chat.messages.push(user, pending);
  state.chat.input = "";
  collapseChatComposer();
  renderChat();
  try {
    if (editing) {
      const answer = await requestToothGoal(message);
      if (request.signal.aborted) return;
      pending.content = answer;
      state.chat.status = "Preview ready";
    } else {
      const result = await requestAnswer(message, history, uiContext, pending, request.signal);
      if (request.signal.aborted) return;
      if (result.ok === false) throw new Error((result.errors || ["AI chat is not available."]).join(" "));
      const assistant = [...result.session.messages].reverse().find((item) => item.role === "assistant");
      pending.content = assistant?.content || "No answer returned.";
      state.chat.sessionId = result.session.session_id;
      state.chat.status = "Ready";
    }
  } catch (error) {
    if (request.signal.aborted) return;
    pending.failed = true;
    pending.content = error.message;
    user.failed = true; // Failed attempts must not be duplicated in follow-up context.
    if (!state.chat.input) state.chat.input = message;
    state.chat.status = "Couldn’t send · prompt kept for retry";
  } finally {
    finishChatRequest(request);
    if (!request.signal.aborted) {
      pending.pending = false;
      state.chat.busy = false;
      renderChat();

    }
  }
}

function connectionReady() {
  const connector = state.chat.connectors.find((item) => item.kind === state.chat.provider);
  let missing = null;
  if (connector?.requires_api_key && state.chat.provider !== "mcp" && !el("chatApiKey").value.trim()) missing = "chatApiKey";
  else if (["mcp", "open-source"].includes(state.chat.provider) && !state.chat.agentEndpoint.trim()) missing = "agentEndpoint";
  else if (state.chat.provider !== "local" && !state.chat.agentAccessEnabled) missing = "agentAccessEnabled";
  if (!missing) return true;
  el("chatSettingsDialog").showModal();
  el(missing).focus();
  return false;
}

async function requestAnswer(message, history, uiContext, pending, signal) {
  // Credentials stay in the DOM and are transmitted only on explicit send.
  const payload = {
    plan: planJson(), message, history, provider: state.chat.provider, model: state.chat.model,
    context_scope: state.chat.contextScope, case_source: selectedChatCase(),
    ui_context: { ...uiContext, selected_tooth: state.manualEdit.selectedTooth,
      stage_index: Number(el("stageSlider").value || 0), view: state.view, sample: state.sample.active },
    api_key: el("chatApiKey").value.trim() || undefined,
    endpoint: state.chat.agentEndpoint.trim() || undefined,
    share_acknowledged: state.chat.agentAccessEnabled,
    session_id: state.chat.sessionId || undefined,
  };
  const connector = state.chat.connectors.find((item) => item.kind === state.chat.provider);
  if (!connector?.supports_streaming) return askPlanAssistant(payload, signal);
  pending.content = "";
  let finalResult = null;
  await streamPlanAssistant(payload, {
    onDelta: (text) => {
      if (signal.aborted) return;
      pending.content += text;
      renderChat();
    },
    onDone: (result) => { finalResult = result; },
  }, signal);
  return finalResult || { ok: false, errors: ["AI chat stream ended without a final response."] };
}
