if (window.parent !== window && new URLSearchParams(location.search).get("embedded") === "1") {
  const back = document.getElementById("progressBack");
  back.textContent = "← Back to scan history";
  back.onclick = event => { event.preventDefault(); parent.postMessage({ type: "scan-pair-return" }, location.origin); };
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); parent.postMessage({ type: "scan-pair-return" }, location.origin); }
  });
}
