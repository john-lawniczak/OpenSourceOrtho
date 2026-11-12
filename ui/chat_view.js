import { renderChatContext } from "./chat_context.js";
import { initializeChatComposer } from "./chat_composer.js";
import { saveChatSession } from "./chat_persistence.js";
import { el, state } from "./state.js";
import { renderChatMessages } from "./chat_thread.js";

const AI_KEY_HELP = {
  local: "Offline. No key needed.",
  anthropic: "Paste an Anthropic API key here. Use Claude Code instead for local CLI sign-in.",
  openai: "Paste the complete key from platform.openai.com. Kept for this page only.",
  "claude-code": "Uses your signed-in Claude Code CLI on this machine. To enter an API key, choose Claude API (Anthropic).",
  deepseek: "Use a DeepSeek API key. Kept for this tab only.",
  glm: "Use a Z.ai standard API key. Kept for this tab only.",
  mcp: "Use your host’s API key and endpoint. Kept for this tab only.",
  "open-source": "Enter your model endpoint. API key is optional.",
};

initializeChatComposer();

export function renderChat() {
  renderChatContext();
  document.body.dataset.chatCollapsed = state.chat.collapsed ? "1" : "";
  el("aiChatBlock").inert = state.chat.collapsed;
  renderChatConnectorControls();
  el("chatInput").value = state.chat.input;
  el("agentAccessEnabled").checked = state.chat.agentAccessEnabled;
  el("agentEndpoint").value = state.chat.agentEndpoint;
  el("sendChat").disabled = state.chat.busy || !state.chat.input.trim();
  const toggle = el("toggleChatPanel");
  if (toggle) {
    toggle.textContent = state.chat.collapsed ? "Show" : "Hide";
    toggle.setAttribute("aria-expanded", state.chat.collapsed ? "false" : "true");
    toggle.setAttribute("aria-label", state.chat.collapsed ? "Expand AI chat" : "Collapse AI chat");
  }
  // The reopen tab is the only visible handle once the panel slides off-screen.
  const reopenTab = el("chatReopenTab");
  if (reopenTab) reopenTab.hidden = !state.chat.collapsed;
  const contextEl = el("chatStageContext");
  if (contextEl) contextEl.textContent = chatStageLabel();
  // The local helper needs no key, so hide the key field for it; for any real
  // provider show the field with provider-specific, plain-language instructions.
  const isLocal = state.chat.provider === "local";
  const connector = chatConnector(state.chat.provider);
  el("aiKeyField").hidden = isLocal || state.chat.provider === "claude-code";
  el("chatEndpointField").hidden = !["mcp", "open-source"].includes(state.chat.provider);
  el("chatSharingField").hidden = isLocal;
  el("chatCustomModelField").hidden = el("chatModel").value !== "__custom__";
  el("chatConnection").textContent = isLocal ? "Local helper · offline" : `${connector?.label} · ${state.chat.model}`;
  el("aiKeyHelp").textContent = AI_KEY_HELP[state.chat.provider] || AI_KEY_HELP.local;
  el("chatStatus").textContent = state.chat.status;
  for (const id of ["chatProvider", "chatModel", "chatCustomModel", "chatApiKey", "agentEndpoint", "agentAccessEnabled"]) el(id).disabled = state.chat.busy;
  el("newChat").disabled = state.chat.busy || (!state.chat.messages.length && !state.chat.input);
  el("sendChat").textContent = state.chat.busy ? "Thinking…" : "Send ↑";
  document.body.dataset.chatFocus = state.chat.expanded ? "1" : "";
  el("expandChat").setAttribute("aria-pressed", String(Boolean(state.chat.expanded)));
  el("expandChat").textContent = state.chat.expanded ? "Dock" : "Expand";
  saveChatSession();
  renderChatMessages();
}

function chatConnector(kind) {
  return (state.chat.connectors || []).find((connector) => connector.kind === kind);
}

function renderChatConnectorControls() {
  const provider = el("chatProvider");
  const model = el("chatModel");
  const custom = el("chatCustomModel");
  const connectors = state.chat.connectors || [];
  const providerSignature = connectors.map((item) => `${item.kind}:${item.label}`).join("|");
  if (provider.dataset.signature !== providerSignature) {
    provider.replaceChildren(...connectors.map((connector) => {
      const option = document.createElement("option");
      option.value = connector.kind;
      option.textContent = connector.label;
      return option;
    }));
    provider.dataset.signature = providerSignature;
  }
  provider.value = state.chat.provider;
  const connector = chatConnector(state.chat.provider) || connectors[0];
  const models = connector?.models?.length ? connector.models : [connector?.model || state.chat.model];
  const modelSignature = `${connector?.kind || ""}:${models.join("|")}:${connector?.allow_custom_model ? "custom" : ""}`;
  if (model.dataset.signature !== modelSignature) {
    const options = models.map((modelId) => {
      const option = document.createElement("option");
      option.value = modelId;
      option.textContent = modelId;
      return option;
    });
    if (connector?.allow_custom_model) {
      const option = document.createElement("option");
      option.value = "__custom__";
      option.textContent = "Custom model ID";
      options.push(option);
    }
    model.replaceChildren(...options);
    model.dataset.signature = modelSignature;
  }
  const selected = state.chat.modelByProvider[state.chat.provider] || connector?.model || models[0];
  const customSelected = connector?.allow_custom_model && !models.includes(selected);
  model.value = customSelected ? "__custom__" : selected;
  custom.value = customSelected ? selected : custom.value;
  state.chat.model = customSelected ? custom.value : model.value;
}

function chatStageLabel() {
  if (state.userMode === "simple") {
    const labels = {
      upload: "Guided step 1: Upload",
      plan: "Guided step 2: Teeth and time",
      details: "Guided step 3: Details",
      review: "Guided step 4: Review",
      preview: "Guided step 5: 3D preview",
      print: "Guided step 6: Print / send",
    };
    return labels[state.guided.step] || "Guided workflow";
  }
  const labels = {
    upload: "Technician: Upload",
    availability: "Technician: Data",
    settings: "Technician: Settings",
    stages: "Technician: Stages",
    review: "Technician: Review",
    toothmap: "Reference: Tooth map",
    glossary: "Reference: Glossary",
    photos: "Reference: Imaging guide",
  };
  return labels[state.activeStep] || "Technician workflow";
}


// View actions never alter the plan.
el("expandChat").addEventListener("click", () => {
  state.chat.expanded = !state.chat.expanded;
  renderChat();
});
el("newChat").addEventListener("click", () => {
  if (state.chat.busy) return;
  state.chat.messages = [];
  state.chat.input = "";
  state.chat.sessionId = null;
  state.chat.status = "New conversation";
  renderChat();
  el("chatInput").focus();
});
el("chatStarters").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  state.chat.input = button.textContent;
  renderChat();
  el("chatInput").focus();
});

el("chatMessages").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-reuse-prompt]");
  if (!button || state.chat.busy) return;
  const message = state.chat.messages[Number(button.dataset.reusePrompt)];
  state.chat.input = message.prompt || message.content;
  renderChat();
  el("chatInput").focus();
});
