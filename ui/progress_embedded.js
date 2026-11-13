const back = document.getElementById("progressBack");
const embedded = window.parent !== window && new URLSearchParams(location.search).get("embedded") === "1";
if (embedded) {
  back.textContent = "← Back to scan history";
  back.onclick = event => { event.preventDefault(); parent.postMessage({ type: "scan-pair-return" }, location.origin); };
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); parent.postMessage({ type: "scan-pair-return" }, location.origin); }
  });
} else {
  back.onclick = () => location.assign("./");
}
// Do not allow navigation before the embedded return handler is installed.
back.disabled = false;
