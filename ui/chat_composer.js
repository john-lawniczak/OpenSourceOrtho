import { el } from "./state.js";

export function collapseChatComposer() {
  const composer = el("chatComposer");
  if (composer.contains(document.activeElement)) document.activeElement.blur();
  composer.dataset.expanded = "false";
  el("collapseChatComposer").setAttribute("aria-expanded", "false");
}

export function initializeChatComposer() {
  const composer = el("chatComposer");
  composer.addEventListener("focusin", event => {
    if (event.target.id === "collapseChatComposer") return;
    composer.dataset.expanded = "true";
    el("collapseChatComposer").setAttribute("aria-expanded", "true");
  });
  composer.addEventListener("focusout", event => {
    if (!composer.contains(event.relatedTarget)) collapseChatComposer();
  });
  el("collapseChatComposer").onclick = collapseChatComposer;
}
