// Apply the workspace palette before loading the heavier scan viewer module.
(() => {
  const embedded = window.parent !== window && new URLSearchParams(location.search).get("embedded") === "1";
  document.body.dataset.embedded = String(embedded);
  let workspace;
  try { if (embedded) workspace = parent.document.body; } catch { /* Standalone theme fallback. */ }
  function syncTheme() {
    let theme = workspace?.dataset.theme;
    try { theme ||= localStorage.getItem("orthoplan-theme"); } catch { /* Storage may be disabled. */ }
    document.body.dataset.theme = theme === "dark" ? "dark" : "light";
  }
  syncTheme();
  if (workspace) {
    const observer = new MutationObserver(syncTheme);
    observer.observe(workspace, { attributes: true, attributeFilter: ["data-theme"] });
    window.addEventListener("pagehide", () => observer.disconnect(), { once: true });
  }
  window.addEventListener("storage", syncTheme);
})();
