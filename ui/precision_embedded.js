// The standalone editor remains linkable; embedded mode returns to its parent.
export function setupEmbeddedPrecision(saving) {
  const params = new URLSearchParams(location.search);
  if (window.parent === window || params.get("embedded") !== "1") return;
  document.body.classList.add("precision-embedded");
  if (params.get("sample") !== "1") {
    document.querySelector(".review-baseline-entry").hidden = true;
    document.getElementById("loadSample").hidden = true;
    document.querySelector(".review-import").open = true;
  }
  window.confirmPrecisionExit = saving.canLeave;
  document.getElementById("reviewWorkspaceLink").onclick = event => {
    event.preventDefault(); parent.postMessage({ type: "precision-return" }, location.origin);
  };
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); parent.postMessage({ type: "precision-return" }, location.origin); }
  });
}
