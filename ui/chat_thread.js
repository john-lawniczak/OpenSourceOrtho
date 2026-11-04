import { el, state } from "./state.js";

// Update existing turns in place: streamed text must never replace a user's
// prompt, duplicate a turn, or drag someone away from older messages.
export function renderChatMessages() {
  const host = el("chatMessages");
  const messages = state.chat.messages;
  const nearBottom = host.scrollHeight - host.scrollTop - host.clientHeight < 64;
  const newTurn = messages.length > host.querySelectorAll(".chat-message").length;
  el("chatStarters").hidden = messages.length > 0;
  host.setAttribute("aria-busy", String(state.chat.busy));
  if (!messages.length) {
    if (!host.querySelector(".chat-welcome")) {
      const welcome = document.createElement("div");
      welcome.className = "chat-welcome";
      const title = document.createElement("h3");
      title.textContent = "Understand your plan";
      const hint = document.createElement("p");
      hint.textContent = "Explore the preview, findings, and missing records. Answers are educational, not treatment approval.";
      welcome.append(title, hint);
      host.replaceChildren(welcome);
    }
    return;
  }
  host.querySelector(".chat-welcome")?.remove();
  while (host.children.length > messages.length) host.lastElementChild.remove();
  messages.forEach((message, index) => {
    let node = host.children[index];
    if (!node) { node = messageNode(message.role); host.append(node); }
    const content = node.querySelector("p");
    if (content.textContent !== message.content) content.textContent = message.content;
    node.classList.toggle("is-pending", Boolean(message.pending));
    node.classList.toggle("is-error", Boolean(message.failed));
    node.querySelector("strong").textContent = message.role === "user" ? "You"
      : message.failed ? "Couldn’t send" : "Plan assistant";
  });
  if (nearBottom || newTurn) host.scrollTop = host.scrollHeight;
}

function messageNode(role) {
  const node = document.createElement("article");
  node.className = `chat-message ${role === "user" ? "user" : "assistant"}`;
  const label = document.createElement("strong");
  const content = document.createElement("p");
  // Text content is intentional: model output and prompts are untrusted.
  node.append(label, content);
  return node;
}
