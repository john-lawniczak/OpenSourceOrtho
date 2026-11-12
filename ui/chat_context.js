import { el, state } from "./state.js";

export function selectedChatCase() {
  const source = state.chat.caseSource || "auto";
  return source === "auto" ? (state.sample.active && state.sample.view !== "simulation" ? "user_one" : "workspace") : source;
}

export function renderChatContext() {
  const selector = el("chatCaseSource");
  selector.value = state.chat.caseSource || "auto";
  selector.disabled = state.chat.busy;
  const userOne = selectedChatCase() === "user_one";
  el("chatEditMode").closest("label").hidden = userOne;
  if (userOne) el("chatEditMode").checked = false;
  el("chatContextHint").textContent = userOne
    ? "USER_ONE · scans, saved labels & notes, including week 18 records."
    : "Current planning workspace · select USER_ONE to discuss the saved sample scans.";
}
