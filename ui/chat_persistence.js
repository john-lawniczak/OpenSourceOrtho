import { el, state } from "./state.js";

const STORAGE_KEY = "orthoplan-chat-session-v1";
const PROVIDERS = ["local", "openai", "anthropic", "claude-code", "deepseek", "glm", "mcp", "open-source"];
let activeRequest = null;
let storageAvailable = true;

// Explicit allowlist: never serialize credentials, endpoints, consent or plans.
export function saveChatSession() {
  const chat = state.chat;
  const data = {
    caseSource: chat.caseSource || "auto",
    version: 1, provider: chat.provider, modelByProvider: chat.modelByProvider,
    input: chat.input, collapsed: chat.collapsed, expanded: chat.expanded,
    sessionId: chat.sessionId,
    messages: chat.messages.map(({ role, content, pending, failed, prompt }) => ({ role, content, pending, failed, prompt })),
  };
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    storageAvailable = true;
  } catch {
    storageAvailable = false;
  }
  const notice = el("chatPersistenceNotice");
  if (notice) notice.textContent = storageAvailable
    ? "Chat and drafts survive navigation and reloads in this tab. New chat clears them. New requests use the selected context."
    : "Browser storage is unavailable or full. Keep this page open to retain your chat and draft.";
}

export function beginChatRequest() {
  activeRequest = new AbortController();
  return activeRequest;
}

export function finishChatRequest(request) {
  if (activeRequest === request) activeRequest = null;
}

function recoverPendingTurn() {
  const chat = state.chat;
  let interrupted = false;
  chat.messages.forEach((message, index) => {
    if (!message.pending) return;
    message.pending = false;
    message.failed = true;
    message.content = "This request was interrupted by navigation. Review the prompt and send again when ready.";
    const user = chat.messages[index - 1];
    if (user?.role === "user") {
      user.failed = true;
      if (!chat.input) chat.input = user.prompt || user.content;
    }
    interrupted = true;
  });
  chat.busy = false;
  if (interrupted) chat.status = "Request interrupted · prompt kept";
}

function restoreChatSession() {
  try {
    const data = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    if (!data || data.version !== 1 || !Array.isArray(data.messages)) return;
    const chat = state.chat;
    if (PROVIDERS.includes(data.provider)) chat.provider = data.provider;
    for (const provider of PROVIDERS) {
      const model = data.modelByProvider?.[provider];
      if (typeof model === "string" && model.length <= 200) chat.modelByProvider[provider] = model;
    }
    if (["auto", "workspace", "user_one"].includes(data.caseSource)) chat.caseSource = data.caseSource;
    chat.input = typeof data.input === "string" ? data.input : "";
    chat.collapsed = data.collapsed === true;
    chat.expanded = data.expanded === true;
    chat.sessionId = typeof data.sessionId === "string" ? data.sessionId : null;
    chat.messages = data.messages.filter((item) => item && ["user", "assistant"].includes(item.role)
      && typeof item.content === "string").map((item) => ({
      role: item.role, content: item.content, pending: item.pending === true, failed: item.failed === true,
      prompt: typeof item.prompt === "string" ? item.prompt : undefined,
    }));
    chat.status = "Conversation restored · new requests use the selected context";
    recoverPendingTurn();
  } catch {
    state.chat.status = "Saved chat could not be restored";
  }
}

export function initializeChatPersistence(render) {
  restoreChatSession();
  const entry = new URL(location.href);
  if (entry.searchParams.get("chat_case") === "user_one") {
    state.chat.caseSource = "user_one";
    entry.searchParams.delete("chat_case"); history.replaceState(history.state, "", entry);
  }
  window.addEventListener("pagehide", () => {
    activeRequest?.abort();
    activeRequest = null;
    recoverPendingTurn();
    // Full-page navigation ends the credential/consent lifetime, including BFCache.
    el("chatApiKey").value = "";
    state.chat.apiKeyPresent = false;
    state.chat.agentAccessEnabled = false;
    state.chat.agentEndpoint = "";
    saveChatSession();
  });
  window.addEventListener("pageshow", (event) => { if (event.persisted) render(); });
}
