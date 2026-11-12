import { saveChatSession } from "./chat_persistence.js";
import { el, state } from "./state.js";

// Native dialog supplies focus trapping, Escape dismissal, and focus restoration.
const dialog = document.getElementById("chatSettingsDialog");
document.getElementById("openChatSettings").addEventListener("click", () => dialog.showModal());

export function confirmWorkspaceMode(mode, apply) {
  if (mode === state.userMode) return;
  const name = mode === "simple" ? "Guided" : "Technician";
  if (!window.confirm(`Switch to ${name}? The workspace layout will change. Your scans, edits and conversation will stay in place.`)) return;
  dialog.close();
  apply(mode);
}

export function updateChatSetting(target) {
  if (target.id === "chatProvider") {
    state.chat.provider = target.value;
    el("chatApiKey").value = "";
    state.chat.apiKeyPresent = false;
    state.chat.agentAccessEnabled = false;
    el("agentAccessEnabled").checked = false;
    el("agentEndpoint").value = "";
    state.chat.agentEndpoint = "";
    state.chat.model = state.chat.modelByProvider[state.chat.provider] || defaultModelForProvider(state.chat.provider);
  }
  if (target.id === "chatModel") {
    state.chat.model = target.value === "__custom__"
      ? el("chatCustomModel").value.trim() || "custom-model"
      : target.value;
    if (state.chat.model) state.chat.modelByProvider[state.chat.provider] = state.chat.model;
  }
  if (target.id === "chatCustomModel") {
    state.chat.model = target.value.trim();
    if (state.chat.model) state.chat.modelByProvider[state.chat.provider] = state.chat.model;
  }
  if (target.id === "chatCaseSource") state.chat.caseSource = target.value;
  if (target.id === "chatInput") state.chat.input = target.value;
  if (target.id === "chatApiKey") state.chat.apiKeyPresent = Boolean(target.value.trim());
  if (target.id === "agentAccessEnabled") state.chat.agentAccessEnabled = target.checked;
  saveChatSession();
}

function defaultModelForProvider(provider) {
  const connector = (state.chat.connectors || []).find((item) => item.kind === provider);
  return connector?.model || connector?.models?.[0] || "local-educational-helper";
}
